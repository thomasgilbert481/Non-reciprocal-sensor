#!/usr/bin/env python3
"""
EP Circuit Analysis — Circulator Topology
==========================================

Same analysis pipeline as ep_circuit_analysis.py (Fig. 3c & 3d), but
applied to the paper circulator AWR data.

Extracts |S21| peak splitting vs. perturbation strength ε, produces
log-log and waterfall plots.
"""

import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
from pathlib import Path

# =============================================================================
# CONSTANTS
# =============================================================================

C1_PF = 3200.0
KAPPA = 0.3125
F0_MHZ = 20.0
FREQ_RANGE = (10, 35)  # wider range — circulator upper peak reaches ~31 MHz
CSENSING_VALUES = list(range(100, 1700, 100))


# =============================================================================
# DATA LOADING
# =============================================================================

def load_data(filepath):
    """Load AWR Excel export. Returns freq (MHz), dict of Cε -> |S21|."""
    df = pd.read_excel(filepath, header=0)
    freq_mhz = df.iloc[:, 0].values * 1000.0
    traces = {}
    for col in df.columns[1:]:
        match = re.search(r'Csensing\s*=\s*(\d+)', col)
        if match:
            traces[int(match.group(1))] = df[col].values
    return freq_mhz, traces


# =============================================================================
# PEAK DETECTION (dual Lorentzian)
# =============================================================================

def dual_lorentzian(f, a1, f1, g1, a2, f2, g2):
    """Sum of two Lorentzian peaks (|S21|² model)."""
    return a1 / ((f - f1)**2 + g1**2) + a2 / ((f - f2)**2 + g2**2)


def find_two_peaks(freq_mhz, s21, freq_range=FREQ_RANGE):
    """Find two dominant |S21| peaks via Lorentzian refinement."""
    mask = (freq_mhz >= freq_range[0]) & (freq_mhz <= freq_range[1])
    freq_sub = freq_mhz[mask]
    vals_sub = s21[mask]

    freq_step = freq_sub[1] - freq_sub[0]
    min_dist = max(2, int(1.0 / freq_step))

    rough_peaks = None
    for prominence in [0.01, 0.005, 0.001, 0.0005, 0.0001]:
        peaks, _ = find_peaks(vals_sub, prominence=prominence, distance=min_dist)
        if len(peaks) >= 2:
            heights = vals_sub[peaks]
            top2 = peaks[heights.argsort()[-2:]]
            rough_peaks = sorted(top2)
            break

    if rough_peaks is None:
        return None, None

    f1_guess = freq_sub[rough_peaks[0]]
    f2_guess = freq_sub[rough_peaks[1]]

    s21_sq = vals_sub ** 2
    a1_guess = s21_sq[rough_peaks[0]]
    a2_guess = s21_sq[rough_peaks[1]]
    p0 = [a1_guess, f1_guess, 1.0, a2_guess, f2_guess, 1.0]
    bounds_lo = [0, freq_range[0], 0.01, 0, freq_range[0], 0.01]
    bounds_hi = [np.inf, freq_range[1], 10, np.inf, freq_range[1], 10]

    try:
        popt, _ = curve_fit(dual_lorentzian, freq_sub, s21_sq,
                            p0=p0, bounds=(bounds_lo, bounds_hi), maxfev=10000)
        return tuple(sorted([popt[1], popt[4]]))
    except (RuntimeError, ValueError):
        return freq_sub[rough_peaks[0]], freq_sub[rough_peaks[1]]


# =============================================================================
# THEORETICAL PREDICTION
# =============================================================================

def delta_f_theory(epsilon, kappa=KAPPA, f0=F0_MHZ):
    """Theoretical splitting: Δf = 2√(κε) × f₀."""
    return 2.0 * np.sqrt(kappa * epsilon) * f0


# =============================================================================
# MAIN
# =============================================================================

def main():
    data_path = Path('data/paper circulator Csensing sweep (100-1600pf).xlsx')
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    print("=" * 65)
    print("EP Circuit Analysis — CIRCULATOR Topology")
    print("Reproducing Zhao et al. Fig. 3c & 3d")
    print("=" * 65)

    # ------------------------------------------------------------------
    # Step 1: Load data
    # ------------------------------------------------------------------
    freq_mhz, traces = load_data(data_path)
    print(f"Loaded {len(traces)} traces, {len(freq_mhz)} frequency points")
    print(f"Frequency range: {freq_mhz[0]:.1f} – {freq_mhz[-1]:.1f} MHz")

    # ------------------------------------------------------------------
    # Step 2: Extract peak positions and compute splitting
    # ------------------------------------------------------------------
    results = []
    for c_eps_pf in sorted(traces.keys()):
        if c_eps_pf == 0:
            continue

        epsilon = c_eps_pf / (2.0 * C1_PF)
        s21 = traces[c_eps_pf]
        f_minus, f_plus = find_two_peaks(freq_mhz, s21)

        if f_minus is not None:
            delta_f = f_plus - f_minus
            delta_f_th = delta_f_theory(epsilon)
            results.append({
                'C_eps_pF': c_eps_pf,
                'epsilon': epsilon,
                'f_minus_MHz': f_minus,
                'f_plus_MHz': f_plus,
                'delta_f_MHz': delta_f,
                'delta_f_theory_MHz': delta_f_th,
            })
        else:
            print(f"  WARNING: Could not find 2 peaks for Cε = {c_eps_pf} pF")

    results_df = pd.DataFrame(results)
    print(f"\nSuccessfully extracted peaks for "
          f"{len(results_df)} / {len(CSENSING_VALUES)} traces")

    # ------------------------------------------------------------------
    # Step 3: Log-log plot (Fig. 3d)
    # ------------------------------------------------------------------
    eps_arr = results_df['epsilon'].values
    df_arr = results_df['delta_f_MHz'].values

    log_eps = np.log10(eps_arr)
    log_df = np.log10(df_arr)

    coeffs = np.polyfit(log_eps, log_df, 1)
    slope, intercept = coeffs
    fit_line = np.polyval(coeffs, log_eps)

    eps_theory = np.linspace(eps_arr.min(), eps_arr.max(), 200)
    df_theory_arr = delta_f_theory(eps_theory)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(log_eps, log_df, 'o', markersize=8, color='#1f77b4',
            label='Circulator simulation data', zorder=5)
    ax.plot(log_eps, fit_line, '-', color='#d62728', linewidth=2,
            label=f'Linear fit (slope = {slope:.4f})')
    ax.plot(np.log10(eps_theory), np.log10(df_theory_arr), '--', color='#2ca02c',
            linewidth=2,
            label=r'Theory: $\Delta f = 2\sqrt{\kappa\varepsilon}\,f_0$')

    ax.set_xlabel(r'$\log_{10}(\varepsilon)$', fontsize=14)
    ax.set_ylabel(r'$\log_{10}(\Delta f\;[\mathrm{MHz}])$', fontsize=14)
    ax.set_title('Circulator — Frequency Splitting vs. Perturbation (Log-Log)',
                 fontsize=13)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    ax.text(0.05, 0.95,
            f'Measured slope = {slope:.4f}\nTheoretical slope = 0.5',
            transform=ax.transAxes, fontsize=12, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    loglog_path = output_dir / 'circulator_loglog_splitting.png'
    plt.savefig(loglog_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\nSaved log-log plot: {loglog_path}")

    # ------------------------------------------------------------------
    # Step 4: Waterfall / overlay plot (Fig. 3c)
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 7))

    cmap = plt.cm.viridis
    sorted_keys = sorted(traces.keys())
    n_traces = len(sorted_keys)

    for i, c_eps_pf in enumerate(sorted_keys):
        s21 = traces[c_eps_pf]
        color = cmap(i / max(1, n_traces - 1))

        if c_eps_pf == 0:
            ax.plot(freq_mhz, s21 / 6.0, '--', color='gray', linewidth=1.5,
                    label=r'$C_\varepsilon = 0$ (÷6)', zorder=1)
        else:
            label = f'{c_eps_pf} pF' if i % 2 == 0 else None
            ax.plot(freq_mhz, s21, '-', color=color, linewidth=1.2,
                    label=label)

    ax.set_xlabel('Frequency (MHz)', fontsize=14)
    ax.set_ylabel(r'$|S_{21}|$', fontsize=14)
    ax.set_title(r'Circulator — Transmission Spectra for Varying $C_\varepsilon$',
                 fontsize=14)
    ax.set_xlim(10, 35)
    ax.legend(fontsize=9, ncol=2, loc='upper right')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    waterfall_path = output_dir / 'circulator_waterfall_traces.png'
    plt.savefig(waterfall_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved waterfall plot: {waterfall_path}")

    # ------------------------------------------------------------------
    # Step 5: Summary table
    # ------------------------------------------------------------------
    print("\n" + "=" * 90)
    print(f"{'Cε (pF)':>8} | {'ε':>10} | {'f₋ (MHz)':>10} | {'f₊ (MHz)':>10} | "
          f"{'Δf (MHz)':>10} | {'Δf_theory (MHz)':>16}")
    print("-" * 90)
    for _, row in results_df.iterrows():
        print(f"{row['C_eps_pF']:>8.0f} | {row['epsilon']:>10.6f} | "
              f"{row['f_minus_MHz']:>10.2f} | {row['f_plus_MHz']:>10.2f} | "
              f"{row['delta_f_MHz']:>10.2f} | {row['delta_f_theory_MHz']:>16.2f}")
    print("=" * 90)

    # ------------------------------------------------------------------
    # Summary statement
    # ------------------------------------------------------------------
    print(f"\n--- Result Summary ---")
    print(f"Log-log slope (measured):    {slope:.4f}")
    print(f"Log-log slope (theoretical): 0.5000")
    print(f"Deviation from theory:       "
          f"{abs(slope - 0.5):.4f} ({abs(slope - 0.5)/0.5*100:.2f}%)")

    if abs(slope - 0.5) < 0.1:
        print(f"The slope is reasonably close to 0.5.")
    else:
        print(f"The slope deviates significantly from 0.5.")

    print(f"\nNote: The circulator topology shows a large base splitting")
    print(f"(~{df_arr.min():.1f}–{df_arr.max():.1f} MHz) that varies weakly with ε,")
    print(f"unlike the original paper circuit where splitting grew from")
    print(f"~2.4 to ~9.7 MHz. This reflects the stronger coupling and")
    print(f"different isolation mechanism of the electronic circulator.")

    csv_path = output_dir / 'circulator_splitting_results.csv'
    results_df.to_csv(csv_path, index=False)
    print(f"\nResults saved to: {csv_path}")


if __name__ == '__main__':
    main()
