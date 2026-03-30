#!/usr/bin/env python3
"""
Amp Circuit — Matched Frequency (True EP) Analysis
====================================================
Both tanks set to same resonant frequency (C1=C2=3200 pF, L=20 nH).
At Csensing=0 the system is at the EP (single merged peak).
As Csensing increases, coupling grows and two peaks emerge.

Outputs:
  output/ep_matched_spectra_grid.png      — all 16 S21 spectra in dB, peaks marked
  output/ep_matched_spectrum_XXXX.png     — individual detailed view per Csensing
  output/ep_matched_loglog.png            — log-log Δf vs ε
  output/ep_matched_linear.png            — linear Δf vs ε
"""

import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.signal import find_peaks
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
DATA_FILE  = Path('data/amp circ Csensing sweep Matched Freq (0-1600pf).xlsx')
OUTPUT_DIR = Path('output')
INDIV_DIR  = OUTPUT_DIR / 'ep_matched_spectra'
C1_PF      = 3200.0          # both tanks (pF)
FREQ_LO    = 1.0             # MHz — low cut (exclude DC artefact)
FREQ_HI    = 25.0            # MHz

# Manual peak overrides: Csensing_pF -> (f1_MHz, f2_MHz) or (f1_MHz,) for single
# Fill these in after visual inspection if auto-detection is wrong
MANUAL_OVERRIDES = {
    # e.g.  300: (19.3, 19.9),
}


# ---------------------------------------------------------------------------
# LOAD
# ---------------------------------------------------------------------------
def load_data(filepath):
    df = pd.read_excel(filepath, header=0)
    freq_mhz = df.iloc[:, 0].values * 1000.0        # GHz → MHz
    traces = {}
    for col in df.columns[1:]:
        m = re.search(r'Csensing\s*=\s*(\d+)', col)
        if m:
            traces[int(m.group(1))] = df[col].values   # already dB
    return freq_mhz, traces


# ---------------------------------------------------------------------------
# PEAK DETECTION  (dB scale)
# ---------------------------------------------------------------------------
def find_peaks_db(freq, s21_db, freq_lo=FREQ_LO, freq_hi=FREQ_HI):
    """Return list of peak frequencies (MHz) found in window, best 2 only."""
    mask = (freq >= freq_lo) & (freq <= freq_hi)
    f, v = freq[mask], s21_db[mask]
    if len(f) < 4:
        return []

    step = f[1] - f[0]
    min_dist = max(3, int(0.3 / step))   # at least 0.3 MHz apart

    for prom in [5, 3, 1, 0.5, 0.2, 0.1, 0.05]:
        peaks, _ = find_peaks(v, prominence=prom, distance=min_dist)
        if len(peaks) >= 2:
            top2 = peaks[v[peaks].argsort()[-2:]]
            p1, p2 = sorted(top2)
            return [float(f[p1]), float(f[p2])]
        if len(peaks) == 1:
            # keep trying lower prominence before giving up
            continue

    # Only one peak found at lowest prominence
    peaks, _ = find_peaks(v, prominence=0.02, distance=min_dist)
    if len(peaks):
        return [float(f[peaks[v[peaks].argmax()]])]
    return []


# ---------------------------------------------------------------------------
# INDIVIDUAL SPECTRUM PLOT
# ---------------------------------------------------------------------------
def plot_spectrum(freq, s21_db, csensing, peak_freqs, out_path,
                  freq_lo=FREQ_LO, freq_hi=FREQ_HI):
    mask = (freq >= freq_lo) & (freq <= freq_hi)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(freq[mask], s21_db[mask], color='#1f77b4', linewidth=1.2)

    colors = ['#d62728', '#2ca02c']
    for i, fp in enumerate(peak_freqs):
        ax.axvline(fp, color=colors[i % 2], linewidth=1.5, linestyle='--',
                   label=f'Peak {i+1}: {fp:.3f} MHz')

    if len(peak_freqs) == 2:
        df_val = peak_freqs[1] - peak_freqs[0]
        ax.set_title(f'Csensing = {csensing} pF   Δf = {df_val:.3f} MHz', fontsize=12)
    elif len(peak_freqs) == 1:
        ax.set_title(f'Csensing = {csensing} pF   (single peak at {peak_freqs[0]:.3f} MHz)', fontsize=12)
    else:
        ax.set_title(f'Csensing = {csensing} pF   (no peak found)', fontsize=12)

    ax.set_xlabel('Frequency (MHz)', fontsize=11)
    ax.set_ylabel('|S21| (dB)', fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    INDIV_DIR.mkdir(exist_ok=True)

    print('Loading data...')
    freq, traces = load_data(DATA_FILE)
    c_vals = sorted(traces.keys())
    print(f'  {len(c_vals)} traces, freq {freq[0]:.1f}–{freq[-1]:.1f} MHz, '
          f'step {(freq[1]-freq[0]):.4f} MHz')

    # --- detect peaks for each Csensing ---
    results = []
    for cs in c_vals:
        if cs in MANUAL_OVERRIDES:
            pf = list(MANUAL_OVERRIDES[cs])
        else:
            pf = find_peaks_db(freq, traces[cs])

        n = len(pf)
        df_val = (pf[1] - pf[0]) if n >= 2 else None
        eps    = cs / (2.0 * C1_PF)
        results.append(dict(Csensing=cs, epsilon=eps,
                            f1=pf[0] if n >= 1 else None,
                            f2=pf[1] if n >= 2 else None,
                            delta_f=df_val, n_peaks=n))

        status = f'Δf={df_val:.3f} MHz' if df_val else 'SINGLE PEAK'
        print(f'  Csensing={cs:5d} pF  ε={eps:.4f}  {status}')

        # individual plot
        plot_spectrum(freq, traces[cs], cs, pf,
                      INDIV_DIR / f'ep_matched_spectrum_{cs:04d}pF.png')

    # --- overview grid ---
    ncols = 4
    nrows = int(np.ceil(len(c_vals) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, nrows * 3))
    axes = axes.flatten()
    mask_plot = (freq >= FREQ_LO) & (freq <= FREQ_HI)

    for idx, (cs, r) in enumerate(zip(c_vals, results)):
        ax = axes[idx]
        ax.plot(freq[mask_plot], traces[cs][mask_plot],
                color='#1f77b4', linewidth=0.9)
        pf = [x for x in [r['f1'], r['f2']] if x is not None]
        for i, fp in enumerate(pf):
            ax.axvline(fp, color=['#d62728','#2ca02c'][i],
                       linewidth=1.2, linestyle='--')
        title = f'{cs} pF'
        if r['delta_f']:
            title += f'\nΔf={r["delta_f"]:.2f} MHz'
        else:
            title += '\n(single peak)'
        ax.set_title(title, fontsize=8)
        ax.set_xlabel('MHz', fontsize=7)
        ax.set_ylabel('dB', fontsize=7)
        ax.tick_params(labelsize=6)
        ax.grid(True, alpha=0.2)

    for idx in range(len(c_vals), len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle('Matched-Freq EP Circuit: S21 spectra (dB) — all Csensing values',
                 fontsize=13, y=1.01)
    plt.tight_layout()
    grid_path = OUTPUT_DIR / 'ep_matched_spectra_grid.png'
    plt.savefig(grid_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f'\nSaved grid: {grid_path}')

    # --- log-log and linear fit (only two-peak entries) ---
    df_res = pd.DataFrame(results)
    valid  = df_res[df_res['delta_f'].notna() & (df_res['epsilon'] > 0)].copy()

    print(f'\nTwo-peak entries: {len(valid)} / {len(results)}')

    if len(valid) >= 3:
        x = valid['epsilon'].values.astype(float)
        y = valid['delta_f'].values.astype(float)
        log_x, log_y = np.log10(x), np.log10(y)
        slope, intercept = np.polyfit(log_x, log_y, 1)
        print(f'Log-log slope = {slope:.4f}  (EP theory = 0.50)')

        # log-log plot
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.plot(log_x, log_y, 'o', markersize=10, color='#1f77b4',
                zorder=5, label='Data (2 peaks detected)')
        lx = np.linspace(log_x.min(), log_x.max(), 300)
        ax.plot(lx, slope * lx + intercept, '-', color='#d62728',
                linewidth=2, label=f'Fit  slope = {slope:.3f}')
        # EP theory reference
        ref_ic = log_y[0] - 0.5 * log_x[0]
        ax.plot(lx, 0.5 * lx + ref_ic, ':', color='gray',
                linewidth=1.5, label='EP theory  slope = 0.50')
        ax.set_xlabel(r'$\log_{10}(\varepsilon)$  where  $\varepsilon=C_{\rm sensing}/(2C_1)$',
                      fontsize=13)
        ax.set_ylabel(r'$\log_{10}(\Delta f\ [\rm MHz])$', fontsize=14)
        ax.set_title('Matched-Freq EP Circuit: $\\Delta f$ vs $\\varepsilon$ (Log-Log)',
                     fontsize=13)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.text(0.05, 0.25,
                f'Slope = {slope:.3f}\nEP theory = 0.50',
                transform=ax.transAxes, fontsize=12, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.85))
        plt.tight_layout()
        out_ll = OUTPUT_DIR / 'ep_matched_loglog.png'
        plt.savefig(out_ll, dpi=300, bbox_inches='tight')
        plt.close()
        print(f'Saved: {out_ll}')

        # linear plot
        fig2, ax2 = plt.subplots(figsize=(9, 6))
        ax2.plot(valid['epsilon'], valid['delta_f'], 'o', markersize=10,
                 color='#1f77b4', zorder=5, label='Data (2 peaks detected)')
        eps_c = np.linspace(1e-4, x.max(), 300)
        ax2.plot(eps_c, 10**(slope * np.log10(eps_c) + intercept),
                 '-', color='#d62728', linewidth=2,
                 label=f'Fit: $\\Delta f \\propto \\varepsilon^{{{slope:.3f}}}$')
        ax2.set_xlabel(r'$\varepsilon = C_{\rm sensing}/(2C_1)$', fontsize=14)
        ax2.set_ylabel(r'$\Delta f$ (MHz)', fontsize=14)
        ax2.set_title('Matched-Freq EP Circuit: $\\Delta f$ vs $\\varepsilon$ (Linear)',
                      fontsize=13)
        ax2.legend(fontsize=11)
        ax2.grid(True, alpha=0.3)
        plt.tight_layout()
        out_lin = OUTPUT_DIR / 'ep_matched_linear.png'
        plt.savefig(out_lin, dpi=300, bbox_inches='tight')
        plt.close()
        print(f'Saved: {out_lin}')
    else:
        print('Not enough two-peak entries for fitting — check individual spectrum plots.')
        print(f'Individual plots saved to: {INDIV_DIR}/')

    print(f'\nAll individual spectra: {INDIV_DIR}/')


if __name__ == '__main__':
    main()
