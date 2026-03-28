#!/usr/bin/env python3
"""
Amp Circuit F=0 (Broadband Amplifier) — Csensing Sweep Analysis
================================================================
Manually read peak frequencies from AWR simulation with F=0 GHz (flat gain).
Computes epsilon vs (Δf₀ - Δf) and fits all valid points.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

OUTPUT_DIR = Path('output')
C1_PF      = 3200.0   # Left tank capacitor (pF)

# Manually read peak pairs from AWR (GHz), all 17 points including Csensing=0
# Format: Csensing_pF -> (f1_GHz, f2_GHz)
PEAKS_GHZ = {
    0:    (0.0200, 0.0320),
    100:  (0.0198, 0.0372),   # NOTE: anomalous — Δf larger than baseline
    200:  (0.0194, 0.0306),
    300:  (0.0184, 0.0294),
    400:  (0.0188, 0.0293),
    500:  (0.0184, 0.0289),
    600:  (0.0180, 0.0285),
    700:  (0.0176, 0.0281),
    800:  (0.0172, 0.0277),
    900:  (0.0169, 0.0274),
    1000: (0.0165, 0.0272),
    1100: (0.0162, 0.0269),
    1200: (0.0159, 0.0267),
    1300: (0.0156, 0.0265),
    1400: (0.0153, 0.0264),
    1500: (0.0150, 0.0262),
    1600: (0.0148, 0.0262),
}


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    c_vals  = sorted(PEAKS_GHZ.keys())
    epsilon = np.array([c / (2.0 * C1_PF) for c in c_vals])
    f1_mhz  = np.array([PEAKS_GHZ[c][0] * 1000 for c in c_vals])
    f2_mhz  = np.array([PEAKS_GHZ[c][1] * 1000 for c in c_vals])
    delta_f = f2_mhz - f1_mhz

    df0      = delta_f[0]           # Δf at ε=0
    response = df0 - delta_f        # Δf₀ - Δf

    print("Csensing | ε        | f1 (MHz) | f2 (MHz) | Δf (MHz) | response (MHz)")
    print("-" * 75)
    for i, c in enumerate(c_vals):
        print(f"  {c:5d}  | {epsilon[i]:.5f} | {f1_mhz[i]:8.2f} | {f2_mhz[i]:8.2f} | "
              f"{delta_f[i]:8.2f} | {response[i]:+.2f}")

    # -----------------------------------------------------------------------
    # Log-log fit: exclude ε=0 (response=0) and negative responses
    # Csensing=100 gives response = -5.4 MHz (anomalous), excluded automatically
    # -----------------------------------------------------------------------
    valid = (epsilon > 0) & (response > 0)
    x_fit, y_fit = epsilon[valid], response[valid]

    if len(x_fit) >= 2:
        log_x, log_y   = np.log10(x_fit), np.log10(y_fit)
        slope, intercept = np.polyfit(log_x, log_y, 1)
        print(f"\nLog-log slope (valid {len(x_fit)} pts) = {slope:.4f}")
    else:
        slope, intercept = 0.0, 0.0
        print("\nWARNING: not enough valid points for fit.")

    # -----------------------------------------------------------------------
    # Plot 1 — Linear: response vs ε (all 17 points)
    # -----------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 6))

    colors = ['#d62728' if r < 0 else '#1f77b4' for r in response]
    for xi, yi, ci in zip(epsilon, response, colors):
        ax.plot(xi, yi, 'o', markersize=9, color=ci, zorder=5)

    # dummy handles for legend
    ax.plot([], [], 'o', color='#1f77b4', markersize=9, label='Data (response > 0)')
    ax.plot([], [], 'o', color='#d62728', markersize=9, label='Anomalous (response < 0)')

    # fit curve over valid range
    if len(x_fit) >= 2:
        eps_curve = np.linspace(1e-4, epsilon.max(), 300)
        ax.plot(eps_curve, 10**(slope * np.log10(eps_curve) + intercept),
                '-', color='#2ca02c', linewidth=2,
                label=f'Fit: $\\propto \\varepsilon^{{{slope:.3f}}}$  (valid pts only)')

    ax.axhline(0, color='gray', linewidth=0.8, linestyle='--')
    ax.set_xlabel(r'$\varepsilon = C_{\rm sensing}/(2C_1)$', fontsize=14)
    ax.set_ylabel(r'$\Delta f_0 - \Delta f$ (MHz)', fontsize=14)
    ax.set_title('Amp Circuit F=0: Sensor Response vs $\\varepsilon$ (Linear)', fontsize=13)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.text(0.97, 0.97,
            f'Slope = {slope:.3f}\n(EP theory = 0.50)',
            transform=ax.transAxes, fontsize=12,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.85))

    plt.tight_layout()
    out = OUTPUT_DIR / 'amp_circ_F0_linear_response.png'
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out}")

    # -----------------------------------------------------------------------
    # Plot 2 — Log-Log: response vs ε (valid points only)
    # -----------------------------------------------------------------------
    fig2, ax2 = plt.subplots(figsize=(9, 6))

    ax2.plot(np.log10(x_fit), np.log10(y_fit),
             'o', markersize=9, color='#1f77b4', zorder=5, label='Data (response > 0)')

    if len(x_fit) >= 2:
        log_x_curve = np.linspace(np.log10(x_fit.min()), np.log10(x_fit.max()), 300)
        ax2.plot(log_x_curve, slope * log_x_curve + intercept,
                 '-', color='#d62728', linewidth=2,
                 label=f'Linear fit  (slope = {slope:.3f})')

    ax2.set_xlabel(r'$\log_{10}(\varepsilon)$  where  $\varepsilon = C_{\rm sensing}/(2C_1)$', fontsize=13)
    ax2.set_ylabel(r'$\log_{10}(\Delta f_0 - \Delta f\ [\rm MHz])$', fontsize=14)
    ax2.set_title('Amp Circuit F=0: Sensor Response vs $\\varepsilon$ (Log-Log)', fontsize=13)
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.text(0.05, 0.95,
             f'Measured slope = {slope:.3f}\n(EP theory = 0.50)',
             transform=ax2.transAxes, fontsize=12, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.85))

    plt.tight_layout()
    out2 = OUTPUT_DIR / 'amp_circ_F0_loglog_response.png'
    plt.savefig(out2, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out2}")

    # -----------------------------------------------------------------------
    # Plot 3 — Raw Δf vs ε (to show the overall trend clearly)
    # -----------------------------------------------------------------------
    fig3, ax3 = plt.subplots(figsize=(9, 6))
    ax3.plot(epsilon, delta_f, 'o-', markersize=9, color='#1f77b4',
             linewidth=1.5, zorder=5, label='Δf (measured)')
    ax3.axhline(df0, color='gray', linewidth=1, linestyle='--',
                label=f'Baseline Δf₀ = {df0:.1f} MHz')
    ax3.set_xlabel(r'$\varepsilon = C_{\rm sensing}/(2C_1)$', fontsize=14)
    ax3.set_ylabel(r'$\Delta f$ (MHz)', fontsize=14)
    ax3.set_title('Amp Circuit F=0: Raw Frequency Splitting vs $\\varepsilon$', fontsize=13)
    ax3.legend(fontsize=11)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    out3 = OUTPUT_DIR / 'amp_circ_F0_raw_deltaf.png'
    plt.savefig(out3, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out3}")


if __name__ == '__main__':
    main()
