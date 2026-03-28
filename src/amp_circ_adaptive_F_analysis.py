#!/usr/bin/env python3
"""
Amp Circuit Adaptive F — Csensing Sweep Analysis
=================================================
F is tuned to track f1 for each Csensing value, maintaining gain-loss
balance across the full perturbation range. Tests whether EP slope ≈ 0.5
is recovered when bandwidth is not a limitation.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

OUTPUT_DIR = Path('output')
C1_PF      = 3200.0   # Left tank capacitor (pF)

# Manually read peak pairs from AWR with adaptive F (GHz)
# Format: Csensing_pF -> (f1_GHz, f2_GHz)
PEAKS_GHZ = {
    0:    (0.0200,  0.0317),
    100:  (0.0200,  0.0302),
    200:  (0.0200,  0.0289),
    300:  (0.0200,  0.0279),
    400:  (0.0200,  0.0270),
    500:  (0.0202,  0.0263),
    600:  (0.0190,  0.0257),
    700:  (0.01864, 0.0252),
    800:  (0.01912, 0.0247),
    900:  (0.0186,  0.0243),
    1000: (0.0182,  0.0240),
    1100: (0.0178,  0.0237),
    1200: (0.0174,  0.0235),
    1300: (0.0171,  0.0232),
    1400: (0.0169,  0.0231),
    1500: (0.0164,  0.0229),
    1600: (0.0162,  0.0228),
}


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    c_vals  = sorted(PEAKS_GHZ.keys())
    epsilon = np.array([c / (2.0 * C1_PF) for c in c_vals])
    f1_mhz  = np.array([PEAKS_GHZ[c][0] * 1000 for c in c_vals])
    f2_mhz  = np.array([PEAKS_GHZ[c][1] * 1000 for c in c_vals])
    delta_f = f2_mhz - f1_mhz

    df0      = delta_f[0]
    response = df0 - delta_f

    print("Csensing | ε        | f1 (MHz) | f2 (MHz) | Δf (MHz) | response (MHz)")
    print("-" * 75)
    for i, c in enumerate(c_vals):
        print(f"  {c:5d}  | {epsilon[i]:.5f} | {f1_mhz[i]:8.3f} | {f2_mhz[i]:8.3f} | "
              f"{delta_f[i]:8.3f} | {response[i]:+.3f}")

    # Log-log fit — all points with ε>0 and response>0
    valid = (epsilon > 0) & (response > 0)
    x_fit, y_fit = epsilon[valid], response[valid]

    log_x, log_y   = np.log10(x_fit), np.log10(y_fit)
    slope, intercept = np.polyfit(log_x, log_y, 1)
    print(f"\nΔf₀ = {df0:.2f} MHz")
    print(f"Log-log slope (all {len(x_fit)} valid pts) = {slope:.4f}  (EP theory = 0.50)")

    # Also fit only early points (ε ≤ 0.10) where response is most linear in log space
    valid_early = valid & (epsilon <= 0.10)
    x_early, y_early = epsilon[valid_early], response[valid_early]
    if len(x_early) >= 2:
        slope_early, intercept_early = np.polyfit(np.log10(x_early), np.log10(y_early), 1)
        print(f"Log-log slope (ε ≤ 0.10, {len(x_early)} pts) = {slope_early:.4f}")
    else:
        slope_early = None

    # -----------------------------------------------------------------------
    # Plot 1 — Log-Log
    # -----------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 6))

    ax.plot(log_x, log_y, 'o', markersize=9, color='#1f77b4',
            zorder=5, label='Adaptive F data (all valid)')

    # Full fit line
    lx_curve = np.linspace(log_x.min(), log_x.max(), 300)
    ax.plot(lx_curve, slope * lx_curve + intercept,
            '-', color='#d62728', linewidth=2,
            label=f'Full fit  slope = {slope:.3f}')

    # Early-range fit line
    if slope_early is not None:
        lx_early_curve = np.linspace(np.log10(x_early.min()), np.log10(x_early.max()), 300)
        ax.plot(lx_early_curve, slope_early * lx_early_curve + intercept_early,
                '--', color='#ff7f0e', linewidth=2,
                label=f'Early fit (ε≤0.10)  slope = {slope_early:.3f}')

    # EP reference line (slope = 0.5) anchored at first point
    lx_ref = np.linspace(log_x.min(), log_x.max(), 300)
    ref_intercept = log_y[0] - 0.5 * log_x[0]
    ax.plot(lx_ref, 0.5 * lx_ref + ref_intercept,
            ':', color='gray', linewidth=1.5, label='EP theory  slope = 0.50')

    ax.set_xlabel(r'$\log_{10}(\varepsilon)$  where  $\varepsilon = C_{\rm sensing}/(2C_1)$', fontsize=13)
    ax.set_ylabel(r'$\log_{10}(\Delta f_0 - \Delta f\ [\rm MHz])$', fontsize=14)
    ax.set_title('Amp Circuit Adaptive F: Sensor Response vs $\\varepsilon$ (Log-Log)', fontsize=13)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.text(0.05, 0.25,
            f'Full slope = {slope:.3f}\nEP theory = 0.50',
            transform=ax.transAxes, fontsize=12, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.85))

    plt.tight_layout()
    out = OUTPUT_DIR / 'amp_circ_adaptiveF_loglog_response.png'
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out}")

    # -----------------------------------------------------------------------
    # Plot 2 — Linear: response vs ε
    # -----------------------------------------------------------------------
    fig2, ax2 = plt.subplots(figsize=(9, 6))

    ax2.plot(epsilon, response, 'o', markersize=9, color='#1f77b4',
             zorder=5, label='Adaptive F data')

    eps_curve = np.linspace(1e-4, epsilon.max(), 300)
    ax2.plot(eps_curve, 10**(slope * np.log10(eps_curve) + intercept),
             '-', color='#d62728', linewidth=2,
             label=f'Fit: $\\propto \\varepsilon^{{{slope:.3f}}}$')

    if slope_early is not None:
        eps_early_curve = np.linspace(1e-4, x_early.max(), 300)
        ax2.plot(eps_early_curve, 10**(slope_early * np.log10(eps_early_curve) + intercept_early),
                 '--', color='#ff7f0e', linewidth=2,
                 label=f'Early fit (ε≤0.10): $\\propto \\varepsilon^{{{slope_early:.3f}}}$')

    ax2.set_xlabel(r'$\varepsilon = C_{\rm sensing}/(2C_1)$', fontsize=14)
    ax2.set_ylabel(r'$\Delta f_0 - \Delta f$ (MHz)', fontsize=14)
    ax2.set_title('Amp Circuit Adaptive F: Sensor Response vs $\\varepsilon$ (Linear)', fontsize=13)
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    out2 = OUTPUT_DIR / 'amp_circ_adaptiveF_linear_response.png'
    plt.savefig(out2, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out2}")

    # -----------------------------------------------------------------------
    # Plot 3 — Raw Δf vs ε
    # -----------------------------------------------------------------------
    fig3, ax3 = plt.subplots(figsize=(9, 6))
    ax3.plot(epsilon, delta_f, 'o-', markersize=9, color='#1f77b4',
             linewidth=1.5, label='Δf (adaptive F)')
    ax3.axhline(df0, color='gray', linewidth=1, linestyle='--',
                label=f'Baseline Δf₀ = {df0:.2f} MHz')
    ax3.set_xlabel(r'$\varepsilon = C_{\rm sensing}/(2C_1)$', fontsize=14)
    ax3.set_ylabel(r'$\Delta f$ (MHz)', fontsize=14)
    ax3.set_title('Amp Circuit Adaptive F: Raw Frequency Splitting vs $\\varepsilon$', fontsize=13)
    ax3.legend(fontsize=11)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    out3 = OUTPUT_DIR / 'amp_circ_adaptiveF_raw_deltaf.png'
    plt.savefig(out3, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out3}")


if __name__ == '__main__':
    main()
