#!/usr/bin/env python3
"""
Figure 2b Recreation — Circulator Topology
============================================

Same analysis as fig2b_splitting_vs_epsilon.py but applied to the
paper circulator AWR data. Plots normalized Δω vs ε for all three
perturbation types (analytical) with circulator AWR data overlay.
"""

import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
from pathlib import Path

# =============================================================================
# CONSTANTS
# =============================================================================

KAPPA = 0.3125
F0_MHZ = 20.0
C1_PF = 3200.0
FREQ_RANGE = (10, 35)  # wider for circulator upper peaks


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


def find_two_peaks(freq_mhz, s21):
    """Find two dominant |S21| peaks via Lorentzian refinement."""
    mask = (freq_mhz >= FREQ_RANGE[0]) & (freq_mhz <= FREQ_RANGE[1])
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
    bounds_lo = [0, FREQ_RANGE[0], 0.01, 0, FREQ_RANGE[0], 0.01]
    bounds_hi = [np.inf, FREQ_RANGE[1], 10, np.inf, FREQ_RANGE[1], 10]

    try:
        popt, _ = curve_fit(dual_lorentzian, freq_sub, s21_sq,
                            p0=p0, bounds=(bounds_lo, bounds_hi), maxfev=10000)
        return tuple(sorted([popt[1], popt[4]]))
    except (RuntimeError, ValueError):
        return freq_sub[rough_peaks[0]], freq_sub[rough_peaks[1]]


# =============================================================================
# ANALYTICAL CURVES
# =============================================================================

def delta_omega_type1(eps):
    """Type 1: Δω⁽¹⁾ = 1 - 1/√(1+2ε)."""
    return 1.0 - 1.0 / np.sqrt(1.0 + 2.0 * eps)


def delta_omega_type2(eps, kappa=KAPPA):
    """Type 2: Δω⁽²⁾ = 2√[ε(κ+ε)]."""
    return 2.0 * np.sqrt(eps * (kappa + eps))


def delta_omega_type3(eps, kappa=KAPPA):
    """Type 3: Im[Δω⁽³⁾] = 2√[ε(κ-ε)]  (ε < κ only)."""
    arg = eps * (kappa - eps)
    return np.where(arg >= 0, 2.0 * np.sqrt(np.maximum(arg, 0)), np.nan)


def delta_omega_ref(eps, kappa=KAPPA):
    """Reference: 2√(κε)."""
    return 2.0 * np.sqrt(kappa * eps)


# =============================================================================
# PLOTTING
# =============================================================================

def make_fig2b(eps_fine, eps_awr, dw_awr, xlim, ylim, output_path, zoomed=False):
    """Create one version of Figure 2b."""
    fig, ax = plt.subplots(figsize=(7, 5.5))

    # Analytical curves
    ax.plot(eps_fine, delta_omega_type1(eps_fine),
            color='#1f77b4', linewidth=2, label=r'$\Delta\omega^{(1)}$')
    ax.plot(eps_fine, delta_omega_type2(eps_fine),
            color='#d62728', linewidth=2, label=r'$\Delta\omega^{(2)}$')

    eps_t3 = eps_fine[eps_fine <= KAPPA]
    ax.plot(eps_t3, delta_omega_type3(eps_t3),
            color='#2ca02c', linewidth=2, label=r'Im[$\Delta\omega^{(3)}$]')

    ax.plot(eps_fine, delta_omega_ref(eps_fine),
            color='black', linewidth=1.5, linestyle='--',
            label=r'$2\sqrt{\kappa\varepsilon}$')

    # AWR circulator data
    ax.plot(eps_awr, dw_awr, 's', color='#d62728', markersize=6,
            markeredgecolor='black', markeredgewidth=0.5, zorder=10,
            label='AWR circulator (Type 2)')

    # Annotations
    if zoomed:
        ep = 0.035
        ax.annotate(r'$2\sqrt{\kappa\varepsilon}$',
                    xy=(ep, delta_omega_ref(ep)),
                    xytext=(ep + 0.015, delta_omega_ref(ep) - 0.035),
                    fontsize=12, color='black',
                    arrowprops=dict(arrowstyle='->', color='black', lw=1.2))
        ep = 0.055
        ax.annotate(r'$\sim\!\varepsilon$',
                    xy=(ep, delta_omega_type1(ep)),
                    xytext=(ep + 0.012, delta_omega_type1(ep) + 0.025),
                    fontsize=12, color='#1f77b4',
                    arrowprops=dict(arrowstyle='->', color='#1f77b4', lw=1.2))
    else:
        ep = 0.07
        ax.annotate(r'$2\sqrt{\kappa\varepsilon}$',
                    xy=(ep, delta_omega_ref(ep)),
                    xytext=(ep + 0.035, delta_omega_ref(ep) - 0.05),
                    fontsize=12, color='black',
                    arrowprops=dict(arrowstyle='->', color='black', lw=1.2))
        ep = 0.13
        ax.annotate(r'$\sim\!\varepsilon$',
                    xy=(ep, delta_omega_type1(ep)),
                    xytext=(ep + 0.025, delta_omega_type1(ep) + 0.035),
                    fontsize=12, color='#1f77b4',
                    arrowprops=dict(arrowstyle='->', color='#1f77b4', lw=1.2))

    ax.set_xlabel(r'$\varepsilon$', fontsize=14)
    ax.set_ylabel(r'$\Delta\omega$', fontsize=14)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.legend(fontsize=10, loc='upper left', framealpha=0.9)
    ax.tick_params(labelsize=11)
    ax.grid(True, alpha=0.2)

    suffix = " (zoomed)" if zoomed else ""
    ax.set_title(f'Circulator — Fig. 2b Splitting vs. Perturbation{suffix}',
                 fontsize=13)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    data_path = Path('data/paper circulator Csensing sweep (100-1600pf).xlsx')
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    print("=" * 65)
    print("Figure 2b — CIRCULATOR Topology")
    print("=" * 65)

    freq_mhz, traces = load_data(data_path)

    eps_awr = []
    dw_awr = []
    rows = []

    for c_eps_pf in sorted(traces.keys()):
        if c_eps_pf == 0:
            continue
        epsilon = c_eps_pf / (2.0 * C1_PF)
        f_minus, f_plus = find_two_peaks(freq_mhz, traces[c_eps_pf])
        if f_minus is None:
            print(f"  WARNING: no peaks for Cε = {c_eps_pf} pF")
            continue

        delta_f = f_plus - f_minus
        dw = delta_f / F0_MHZ
        dw_th = delta_omega_type2(epsilon)

        eps_awr.append(epsilon)
        dw_awr.append(dw)

        pct_err = (dw - dw_th) / dw_th * 100
        rows.append({
            'C_eps_pF': c_eps_pf,
            'epsilon': epsilon,
            'dw_AWR': dw,
            'dw_analytical': dw_th,
            'pct_error': pct_err,
        })

    eps_awr = np.array(eps_awr)
    dw_awr = np.array(dw_awr)

    # Power-law fit
    log_eps = np.log10(eps_awr)
    log_dw = np.log10(dw_awr)
    slope, intercept = np.polyfit(log_eps, log_dw, 1)
    A_fit = 10**intercept
    print(f"\nAWR power-law fit: Δω = {A_fit:.4f} × ε^{slope:.4f}")
    print(f"  Exponent = {slope:.4f} (theory: 0.5)")

    # Fine grids
    eps_full = np.linspace(1e-4, 0.25, 500)
    eps_zoom = np.linspace(1e-4, 0.10, 500)

    # Plots
    make_fig2b(eps_full, eps_awr, dw_awr,
               xlim=(0, 0.25), ylim=(0, None),
               output_path=output_dir / 'circulator_fig2b_full_range.png',
               zoomed=False)

    make_fig2b(eps_zoom, eps_awr[eps_awr <= 0.10], dw_awr[eps_awr <= 0.10],
               xlim=(0, 0.10), ylim=(0, 0.65),
               output_path=output_dir / 'circulator_fig2b_zoomed.png',
               zoomed=True)

    # Comparison table
    tbl = pd.DataFrame(rows)
    print(f"\n{'='*85}")
    print(f"{'Cε (pF)':>8} | {'ε':>10} | {'Δω AWR':>10} | {'Δω analyt.':>11} | "
          f"{'Error (%)':>10}")
    print(f"{'-'*85}")
    for _, r in tbl.iterrows():
        print(f"{r['C_eps_pF']:>8.0f} | {r['epsilon']:>10.6f} | "
              f"{r['dw_AWR']:>10.4f} | {r['dw_analytical']:>11.4f} | "
              f"{r['pct_error']:>10.2f}")
    print(f"{'='*85}")

    mean_abs_err = tbl['pct_error'].abs().mean()
    max_abs_err = tbl['pct_error'].abs().max()
    print(f"\nMean |error|: {mean_abs_err:.2f}%")
    print(f"Max  |error|: {max_abs_err:.2f}%")

    print(f"\n--- Comparison Summary ---")
    print(f"Power-law fit: Δω = {A_fit:.4f} × ε^{slope:.4f}")
    print(f"The circulator AWR data shows a fitted exponent of {slope:.4f}.")
    if abs(slope - 0.5) < 0.1:
        print(f"This is reasonably close to the theoretical 0.5 (EP square-root).")
    else:
        print(f"This deviates from the theoretical EP square-root value of 0.5,")
        print(f"indicating the circulator topology has different coupling dynamics.")

    csv_path = output_dir / 'circulator_fig2b_comparison.csv'
    tbl.to_csv(csv_path, index=False)
    print(f"\nTable saved to: {csv_path}")


if __name__ == '__main__':
    main()
