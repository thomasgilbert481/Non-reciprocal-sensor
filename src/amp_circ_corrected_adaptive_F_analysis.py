#!/usr/bin/env python3
"""
Amp Circuit Corrected Adaptive F — Bare Left-Tank Resonance Tracking
=====================================================================
F set to f_left = 1/(2pi*sqrt((C1+Csensing)*L)) for each Csensing,
which is the theoretically correct value to maintain gain-loss balance.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

OUTPUT_DIR = Path('output')
C1_PF      = 3200.0
L_NH       = 20.0

# Peak pairs read from AWR with F = bare left-tank resonance (GHz)
PEAKS_GHZ = {
    0:    (0.0200,  0.0317),
    100:  (0.0200,  0.0302),
    200:  (0.0200,  0.0289),
    300:  (0.0200,  0.0279),
    400:  (0.0200,  0.0270),
    500:  (0.0200,  0.0263),
    600:  (0.0196,  0.0257),
    700:  (0.0188,  0.0252),
    800:  (0.0187,  0.0247),
    900:  (0.01883, 0.0243),
    1000: (0.0180,  0.0240),
    1100: (0.0174,  0.0237),
    1200: (0.0173,  0.0235),
    1300: (0.01705, 0.0233),
    1400: (0.0168,  0.0231),
    1500: (0.0163,  0.0229),
    1600: (0.0162,  0.0228),
}


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    c_vals  = sorted(PEAKS_GHZ.keys())
    epsilon = np.array([c / (2.0 * C1_PF) for c in c_vals])
    f1_mhz  = np.array([PEAKS_GHZ[c][0] * 1000 for c in c_vals])
    f2_mhz  = np.array([PEAKS_GHZ[c][1] * 1000 for c in c_vals])
    delta_f = f2_mhz - f1_mhz

    # Theoretical F used (bare left-tank resonance)
    f_bare = 1 / (2*np.pi*np.sqrt((C1_PF + np.array(c_vals, dtype=float))*1e-12 * L_NH*1e-9)) / 1e6  # MHz

    df0      = delta_f[0]
    response = df0 - delta_f

    print("Csensing | ε        | F_bare(MHz)| f1 (MHz) | f2 (MHz) | Δf (MHz) | response")
    print("-" * 85)
    for i, c in enumerate(c_vals):
        print(f"  {c:5d}  | {epsilon[i]:.5f} | {f_bare[i]:10.3f} | {f1_mhz[i]:8.3f} | "
              f"{f2_mhz[i]:8.3f} | {delta_f[i]:8.3f} | {response[i]:+.3f}")

    # Fit all valid points (ε>0, response>0)
    valid = (epsilon > 0) & (response > 0)
    x_fit, y_fit = epsilon[valid], response[valid]
    slope, intercept = np.polyfit(np.log10(x_fit), np.log10(y_fit), 1)

    # Early-range fit (ε ≤ 0.10)
    valid_early = valid & (epsilon <= 0.10)
    x_early, y_early = epsilon[valid_early], response[valid_early]
    slope_early, intercept_early = np.polyfit(np.log10(x_early), np.log10(y_early), 1)

    print(f"\nΔf₀ = {df0:.3f} MHz")
    print(f"Slope — all {len(x_fit)} pts : {slope:.4f}  (EP theory = 0.50)")
    print(f"Slope — ε≤0.10 ({len(x_early)} pts): {slope_early:.4f}")

    # -----------------------------------------------------------------------
    # Plot 1 — Log-Log
    # -----------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 6))

    log_x, log_y = np.log10(x_fit), np.log10(y_fit)
    ax.plot(log_x, log_y, 'o', markersize=9, color='#1f77b4', zorder=5,
            label='Corrected adaptive F')

    lx = np.linspace(log_x.min(), log_x.max(), 300)
    ax.plot(lx, slope * lx + intercept, '-', color='#d62728', linewidth=2,
            label=f'Full fit  slope = {slope:.3f}')

    lx_e = np.linspace(np.log10(x_early.min()), np.log10(x_early.max()), 300)
    ax.plot(lx_e, slope_early * lx_e + intercept_early, '--', color='#ff7f0e', linewidth=2,
            label=f'Early fit (ε≤0.10)  slope = {slope_early:.3f}')

    # EP reference anchored at first point
    ref_ic = log_y[0] - 0.5 * log_x[0]
    ax.plot(lx, 0.5 * lx + ref_ic, ':', color='gray', linewidth=1.5,
            label='EP theory  slope = 0.50')

    ax.set_xlabel(r'$\log_{10}(\varepsilon)$  where  $\varepsilon = C_{\rm sensing}/(2C_1)$', fontsize=13)
    ax.set_ylabel(r'$\log_{10}(\Delta f_0 - \Delta f\ [\rm MHz])$', fontsize=14)
    ax.set_title('Corrected Adaptive F: Sensor Response vs $\\varepsilon$ (Log-Log)', fontsize=13)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.text(0.05, 0.25,
            f'Full slope = {slope:.3f}\nEarly slope = {slope_early:.3f}\nEP theory = 0.50',
            transform=ax.transAxes, fontsize=12, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.85))

    plt.tight_layout()
    out = OUTPUT_DIR / 'amp_circ_correctedF_loglog_response.png'
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out}")

    # -----------------------------------------------------------------------
    # Plot 2 — Linear
    # -----------------------------------------------------------------------
    fig2, ax2 = plt.subplots(figsize=(9, 6))
    ax2.plot(epsilon, response, 'o', markersize=9, color='#1f77b4', zorder=5,
             label='Corrected adaptive F')
    eps_c = np.linspace(1e-4, epsilon.max(), 300)
    ax2.plot(eps_c, 10**(slope * np.log10(eps_c) + intercept), '-', color='#d62728',
             linewidth=2, label=f'Full fit: $\\propto \\varepsilon^{{{slope:.3f}}}$')
    eps_e = np.linspace(1e-4, x_early.max(), 300)
    ax2.plot(eps_e, 10**(slope_early * np.log10(eps_e) + intercept_early), '--',
             color='#ff7f0e', linewidth=2,
             label=f'Early fit (ε≤0.10): $\\propto \\varepsilon^{{{slope_early:.3f}}}$')
    ax2.set_xlabel(r'$\varepsilon = C_{\rm sensing}/(2C_1)$', fontsize=14)
    ax2.set_ylabel(r'$\Delta f_0 - \Delta f$ (MHz)', fontsize=14)
    ax2.set_title('Corrected Adaptive F: Sensor Response vs $\\varepsilon$ (Linear)', fontsize=13)
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    out2 = OUTPUT_DIR / 'amp_circ_correctedF_linear_response.png'
    plt.savefig(out2, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out2}")

    # -----------------------------------------------------------------------
    # Plot 3 — Comparison: all three experiments on one log-log
    # -----------------------------------------------------------------------
    # Previous datasets (hardcoded for overlay)
    # Fixed F=0.02 GHz (original, ε≤0.15 slope=0.502)
    orig_cs  = [100,200,300,400,500,600,700,800,900,1000,1100,1200,1300,1400,1500,1600]
    orig_df0 = 12.0
    orig_df  = [10.2,9.0,8.1,7.2,7.3,6.4,6.8,6.4,5.7,6.7,7.0,7.2,7.1,6.55,7.1,7.3]
    # Use the published manual-override values from amp_circ_analysis.py
    fixed_peaks = {100:(20.0,30.2),200:(20.0,29.0),300:(19.9,27.9),400:(19.8,27.0),
                   500:(19.0,26.3),600:(18.6,25.7),700:(18.4,25.2),800:(18.3,24.7),
                   900:(18.0,24.3),1000:(17.5,24.2),1100:(17.1,24.1),1200:(16.4,23.6),
                   1300:(16.4,23.5),1400:(16.65,23.2),1500:(15.9,23.2),1600:(15.7,22.8)}
    fixed_cs_all = [0]+orig_cs
    fixed_df_all = [orig_df0] + [v[1]-v[0] for v in [fixed_peaks[c] for c in orig_cs]]
    fixed_eps    = np.array([c/(2*C1_PF) for c in fixed_cs_all])
    fixed_resp   = orig_df0 - np.array(fixed_df_all)

    fig3, ax3 = plt.subplots(figsize=(10, 7))

    # Fixed F (original) — only ε>0 and response>0
    fm = (fixed_eps > 0) & (fixed_resp > 0)
    ax3.plot(np.log10(fixed_eps[fm]), np.log10(fixed_resp[fm]),
             's', markersize=8, color='#2ca02c', alpha=0.7,
             label='Fixed F=0.02 GHz (original)')

    # Corrected adaptive F (current)
    ax3.plot(log_x, log_y, 'o', markersize=9, color='#1f77b4', zorder=5,
             label='Corrected adaptive F (bare resonance)')

    # Fits
    ax3.plot(lx, slope * lx + intercept, '-', color='#1f77b4', linewidth=1.5, alpha=0.7)
    ax3.plot(lx_e, slope_early * lx_e + intercept_early, '--', color='#ff7f0e',
             linewidth=2, label=f'Corrected F early fit  slope={slope_early:.3f}')

    # EP reference
    ax3.plot(lx, 0.5 * lx + ref_ic, ':', color='gray', linewidth=1.5,
             label='EP theory  slope=0.50')

    ax3.set_xlabel(r'$\log_{10}(\varepsilon)$', fontsize=13)
    ax3.set_ylabel(r'$\log_{10}(\Delta f_0 - \Delta f\ [\rm MHz])$', fontsize=14)
    ax3.set_title('Comparison: Fixed vs Corrected Adaptive F', fontsize=13)
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    out3 = OUTPUT_DIR / 'amp_circ_comparison_fixedVsAdaptiveF.png'
    plt.savefig(out3, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out3}")


if __name__ == '__main__':
    main()
