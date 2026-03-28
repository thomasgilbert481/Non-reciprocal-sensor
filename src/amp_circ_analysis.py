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
C1_PF       = 3200.0    # Left tank capacitor (pF)

# Manually verified peak frequencies (MHz) for all Csensing values.
# Format: Csensing_pF -> (f1_MHz, f2_MHz)  [values given in GHz, converted ×1000]
# Note: Csensing=0 has ε=0 — included in linear plot only (excluded from log-log)
# Note: Csensing=1100 not available
MANUAL_OVERRIDES = {
    0:    (20.0,  32.0),
    100:  (20.0,  30.2),
    200:  (20.0,  29.0),
    300:  (19.9,  27.9),
    400:  (19.8,  27.0),
    500:  (19.0,  26.3),
    600:  (18.6,  25.7),
    700:  (18.4,  25.2),
    800:  (18.3,  24.7),
    900:  (18.0,  24.3),
    1000: (17.5,  24.2),
    1100: (17.1,  24.1),
    1200: (16.4,  23.6),
    1300: (16.4,  23.5),
    1400: (16.65, 23.2),
    1500: (15.9,  23.2),
    1600: (15.7,  22.8),
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

    # --- extract splitting — manual overrides take priority over auto-detection ---
    all_csensing = sorted(set(list(MANUAL_OVERRIDES.keys()) + list(traces.keys())))
    results = []
    skipped = []
    for c_pf in all_csensing:
        if c_pf in MANUAL_OVERRIDES:
            f1, f2 = MANUAL_OVERRIDES[c_pf]
            src = 'manual'
        elif c_pf in traces:
            f1, f2 = find_two_peaks(freq_mhz, traces[c_pf])
            src = 'auto'
        else:
            continue

        if f1 is not None:
            delta_f = f2 - f1
            epsilon = c_pf / (2.0 * C1_PF)   # ε=0 when c_pf=0
            results.append({'Csensing_pF': c_pf, 'epsilon': epsilon,
                            'f1_MHz': f1, 'f2_MHz': f2,
                            'delta_f_MHz': delta_f, 'source': src})
            print(f"  Csensing={c_pf:5d} pF  →  f1={f1:.2f} MHz, f2={f2:.2f} MHz, "
                  f"Δf={delta_f:.2f} MHz  [{src}]")
        else:
            skipped.append(c_pf)
            print(f"  Csensing={c_pf:5d} pF  →  could not find 2 peaks (skipped)")

    if not results:
        print("ERROR: No valid peak pairs found.")
        return

    df = pd.DataFrame(results)

    # --- compute flipped response: ΔΔf = Δf[0] - Δf ---
    df0 = df['delta_f_MHz'].iloc[0]   # Δf at ε=0 (Csensing=0)
    df['response_MHz'] = df0 - df['delta_f_MHz']
    print(f"\nΔf[0] = {df0:.2f} MHz  →  response = Δf[0] - Δf")

    # --- log-log fit on response (exclude ε=0 and response<=0) ---
    x = df['epsilon'].values.astype(float)
    y = df['response_MHz'].values.astype(float)

    valid = (x > 0) & (y > 0)
    x_fit, y_fit = x[valid], y[valid]

    log_x = np.log10(x_fit)
    log_y = np.log10(y_fit)
    slope, intercept = np.polyfit(log_x, log_y, 1)
    fit_line = np.polyval([slope, intercept], log_x)

    print(f"Log-log slope = {slope:.4f}")

    # --- log-log plot ---
    fig, ax = plt.subplots(figsize=(9, 6))

    ax.plot(log_x, log_y, 'o', markersize=9, color='#1f77b4',
            zorder=5, label='Manually verified data')
    ax.plot(log_x, fit_line, '-', color='#d62728', linewidth=2,
            label=f'Linear fit  (slope = {slope:.3f})')

    ax.set_xlabel(r'$\log_{10}(\varepsilon)$  where  $\varepsilon = C_{\rm sensing}/(2C_1)$', fontsize=13)
    ax.set_ylabel(r'$\log_{10}(\Delta f_0 - \Delta f\ [\rm MHz])$', fontsize=14)
    ax.set_title(r'Amp Circuit: Sensor Response $(\Delta f_0 - \Delta f)$ vs $\varepsilon$ (Log-Log)',
                 fontsize=13)
    ax.legend(fontsize=11)
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

    # --- linear plot: response vs ε ---
    fig2, ax2 = plt.subplots(figsize=(9, 6))

    ax2.plot(df['epsilon'], df['response_MHz'],
             'o', markersize=9, color='#1f77b4', zorder=5,
             label='Manually verified data')

    # Power-law fit curve in linear space
    eps_range = np.linspace(0, x_fit.max(), 300)
    # avoid log(0): start from small value for the curve
    eps_curve = np.linspace(x_fit.min(), x_fit.max(), 300)
    resp_fit_curve = 10**(slope * np.log10(eps_curve) + intercept)
    ax2.plot(eps_curve, resp_fit_curve, '-', color='#d62728', linewidth=2,
             label=f'Fit: $\\propto \\varepsilon^{{{slope:.3f}}}$')

    ax2.legend(fontsize=11)
    ax2.set_xlabel(r'$\varepsilon = C_{\rm sensing}/(2C_1)$', fontsize=14)
    ax2.set_ylabel(r'$\Delta f_0 - \Delta f$ (MHz)', fontsize=14)
    ax2.set_title(r'Amp Circuit: Sensor Response $(\Delta f_0 - \Delta f)$ vs $\varepsilon$', fontsize=13)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path2 = OUTPUT_DIR / 'amp_circ_linear.png'
    plt.savefig(out_path2, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path2}")

    if skipped:
        print(f"\nSkipped {len(skipped)} traces (no 2 peaks): {skipped}")


if __name__ == '__main__':
    main()
