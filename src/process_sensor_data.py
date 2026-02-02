#!/usr/bin/env python3
"""
Sensor Data Processing Script
=============================

This script processes transmission spectrum data (S21 parameter) from RF sensors
to analyze how the frequency difference between resonant peaks changes as a
function of capacitance (Co).

The sensors are coupled LC resonator circuits where:
- Each resonator has a characteristic resonant frequency
- When coupled, the system shows two transmission peaks (symmetric and antisymmetric modes)
- The frequency difference between peaks depends on the coupling strength
- By sweeping Co (0-1 pF), we measure how the coupling changes

Key Metric: DeltaF = deltaF_baseline - deltaF_current
- deltaF_baseline: frequency difference between peaks at Co=0 (reference)
- deltaF_current: frequency difference at the current Co value
- DeltaF: the change in peak separation from baseline (sensor response)

Author: Auto-generated for Non-Reciprocal Sensor Analysis
"""

# =============================================================================
# IMPORTS
# =============================================================================

import pandas as pd          # For reading Excel files and handling tabular data
import numpy as np           # For numerical operations on arrays
import matplotlib.pyplot as plt  # For generating plots
from scipy.signal import find_peaks  # For detecting peaks in spectra
from scipy.ndimage import gaussian_filter1d  # For smoothing data before differentiation
import re                    # For extracting Co values from column names using regex
from pathlib import Path     # For cross-platform file path handling


# =============================================================================
# DATA LOADING FUNCTIONS
# =============================================================================

def load_sensor_data(filepath):
    """
    Load sensor data from an Excel file.

    The Excel files have a specific format:
    - Single sheet named 'Sheet1'
    - First column: 'Frequency (GHz)' - the x-axis values
    - Remaining columns: Transmission data for each Co value
      - Column names follow pattern: '|S(2,1)| : [Sensor Name] (C0 = X )'
      - X is the capacitance value in pF (0, 0.01, 0.02, ... 1.0)

    Parameters
    ----------
    filepath : str
        Path to the Excel file

    Returns
    -------
    freq : numpy.ndarray
        Array of frequency values in GHz (typically 0.1 to 20 GHz, 1991 points)
    co_data : dict
        Dictionary mapping Co values (float) to transmission arrays (numpy.ndarray)
        Example: {0.0: array([...]), 0.01: array([...]), ...}
    """
    # Read the Excel file - all data is in 'Sheet1'
    df = pd.read_excel(filepath, sheet_name='Sheet1')

    # Extract the frequency column as a numpy array for fast operations
    freq = df['Frequency (GHz)'].values

    # Extract transmission data for each Co value
    # We need to parse column names to find the Co value embedded in them
    co_data = {}
    for col in df.columns:
        # Look for columns containing 'C0 =' which indicates transmission data
        if 'C0 =' in col:
            # Use regex to extract the numeric Co value from the column name
            # Pattern matches: 'C0 = ' followed by digits and optional decimal
            match = re.search(r'C0 = ([\d.]+)', col)
            if match:
                # Convert the matched string to a float (e.g., '0.01' -> 0.01)
                co_val = float(match.group(1))
                # Store the transmission data array keyed by Co value
                co_data[co_val] = df[col].values

    return freq, co_data


# =============================================================================
# PEAK DETECTION FUNCTIONS
# =============================================================================

def find_two_peaks_second_derivative(freq, transmission):
    """
    Find peaks using second derivative analysis.

    This method is used when standard peak detection fails because peaks have
    merged into shoulders. The second derivative of a function is negative at
    peaks (concave down) and positive at valleys (concave up). By finding peaks
    in the NEGATIVE second derivative, we can detect:
    - True local maxima (normal peaks)
    - Inflection points/shoulders (where merged peaks create a "bump")

    This is essential for the non-reciprocal sensor where the two resonant modes
    often merge into a single broad peak with a shoulder at lower Co values.

    Parameters
    ----------
    freq : numpy.ndarray
        Frequency values in GHz
    transmission : numpy.ndarray
        Transmission (|S21|) values

    Returns
    -------
    list or None
        Sorted list of two indices corresponding to detected features,
        or None if fewer than 2 features found
    """
    # Step 1: Smooth the data using a Gaussian filter
    # sigma=3 provides moderate smoothing to reduce noise while preserving features
    # Without smoothing, the second derivative would be very noisy
    trans_smooth = gaussian_filter1d(transmission, sigma=3)

    # Step 2: Calculate the first derivative (slope) using numpy's gradient
    # gradient() computes centered differences, handling edges appropriately
    # We pass freq as the spacing to get the derivative with respect to frequency
    d1 = np.gradient(trans_smooth, freq)

    # Step 3: Calculate the second derivative (curvature)
    d2 = np.gradient(d1, freq)

    # Step 4: Find peaks in the NEGATIVE second derivative
    # Where d2 is most negative (d2_neg most positive), we have:
    # - Local maxima in the original signal (peaks)
    # - Inflection points where curvature changes rapidly (shoulders)
    d2_neg = -d2

    # Use scipy's find_peaks with:
    # - prominence=0.0005: very low threshold to catch subtle features
    # - distance=30: minimum ~0.3 GHz separation between detected features
    d2_peaks, _ = find_peaks(d2_neg, prominence=0.0005, distance=30)

    # Step 5: Filter to the relevant frequency range (1-8 GHz)
    # The sensor resonances occur in this range; features outside are artifacts
    d2_peaks = d2_peaks[(freq[d2_peaks] > 1) & (freq[d2_peaks] < 8)]

    # Step 6: If we found at least 2 features, return the top 2 by prominence
    if len(d2_peaks) >= 2:
        # Get the height of each feature in the negative second derivative
        heights = d2_neg[d2_peaks]
        # argsort gives indices that would sort the array; take last 2 (largest)
        top2_idx = d2_peaks[heights.argsort()[-2:]]
        # Return sorted by index (i.e., by frequency, lower first)
        return sorted(top2_idx)

    # If we couldn't find 2 features, return None to signal failure
    return None


def find_two_peaks(freq, transmission):
    """
    Find the two main transmission peaks in a spectrum.

    This is the primary peak detection function. It uses a multi-stage approach:

    1. Try standard peak detection with progressively lower thresholds
       - Start with high prominence (0.1) for clear, well-separated peaks
       - Gradually lower threshold to catch smaller secondary peaks

    2. If standard detection fails, fall back to second derivative method
       - This catches merged peaks that appear as shoulders

    The two peaks correspond to the symmetric and antisymmetric resonant modes
    of the coupled resonator system.

    Parameters
    ----------
    freq : numpy.ndarray
        Frequency values in GHz
    transmission : numpy.ndarray
        Transmission (|S21|) values - linear magnitude, not dB

    Returns
    -------
    list or None
        Sorted list of two indices [idx1, idx2] where idx1 < idx2,
        or None if two peaks could not be found
    """
    # Stage 1: Try standard peak detection with decreasing prominence thresholds
    # Prominence measures how much a peak stands out from surrounding baseline
    for prominence in [0.1, 0.05, 0.01, 0.005, 0.001]:
        # find_peaks returns indices of local maxima meeting the criteria
        # distance=20 means peaks must be at least 20 samples (~0.2 GHz) apart
        peaks, props = find_peaks(transmission,
                                   prominence=prominence,
                                   distance=20)

        # If we found at least 2 peaks, select the two tallest
        if len(peaks) >= 2:
            # Get the transmission values at each peak
            heights = transmission[peaks]
            # argsort returns indices that would sort ascending; take last 2 for largest
            top2_idx = peaks[heights.argsort()[-2:]]
            # Return sorted by index (lower frequency first)
            return sorted(top2_idx)

    # Stage 2: Standard detection failed - use second derivative method
    # This is our fallback for merged peaks/shoulders
    result = find_two_peaks_second_derivative(freq, transmission)
    if result is not None:
        return result

    # If all methods failed, return None to indicate we couldn't find 2 peaks
    return None


def find_single_peak(freq, transmission):
    """
    Find the single highest transmission peak in a spectrum.

    This function is used when a sensor is known to have only one dominant peak,
    or as a fallback. It simply finds all local maxima and returns the tallest one.

    Note: This function is currently not used in the main processing since all
    three sensors are processed in two-peak mode, but it's kept for flexibility.

    Parameters
    ----------
    freq : numpy.ndarray
        Frequency values in GHz
    transmission : numpy.ndarray
        Transmission (|S21|) values

    Returns
    -------
    int or None
        Index of the highest peak, or None if no peaks found
    """
    # Find all local maxima with minimal requirements
    # prominence=0.001 is very low, catching almost any local maximum
    # distance=20 prevents detecting noise spikes as separate peaks
    peaks, _ = find_peaks(transmission, prominence=0.001, distance=20)

    if len(peaks) >= 1:
        # Find which peak has the maximum transmission value
        heights = transmission[peaks]
        # argmax returns the index within 'peaks' of the maximum
        return peaks[heights.argmax()]

    # No peaks found at all
    return None


# =============================================================================
# BASELINE AND PROCESSING FUNCTIONS
# =============================================================================

def get_baseline(freq, co_data, baseline_co=0.0):
    """
    Determine the baseline frequency difference (deltaF) at the reference Co value.

    The baseline is the frequency difference between the two resonant peaks at
    Co=0 (or the first Co value where two peaks can be detected). This baseline
    represents the "zero point" of our sensor measurement.

    Special handling:
    - If Co=0 has no valid data (transmission all zeros), we find the first
      valid Co value
    - If the peaks are merged at low Co, we find the first Co where two distinct
      peaks can be detected

    Parameters
    ----------
    freq : numpy.ndarray
        Frequency values in GHz
    co_data : dict
        Dictionary mapping Co values to transmission arrays
    baseline_co : float, optional
        Desired baseline Co value (default 0.0)

    Returns
    -------
    deltaF_baseline : float
        Frequency difference between the two peaks at baseline (in GHz)
    baseline_co : float
        The actual Co value used for baseline (may differ from requested if
        requested value had no valid data)

    Raises
    ------
    ValueError
        If no valid data exists or two peaks cannot be found at any Co value
    """
    # Get list of Co values that have valid (non-zero) transmission data
    # Some files (e.g., reciprocal without IC) have all zeros at Co=0
    # We check if max > 1e-10 to filter out essentially-zero data
    available_cos = sorted([co for co in co_data.keys() if co_data[co].max() > 1e-10])

    if not available_cos:
        raise ValueError("No valid data found in file")

    # Find the first Co value where we can successfully detect 2 peaks
    # For some sensors, peaks may be merged at low Co values
    baseline_co = None
    for co in available_cos:
        transmission = co_data[co]
        peak_indices = find_two_peaks(freq, transmission)
        if peak_indices is not None:
            # Found a Co value with detectable peaks - use this as baseline
            baseline_co = co
            break

    if baseline_co is None:
        raise ValueError("Could not find 2 peaks at any Co value")

    # Notify user if we couldn't use Co=0 as baseline
    if baseline_co > 0:
        print(f"  Note: Using Co={baseline_co} pF as baseline (first Co with 2 visible peaks)")

    # Get the peak positions at the baseline Co
    transmission = co_data[baseline_co]
    peak_indices = find_two_peaks(freq, transmission)

    # Extract the frequencies of the two peaks
    f1 = freq[peak_indices[0]]  # Lower frequency peak
    f2 = freq[peak_indices[1]]  # Higher frequency peak

    # Calculate the baseline frequency difference
    deltaF_baseline = abs(f2 - f1)

    # Print baseline information for verification
    print(f"  Baseline (Co={baseline_co} pF): peaks at {f1:.3f} GHz and {f2:.3f} GHz")
    print(f"  Baseline deltaF = {deltaF_baseline:.4f} GHz")

    return deltaF_baseline, baseline_co


def process_sensor(freq, co_data):
    """
    Process all Co values for a sensor and calculate DeltaF for each.

    This is the main processing function that:
    1. Establishes the baseline deltaF at Co=0 (or first valid Co)
    2. For each Co value, finds the two peaks and calculates deltaF
    3. Computes DeltaF = deltaF_baseline - deltaF_current

    The DeltaF metric represents the change in peak separation from the baseline.
    A positive DeltaF means the peaks have moved closer together compared to baseline.

    Parameters
    ----------
    freq : numpy.ndarray
        Frequency values in GHz
    co_data : dict
        Dictionary mapping Co values to transmission arrays

    Returns
    -------
    results_df : pandas.DataFrame
        DataFrame with columns:
        - Co_pF: capacitance value
        - Peak1_GHz: frequency of lower peak
        - Peak2_GHz: frequency of higher peak
        - deltaF_current_GHz: current peak separation
        - DeltaF_GHz: change from baseline (baseline - current)
    deltaF_baseline : float
        The baseline frequency difference used for reference
    """
    # Step 1: Establish the baseline
    deltaF_baseline, baseline_co = get_baseline(freq, co_data)

    # Step 2: Process each Co value
    results = []
    failed_count = 0  # Track how many Co values we couldn't process

    # Iterate through Co values in sorted order (0, 0.01, 0.02, ...)
    for co_val in sorted(co_data.keys()):
        transmission = co_data[co_val]

        # Skip Co values with no valid data (all zeros)
        if transmission.max() < 1e-10:
            continue

        # Try to find the two peaks
        peak_indices = find_two_peaks(freq, transmission)

        if peak_indices is not None:
            # Successfully found 2 peaks - calculate metrics
            f1 = freq[peak_indices[0]]  # Lower frequency peak
            f2 = freq[peak_indices[1]]  # Higher frequency peak
            deltaF_current = abs(f2 - f1)  # Current peak separation

            # DeltaF = baseline - current
            # Positive means peaks moved closer together
            # Negative means peaks moved further apart
            DeltaF = deltaF_baseline - deltaF_current

            results.append({
                'Co_pF': co_val,
                'Peak1_GHz': f1,
                'Peak2_GHz': f2,
                'deltaF_current_GHz': deltaF_current,
                'DeltaF_GHz': DeltaF
            })
        else:
            # Could not find 2 peaks - record as None values
            failed_count += 1
            results.append({
                'Co_pF': co_val,
                'Peak1_GHz': None,
                'Peak2_GHz': None,
                'deltaF_current_GHz': None,
                'DeltaF_GHz': None
            })

    # Warn user if some Co values couldn't be processed
    if failed_count > 0:
        print(f"  Warning: Could not find 2 peaks for {failed_count} Co values")

    # Convert results list to DataFrame for easy handling and CSV export
    return pd.DataFrame(results), deltaF_baseline


def process_single_peak_sensor(freq, co_data):
    """
    Process a sensor with single peak tracking (frequency shift mode).

    This alternative processing mode tracks the shift of a single peak rather
    than the difference between two peaks. It's useful when:
    - The sensor has only one dominant resonance
    - The two peaks are completely merged and can't be separated

    DeltaF in this mode represents the shift of the peak frequency from baseline.

    Note: Currently not used in main() since all sensors use two-peak mode,
    but kept for flexibility.

    Parameters
    ----------
    freq : numpy.ndarray
        Frequency values in GHz
    co_data : dict
        Dictionary mapping Co values to transmission arrays

    Returns
    -------
    results_df : pandas.DataFrame
        DataFrame with columns: Co_pF, Peak_GHz, DeltaF_GHz
    f_baseline : float
        The baseline peak frequency
    """
    # Find the first Co value with valid data
    available_cos = sorted([co for co in co_data.keys() if co_data[co].max() > 1e-10])
    if not available_cos:
        raise ValueError("No valid data found")

    # Use the first available Co as baseline
    baseline_co = available_cos[0]
    baseline_trans = co_data[baseline_co]
    baseline_peak_idx = find_single_peak(freq, baseline_trans)

    if baseline_peak_idx is None:
        raise ValueError("Could not find peak for baseline")

    # Record baseline peak frequency
    f_baseline = freq[baseline_peak_idx]
    print(f"  Baseline (Co={baseline_co} pF): single peak at {f_baseline:.3f} GHz")

    # Process each Co value
    results = []
    for co_val in sorted(co_data.keys()):
        transmission = co_data[co_val]

        # Skip invalid data
        if transmission.max() < 1e-10:
            continue

        peak_idx = find_single_peak(freq, transmission)

        if peak_idx is not None:
            f_current = freq[peak_idx]
            # DeltaF = baseline - current (positive means peak shifted to lower frequency)
            DeltaF = f_baseline - f_current

            results.append({
                'Co_pF': co_val,
                'Peak_GHz': f_current,
                'DeltaF_GHz': DeltaF
            })

    return pd.DataFrame(results), f_baseline


# =============================================================================
# PLOTTING FUNCTIONS
# =============================================================================

def plot_deltaF_vs_Co(results_df, sensor_name, output_path):
    """
    Create a plot of |DeltaF| vs Co for a single sensor.

    The plot shows how the frequency difference between peaks changes as the
    coupling capacitance is swept. We use absolute value because:
    - The sign depends on whether peaks move closer or further apart
    - For sensor comparison, the magnitude of change is most relevant

    Parameters
    ----------
    results_df : pandas.DataFrame
        Processing results with 'Co_pF' and 'DeltaF_GHz' columns
    sensor_name : str
        Name of the sensor for the plot title
    output_path : Path
        Where to save the PNG file

    Returns
    -------
    bool
        True if plot was created successfully, False if no valid data
    """
    # Remove rows where peak detection failed (DeltaF_GHz is None/NaN)
    valid = results_df.dropna(subset=['DeltaF_GHz'])

    if len(valid) == 0:
        print(f"  Error: No valid data points to plot for {sensor_name}")
        return False

    # Create the figure with a reasonable size
    plt.figure(figsize=(10, 6))

    # Plot with both markers and lines for clarity
    # .abs() converts to absolute value - we care about magnitude not sign
    plt.plot(valid['Co_pF'], valid['DeltaF_GHz'].abs(), 'o-',
             linewidth=2, markersize=6, color='#1f77b4')

    # Label axes with units
    plt.xlabel('Co (pF)', fontsize=12)
    plt.ylabel('|ΔF| (GHz)', fontsize=12)
    plt.title(f'{sensor_name}: |ΔF| vs Capacitance', fontsize=14)

    # Add grid for easier reading of values
    plt.grid(True, alpha=0.3)

    # Adjust layout to prevent label cutoff
    plt.tight_layout()

    # Save as high-resolution PNG
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()  # Close to free memory

    print(f"  Saved plot: {output_path}")
    return True


def plot_summary(all_results, output_path):
    """
    Create a comparison plot with all sensors overlaid.

    This plot allows direct comparison of the three sensor configurations:
    - Reciprocal with IC (initial coupling)
    - Non-Reciprocal
    - Reciprocal without IC

    Different colors and markers distinguish each sensor.

    Parameters
    ----------
    all_results : dict
        Dictionary mapping sensor names to their results DataFrames
    output_path : Path
        Where to save the PNG file
    """
    # Create larger figure to accommodate legend
    plt.figure(figsize=(12, 7))

    # Define distinct colors and markers for each sensor
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Blue, Orange, Green
    markers = ['o', 's', '^']  # Circle, Square, Triangle

    # Plot each sensor's data
    for i, (name, results_df) in enumerate(all_results.items()):
        # Filter out failed detections
        valid = results_df.dropna(subset=['DeltaF_GHz'])
        if len(valid) > 0:
            plt.plot(valid['Co_pF'], valid['DeltaF_GHz'].abs(),
                     marker=markers[i], linestyle='-', linewidth=2, markersize=5,
                     color=colors[i], label=name)

    # Labels and formatting
    plt.xlabel('Co (pF)', fontsize=12)
    plt.ylabel('|ΔF| (GHz)', fontsize=12)
    plt.title('Sensor Comparison: |ΔF| vs Capacitance', fontsize=14)
    plt.legend(loc='best', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # Save the comparison plot
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\nSaved summary plot: {output_path}")


def plot_fitting_diagnostics(freq, co_data, sensor_name, output_dir, single_peak=False, n_plots=20):
    """
    Generate diagnostic plots showing raw spectra with detected peak locations.

    These plots are essential for verifying that the peak detection algorithm
    is working correctly. Each plot shows:
    - The raw transmission spectrum (blue line)
    - Detected peak locations (red dots)
    - Peak frequency labels
    - Vertical dashed lines at peak positions

    We generate ~20 plots evenly sampled across the Co range to show how
    the peaks evolve as capacitance changes.

    Parameters
    ----------
    freq : numpy.ndarray
        Frequency values in GHz
    co_data : dict
        Dictionary mapping Co values to transmission arrays
    sensor_name : str
        Name of the sensor for plot titles
    output_dir : Path
        Directory to save the PNG files
    single_peak : bool, optional
        If True, use single peak detection instead of two-peak (default False)
    n_plots : int, optional
        Approximate number of diagnostic plots to generate (default 20)
    """
    # Get list of Co values with valid data
    valid_cos = sorted([co for co in co_data.keys() if co_data[co].max() > 1e-10])

    if len(valid_cos) == 0:
        print(f"  No valid data for fitting plots")
        return

    # Select ~n_plots Co values evenly spaced across the range
    if len(valid_cos) <= n_plots:
        # If we have fewer valid Co values than requested, use all of them
        sample_cos = valid_cos
    else:
        # Generate evenly spaced indices and select those Co values
        indices = np.linspace(0, len(valid_cos) - 1, n_plots, dtype=int)
        sample_cos = [valid_cos[i] for i in indices]

    print(f"  Generating {len(sample_cos)} fitting diagnostic plots...")

    # Generate a plot for each sampled Co value
    for co_val in sample_cos:
        transmission = co_data[co_val]

        # Detect peaks using the appropriate method
        if single_peak:
            peak_idx = find_single_peak(freq, transmission)
            peak_indices = [peak_idx] if peak_idx is not None else []
        else:
            peak_indices = find_two_peaks(freq, transmission)
            if peak_indices is None:
                peak_indices = []

        # Create the diagnostic plot
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot the raw transmission spectrum
        ax.plot(freq, transmission, 'b-', linewidth=1, label='Raw Data')

        # Mark detected peaks if any were found
        if len(peak_indices) > 0:
            peak_freqs = freq[peak_indices]
            peak_trans = transmission[peak_indices]

            # Plot red dots at peak locations
            ax.plot(peak_freqs, peak_trans, 'ro', markersize=12,
                    label=f'Detected Peaks ({len(peak_indices)})', zorder=5)

            # Add vertical dashed lines at peak positions for clarity
            for pf in peak_freqs:
                ax.axvline(x=pf, color='r', linestyle='--', alpha=0.5)

            # Label each peak with its frequency
            for pf, pt in zip(peak_freqs, peak_trans):
                ax.annotate(f'{pf:.3f} GHz',
                           xy=(pf, pt), xytext=(5, 10),
                           textcoords='offset points', fontsize=9,
                           color='red', fontweight='bold')

        # Axis labels and title
        ax.set_xlabel('Frequency (GHz)', fontsize=12)
        ax.set_ylabel('Transmission |S21|', fontsize=12)
        ax.set_title(f'{sensor_name} - Co = {co_val:.2f} pF', fontsize=14)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        # Zoom to the relevant frequency range around the peaks
        # This makes it easier to see the peak structure
        if len(peak_indices) > 0:
            peak_center = np.mean(peak_freqs)
            ax.set_xlim(max(0, peak_center - 3), min(20, peak_center + 3))

        plt.tight_layout()

        # Generate filename: Co_0p52pF.png (using 'p' instead of '.' for compatibility)
        filename = f"Co_{co_val:.2f}pF.png".replace('.', 'p', 1)
        filepath = output_dir / filename

        # Save at moderate resolution (150 dpi) since these are diagnostic plots
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()  # Free memory

    print(f"  Saved fitting plots to: {output_dir}")


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """
    Main entry point for sensor data processing.

    This function orchestrates the entire processing pipeline:
    1. Define the sensor configurations (file paths, names, processing modes)
    2. Create output directories
    3. For each sensor:
       a. Load data from Excel file
       b. Process all Co values to extract DeltaF
       c. Generate individual DeltaF vs Co plot
       d. Generate fitting diagnostic plots
    4. Create a summary comparison plot with all sensors

    Output files are saved to:
    - output/: Main result plots (DeltaF vs Co)
    - fitting/: Diagnostic plots showing peak detection
    """
    # ==========================================================================
    # SENSOR CONFIGURATION
    # ==========================================================================
    # Define the three sensor datasets to process
    # Each entry specifies:
    # - file: path to the Excel data file
    # - name: human-readable name for plot titles
    # - output_prefix: filename prefix for saved plots
    # - single_peak: whether to use single-peak mode (all use two-peak mode)

    sensors = [
        {
            'file': 'data/Reciprocal Sensor with IC Co sweep (o-1pf).xlsx',
            'name': 'Reciprocal Sensor with IC',
            'output_prefix': 'reciprocal_with_IC',
            'single_peak': False  # Use two-peak detection
        },
        {
            'file': 'data/non reciprocal sensor (0-1) co sweep.xlsx',
            'name': 'Non-Reciprocal Sensor',
            'output_prefix': 'non_reciprocal',
            'single_peak': False  # Has 2 peaks (smaller one around 2.5 GHz, may need second derivative)
        },
        {
            'file': 'data/reciprocal sensor without IC (0-1pf_.xlsx',
            'name': 'Reciprocal Sensor without IC',
            'output_prefix': 'reciprocal_without_IC',
            'single_peak': False  # Use two-peak detection
        }
    ]

    # ==========================================================================
    # CREATE OUTPUT DIRECTORIES
    # ==========================================================================

    # Main output directory for DeltaF vs Co plots
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)  # Create if doesn't exist, ignore if does

    # Fitting directory for diagnostic plots
    fitting_dir = Path('fitting')
    fitting_dir.mkdir(exist_ok=True)

    # ==========================================================================
    # PROCESSING LOOP
    # ==========================================================================

    print("=" * 60)
    print("Sensor Data Processing")
    print("=" * 60)

    # Dictionary to store results from all sensors for the summary plot
    all_results = {}

    # Process each sensor
    for sensor in sensors:
        print(f"\nProcessing: {sensor['name']}")
        print("-" * 40)

        try:
            # Step 1: Load data from Excel file
            freq, co_data = load_sensor_data(sensor['file'])
            print(f"  Loaded {len(co_data)} Co values, {len(freq)} frequency points")

            # Step 2: Process based on sensor configuration
            if sensor['single_peak']:
                # Single peak mode: track frequency shift of one peak
                print("  Mode: Single peak tracking (frequency shift)")
                results_df, baseline = process_single_peak_sensor(freq, co_data)
            else:
                # Two-peak mode: track difference between two peaks
                print("  Mode: Two-peak difference tracking")
                results_df, baseline = process_sensor(freq, co_data)

            # Store results for summary plot
            all_results[sensor['name']] = results_df

            # Step 3: Generate individual DeltaF vs Co plot
            plot_path = output_dir / f"{sensor['output_prefix']}_deltaF_vs_Co.png"
            plot_deltaF_vs_Co(results_df, sensor['name'], plot_path)

            # Step 4: Generate fitting diagnostic plots
            # Create a subdirectory for this sensor's diagnostic plots
            sensor_fitting_dir = fitting_dir / sensor['output_prefix']
            sensor_fitting_dir.mkdir(exist_ok=True)
            plot_fitting_diagnostics(freq, co_data, sensor['name'],
                                    sensor_fitting_dir, sensor['single_peak'])

        except Exception as e:
            # If anything goes wrong, print error and continue with next sensor
            print(f"  Error: {e}")

    # ==========================================================================
    # GENERATE SUMMARY PLOT
    # ==========================================================================

    # Create comparison plot with all sensors overlaid
    if all_results:
        summary_path = output_dir / "summary_all_sensors.png"
        plot_summary(all_results, summary_path)

    print("\n" + "=" * 60)
    print("Processing complete!")
    print("=" * 60)


# =============================================================================
# SCRIPT ENTRY POINT
# =============================================================================

# This block runs only when the script is executed directly (not imported)
if __name__ == '__main__':
    main()
