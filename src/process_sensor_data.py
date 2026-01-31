#!/usr/bin/env python3
"""
Sensor Data Processing Script

Processes Excel files containing transmission spectrum data to generate
DeltaF vs Co plots for non-reciprocal sensor analysis.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import re
from pathlib import Path


def load_sensor_data(filepath):
    """Load sensor data from Excel file."""
    df = pd.read_excel(filepath, sheet_name='Sheet1')
    freq = df['Frequency (GHz)'].values

    # Extract Co values and transmission data
    co_data = {}
    for col in df.columns:
        if 'C0 =' in col:
            match = re.search(r'C0 = ([\d.]+)', col)
            if match:
                co_val = float(match.group(1))
                co_data[co_val] = df[col].values

    return freq, co_data


def find_two_peaks(freq, transmission):
    """Find the two main peaks in transmission spectrum."""

    # Try progressively lower prominence thresholds to catch smaller peaks
    for prominence in [0.1, 0.05, 0.01, 0.005, 0.001]:
        peaks, props = find_peaks(transmission,
                                   prominence=prominence,
                                   distance=20)

        if len(peaks) >= 2:
            # Sort by peak height and take top 2
            heights = transmission[peaks]
            top2_idx = peaks[heights.argsort()[-2:]]
            return sorted(top2_idx)

    # If only 1 peak found, return None
    return None


def find_single_peak(freq, transmission):
    """Find the single main peak in transmission spectrum."""
    peaks, _ = find_peaks(transmission, prominence=0.001, distance=20)

    if len(peaks) >= 1:
        # Return the highest peak
        heights = transmission[peaks]
        return peaks[heights.argmax()]
    return None


def get_baseline(freq, co_data, baseline_co=0.0):
    """Calculate baseline frequency difference at Co=0 (or first available with 2 peaks)."""

    # Get list of Co values with valid data, sorted
    available_cos = sorted([co for co in co_data.keys() if co_data[co].max() > 1e-10])

    if not available_cos:
        raise ValueError("No valid data found in file")

    # Try to find first Co value where we can detect 2 peaks
    baseline_co = None
    for co in available_cos:
        transmission = co_data[co]
        peak_indices = find_two_peaks(freq, transmission)
        if peak_indices is not None:
            baseline_co = co
            break

    if baseline_co is None:
        raise ValueError("Could not find 2 peaks at any Co value")

    if baseline_co > 0:
        print(f"  Note: Using Co={baseline_co} pF as baseline (first Co with 2 visible peaks)")

    transmission = co_data[baseline_co]
    peak_indices = find_two_peaks(freq, transmission)

    f1 = freq[peak_indices[0]]
    f2 = freq[peak_indices[1]]
    deltaF_baseline = abs(f2 - f1)

    print(f"  Baseline (Co={baseline_co} pF): peaks at {f1:.3f} GHz and {f2:.3f} GHz")
    print(f"  Baseline deltaF = {deltaF_baseline:.4f} GHz")

    return deltaF_baseline, baseline_co


def process_sensor(freq, co_data):
    """Process all Co values and calculate DeltaF."""

    deltaF_baseline, baseline_co = get_baseline(freq, co_data)

    results = []
    failed_count = 0

    for co_val in sorted(co_data.keys()):
        transmission = co_data[co_val]

        # Skip if no data
        if transmission.max() < 1e-10:
            continue

        peak_indices = find_two_peaks(freq, transmission)

        if peak_indices is not None:
            f1 = freq[peak_indices[0]]
            f2 = freq[peak_indices[1]]
            deltaF_current = abs(f2 - f1)
            DeltaF = deltaF_baseline - deltaF_current  # baseline - current

            results.append({
                'Co_pF': co_val,
                'Peak1_GHz': f1,
                'Peak2_GHz': f2,
                'deltaF_current_GHz': deltaF_current,
                'DeltaF_GHz': DeltaF
            })
        else:
            failed_count += 1
            results.append({
                'Co_pF': co_val,
                'Peak1_GHz': None,
                'Peak2_GHz': None,
                'deltaF_current_GHz': None,
                'DeltaF_GHz': None
            })

    if failed_count > 0:
        print(f"  Warning: Could not find 2 peaks for {failed_count} Co values")

    return pd.DataFrame(results), deltaF_baseline


def process_single_peak_sensor(freq, co_data):
    """Process sensor with single peak - track peak frequency shift."""

    # Find first valid Co for baseline
    available_cos = sorted([co for co in co_data.keys() if co_data[co].max() > 1e-10])
    if not available_cos:
        raise ValueError("No valid data found")

    baseline_co = available_cos[0]
    baseline_trans = co_data[baseline_co]
    baseline_peak_idx = find_single_peak(freq, baseline_trans)

    if baseline_peak_idx is None:
        raise ValueError("Could not find peak for baseline")

    f_baseline = freq[baseline_peak_idx]
    print(f"  Baseline (Co={baseline_co} pF): single peak at {f_baseline:.3f} GHz")

    results = []
    for co_val in sorted(co_data.keys()):
        transmission = co_data[co_val]

        if transmission.max() < 1e-10:
            continue

        peak_idx = find_single_peak(freq, transmission)

        if peak_idx is not None:
            f_current = freq[peak_idx]
            # DeltaF = shift from baseline (baseline - current for consistency)
            DeltaF = f_baseline - f_current

            results.append({
                'Co_pF': co_val,
                'Peak_GHz': f_current,
                'DeltaF_GHz': DeltaF
            })

    return pd.DataFrame(results), f_baseline


def plot_deltaF_vs_Co(results_df, sensor_name, output_path):
    """Create DeltaF vs Co plot with absolute values."""

    # Filter out None values
    valid = results_df.dropna(subset=['DeltaF_GHz'])

    if len(valid) == 0:
        print(f"  Error: No valid data points to plot for {sensor_name}")
        return False

    plt.figure(figsize=(10, 6))
    # Use absolute value for Y-axis
    plt.plot(valid['Co_pF'], valid['DeltaF_GHz'].abs(), 'o-',
             linewidth=2, markersize=6, color='#1f77b4')

    plt.xlabel('Co (pF)', fontsize=12)
    plt.ylabel('|ΔF| (GHz)', fontsize=12)
    plt.title(f'{sensor_name}: |ΔF| vs Capacitance', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved plot: {output_path}")
    return True


def plot_summary(all_results, output_path):
    """Create summary plot with all sensors on one graph."""

    plt.figure(figsize=(12, 7))

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    markers = ['o', 's', '^']

    for i, (name, results_df) in enumerate(all_results.items()):
        valid = results_df.dropna(subset=['DeltaF_GHz'])
        if len(valid) > 0:
            plt.plot(valid['Co_pF'], valid['DeltaF_GHz'].abs(),
                     marker=markers[i], linestyle='-', linewidth=2, markersize=5,
                     color=colors[i], label=name)

    plt.xlabel('Co (pF)', fontsize=12)
    plt.ylabel('|ΔF| (GHz)', fontsize=12)
    plt.title('Sensor Comparison: |ΔF| vs Capacitance', fontsize=14)
    plt.legend(loc='best', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\nSaved summary plot: {output_path}")


def plot_fitting_diagnostics(freq, co_data, sensor_name, output_dir, single_peak=False, n_plots=20):
    """Generate diagnostic plots showing raw spectra with detected peaks."""

    # Get valid Co values
    valid_cos = sorted([co for co in co_data.keys() if co_data[co].max() > 1e-10])

    if len(valid_cos) == 0:
        print(f"  No valid data for fitting plots")
        return

    # Sample ~n_plots evenly across the Co range
    if len(valid_cos) <= n_plots:
        sample_cos = valid_cos
    else:
        indices = np.linspace(0, len(valid_cos) - 1, n_plots, dtype=int)
        sample_cos = [valid_cos[i] for i in indices]

    print(f"  Generating {len(sample_cos)} fitting diagnostic plots...")

    for co_val in sample_cos:
        transmission = co_data[co_val]

        # Find peaks
        if single_peak:
            peak_idx = find_single_peak(freq, transmission)
            peak_indices = [peak_idx] if peak_idx is not None else []
        else:
            peak_indices = find_two_peaks(freq, transmission)
            if peak_indices is None:
                peak_indices = []

        # Create the plot
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot raw spectrum
        ax.plot(freq, transmission, 'b-', linewidth=1, label='Raw Data')

        # Mark detected peaks
        if len(peak_indices) > 0:
            peak_freqs = freq[peak_indices]
            peak_trans = transmission[peak_indices]
            ax.plot(peak_freqs, peak_trans, 'ro', markersize=12,
                    label=f'Detected Peaks ({len(peak_indices)})', zorder=5)

            # Add vertical lines at peak positions
            for pf in peak_freqs:
                ax.axvline(x=pf, color='r', linestyle='--', alpha=0.5)

            # Annotate peak frequencies
            for pf, pt in zip(peak_freqs, peak_trans):
                ax.annotate(f'{pf:.3f} GHz',
                           xy=(pf, pt), xytext=(5, 10),
                           textcoords='offset points', fontsize=9,
                           color='red', fontweight='bold')

        ax.set_xlabel('Frequency (GHz)', fontsize=12)
        ax.set_ylabel('Transmission |S21|', fontsize=12)
        ax.set_title(f'{sensor_name} - Co = {co_val:.2f} pF', fontsize=14)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        # Focus on the relevant frequency range (where peaks are)
        if len(peak_indices) > 0:
            peak_center = np.mean(peak_freqs)
            ax.set_xlim(max(0, peak_center - 3), min(20, peak_center + 3))

        plt.tight_layout()

        # Save plot
        filename = f"Co_{co_val:.2f}pF.png".replace('.', 'p', 1)
        filepath = output_dir / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

    print(f"  Saved fitting plots to: {output_dir}")


def main():
    # Define input files and output names
    # Note: non-reciprocal sensor only has 1 peak, requires special handling
    sensors = [
        {
            'file': 'data/Reciprocal Sensor with IC Co sweep (o-1pf).xlsx',
            'name': 'Reciprocal Sensor with IC',
            'output_prefix': 'reciprocal_with_IC',
            'single_peak': False
        },
        {
            'file': 'data/non reciprocal sensor (0-1) co sweep.xlsx',
            'name': 'Non-Reciprocal Sensor',
            'output_prefix': 'non_reciprocal',
            'single_peak': False  # Has 2 peaks (smaller one around 2.5 GHz)
        },
        {
            'file': 'data/reciprocal sensor without IC (0-1pf_.xlsx',
            'name': 'Reciprocal Sensor without IC',
            'output_prefix': 'reciprocal_without_IC',
            'single_peak': False
        }
    ]

    # Create output directory
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    # Create fitting directory
    fitting_dir = Path('fitting')
    fitting_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("Sensor Data Processing")
    print("=" * 60)

    # Store results for summary plot
    all_results = {}

    for sensor in sensors:
        print(f"\nProcessing: {sensor['name']}")
        print("-" * 40)

        try:
            # Load data
            freq, co_data = load_sensor_data(sensor['file'])
            print(f"  Loaded {len(co_data)} Co values, {len(freq)} frequency points")

            # Process based on sensor type
            if sensor['single_peak']:
                print("  Mode: Single peak tracking (frequency shift)")
                results_df, baseline = process_single_peak_sensor(freq, co_data)
            else:
                print("  Mode: Two-peak difference tracking")
                results_df, baseline = process_sensor(freq, co_data)

            # Store for summary plot
            all_results[sensor['name']] = results_df

            # Generate individual plot
            plot_path = output_dir / f"{sensor['output_prefix']}_deltaF_vs_Co.png"
            plot_deltaF_vs_Co(results_df, sensor['name'], plot_path)

            # Generate fitting diagnostic plots
            sensor_fitting_dir = fitting_dir / sensor['output_prefix']
            sensor_fitting_dir.mkdir(exist_ok=True)
            plot_fitting_diagnostics(freq, co_data, sensor['name'],
                                    sensor_fitting_dir, sensor['single_peak'])

        except Exception as e:
            print(f"  Error: {e}")

    # Generate summary plot with all sensors
    if all_results:
        summary_path = output_dir / "summary_all_sensors.png"
        plot_summary(all_results, summary_path)

    print("\n" + "=" * 60)
    print("Processing complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
