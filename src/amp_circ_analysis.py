#!/usr/bin/env python3
"""
Amp Circuit Csensing Sweep — Log-Log Plot
==========================================
Loads |S21| vs frequency data for the amplifier circuit swept over
Csensing (100–1600 pF), finds the two transmission peaks per trace,
computes the frequency splitting Δf, and produces a log-log plot with
the fitted power-law slope labelled.
"""

import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from pathlib import Path


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
DATA_FILE   = Path('data/Amp circ Csensing sweep (0-1600pf).xlsx')
OUTPUT_DIR  = Path('output')
FREQ_RANGE  = (5, 40)   # MHz — search window for peaks

# Manually identified peaks (MHz) for traces where auto-detection fails
# Format: Csensing_pF -> (f1_MHz, f2_MHz)
MANUAL_OVERRIDES = {
    600:  (19.0, 26.0),
    700:  (19.0, 25.0),
    800:  (18.0, 25.0),
    900:  (17.0, 24.0),
}


# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------
def load_data(filepath):
    df = pd.read_excel(filepath, header=0)
    freq_mhz = df.iloc[:, 0].values * 1000.0   # GHz → MHz

    traces = {}
    for col in df.columns[1:]:
        match = re.search(r'Csensing\s*=\s*(\d+)', col)
        if match:
            traces[int(match.group(1))] = df[col].values

    return freq_mhz, traces


# ---------------------------------------------------------------------------
# PEAK DETECTION
# ---------------------------------------------------------------------------
def find_two_peaks(freq, s21, freq_range=FREQ_RANGE):
    """Return (f_low, f_high) in MHz for the two dominant peaks."""
    mask = (freq >= freq_range[0]) & (freq <= freq_range[1])
    f, v = freq[mask], s21[mask]
    if len(f) < 4:
        return None, None

    step = f[1] - f[0]
    min_dist = max(2, int(1.0 / step))

    for prom in [0.5, 0.1, 0.05, 0.01, 0.005, 0.001, 0.0005, 0.0001, 0.00001]:
        peaks, _ = find_peaks(v, prominence=prom, distance=min_dist)
        if len(peaks) >= 2:
            top2 = peaks[v[peaks].argsort()[-2:]]
            p1, p2 = sorted(top2)
            return float(f[p1]), float(f[p2])

    return None, None


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("Loading data...")
    freq_mhz, traces = load_data(DATA_FILE)
    print(f"  {len(traces)} traces, freq {freq_mhz[0]:.1f}–{freq_mhz[-1]:.1f} MHz")

    # --- extract splitting for each Csensing ---
    results = []
    skipped = []
    for c_pf in sorted(traces):
        if c_pf in MANUAL_OVERRIDES:
            f1, f2 = MANUAL_OVERRIDES[c_pf]
            src = 'manual'
        else:
            f1, f2 = find_two_peaks(freq_mhz, traces[c_pf])
            src = 'auto'

        if f1 is not None:
            delta_f = f2 - f1
            results.append({'Csensing_pF': c_pf, 'f1_MHz': f1,
                            'f2_MHz': f2, 'delta_f_MHz': delta_f,
                            'source': src})
            print(f"  Csensing={c_pf:5d} pF  →  f1={f1:.2f} MHz, f2={f2:.2f} MHz, "
                  f"Δf={delta_f:.2f} MHz  [{src}]")
        else:
            skipped.append(c_pf)
            print(f"  Csensing={c_pf:5d} pF  →  could not find 2 peaks (skipped)")

    if not results:
        print("ERROR: No valid peak pairs found.")
        return

    df = pd.DataFrame(results)

    # --- log-log fit ---
    x = df['Csensing_pF'].values.astype(float)
    y = df['delta_f_MHz'].values.astype(float)

    valid = (x > 0) & (y > 0)
    x_fit, y_fit = x[valid], y[valid]

    log_x = np.log10(x_fit)
    log_y = np.log10(y_fit)
    slope, intercept = np.polyfit(log_x, log_y, 1)
    fit_line = np.polyval([slope, intercept], log_x)

    print(f"\nLog-log slope = {slope:.4f}")

    # --- plot ---
    fig, ax = plt.subplots(figsize=(9, 6))

    for _, row in df.iterrows():
        lx = np.log10(row['Csensing_pF'])
        ly = np.log10(row['delta_f_MHz'])
        marker = 's' if row.get('source') == 'manual' else 'o'
        color  = '#ff7f0e' if row['Csensing_pF'] >= 1500 else '#1f77b4'
        ax.plot(lx, ly, marker, markersize=9, color=color, zorder=5)

    ax.plot(log_x, fit_line, '-', color='#d62728', linewidth=2,
            label=f'Linear fit  (slope = {slope:.3f})')

    # Shade EP region (600–1400 pF — single peak, coalesced modes)
    ax.axvspan(np.log10(550), np.log10(1450), color='grey', alpha=0.15,
               label='EP region (single peak, 600–1400 pF)')

    # Legend proxies for the two data groups
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0],[0], marker='o', color='w', markerfacecolor='#1f77b4',
               markersize=9, label='Auto-detected peaks'),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#1f77b4',
               markersize=9, label='Manually identified peaks'),
        Line2D([0],[0], marker='o', color='w', markerfacecolor='#ff7f0e',
               markersize=9, label='Two peaks  (≥ 1500 pF)'),
        Line2D([0],[0], color='#d62728', linewidth=2,
               label=f'Linear fit  (slope = {slope:.3f})'),
    ]
    ax.legend(handles=handles, fontsize=10)

    ax.set_xlabel(r'$\log_{10}(C_{\rm sensing}\ [\rm pF])$', fontsize=14)
    ax.set_ylabel(r'$\log_{10}(\Delta f\ [\rm MHz])$', fontsize=14)
    ax.set_title('Amp Circuit: Frequency Splitting vs Perturbation (Log-Log)',
                 fontsize=13)
    ax.grid(True, alpha=0.3)

    ax.text(0.05, 0.95,
            f'Measured slope = {slope:.3f}\n(EP theory = 0.50)',
            transform=ax.transAxes, fontsize=12, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.85))

    plt.tight_layout()
    out_path = OUTPUT_DIR / 'amp_circ_loglog.png'
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")

    if skipped:
        print(f"\nSkipped {len(skipped)} traces (no 2 peaks): {skipped}")


if __name__ == '__main__':
    main()
