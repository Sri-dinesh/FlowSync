"""
Script to generate publication-quality figures for the FlowSync-UQ IEEE manuscript.
Saves figures into IEEE-conference-template-062824/ as high-resolution PNGs.
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUTPUT_DIR = "/home/dracarys/Projects/personal-stuff/FlowSync/IEEE-conference-template-062824"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Set publication style
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans', 'Arial', 'Helvetica'],
    'font.size': 9,
    'axes.labelsize': 10,
    'axes.titlesize': 10,
    'xtick.labelsize': 8.5,
    'ytick.labelsize': 8.5,
    'legend.fontsize': 8.5,
    'figure.titlesize': 11,
    'lines.linewidth': 1.8,
    'axes.linewidth': 0.8,
    'grid.linewidth': 0.5,
    'grid.alpha': 0.6,
})

# -------------------------------------------------------------
# Figure 1: System Architecture Diagram
# -------------------------------------------------------------
def generate_fig1_architecture():
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=300)
    ax.axis('off')

    # Color palette
    c_perc = '#E8F0FE'
    c_perc_b = '#1A73E8'
    c_drl = '#E6F4EA'
    c_drl_b = '#137333'
    c_uq = '#FEF7E0'
    c_uq_b = '#EA8600'
    c_fb = '#FCE8E6'
    c_fb_b = '#C5221F'
    c_safe = '#F3E8FD'
    c_safe_b = '#7627BB'

    boxes = [
        # (x, y, w, h, title, subtitle, fill, border)
        (0.02, 0.52, 0.16, 0.40, 'Roadside Video\n(Monocular CCTV)', '10-30 FPS RGB\nStrict FOV (d<=0.45)', c_perc, c_perc_b),
        (0.22, 0.52, 0.18, 0.40, 'Perception Pipeline\n(YOLOv8 + ByteTrack)', 'Detection (conf>=0.25)\nKalman Multi-Tracking\nHomography Projection', c_perc, c_perc_b),
        (0.44, 0.52, 0.16, 0.40, 'Camera State\nBuilder (s_t^cam)', '28-D Feature Vector\n12 Lane Corridors\nZero Oracle Leakage', c_perc, c_perc_b),
        
        # Parallel branches
        (0.64, 0.58, 0.16, 0.36, 'Nominal D3QN\nPolicy Agent', 'Dueling Double DQN\nMasked Centering\nPER Sampling', c_drl, c_drl_b),
        (0.64, 0.10, 0.16, 0.36, '7-Cue Perception\nUncertainty Engine', 'Dispersion, Volatility,\nLatency, Age, Drops\nPlatt Scaling (T=1.2)', c_uq, c_uq_b),
        
        # Supervisor and Fallback
        (0.44, 0.10, 0.16, 0.36, 'Max-Pressure\nQueuing Fallback', 'Pressure Balancing\nVaraiya Formulation\nAnalytic Stability', c_fb, c_fb_b),
        
        # Two-tier safety
        (0.84, 0.52, 0.15, 0.42, 'Hysteretic Supervisor\n& Safety Shield', 'tau_high=0.65, tau_low=0.5\nDwell=8s, Anti-Starv (45s)\nMax Green (60s)', c_safe, c_safe_b),
        (0.84, 0.06, 0.15, 0.38, 'PhysicalSignalFSM\n(Hardware Layer)', 'Non-Preempt G_min=8s\nYellow=3s, All-Red=1s\n0 Executed Violations', c_safe, c_safe_b),
    ]

    for (bx, by, bw, bh, title, sub, fill, border) in boxes:
        rect = plt.Rectangle((bx, by), bw, bh, facecolor=fill, edgecolor=border, linewidth=1.4, transform=ax.transAxes, zorder=2)
        ax.add_patch(rect)
        ax.text(bx + bw/2, by + bh*0.68, title, ha='center', va='center', fontsize=7.5, fontweight='bold', color=border, transform=ax.transAxes, zorder=3)
        ax.text(bx + bw/2, by + bh*0.28, sub, ha='center', va='center', fontsize=6.2, color='#3C4043', transform=ax.transAxes, zorder=3)

    # Connections
    arrow_props = dict(arrowstyle="->", color="#5F6368", lw=1.2)
    # Video -> YOLO
    ax.annotate('', xy=(0.22, 0.72), xytext=(0.18, 0.72), arrowprops=arrow_props)
    # YOLO -> State Builder
    ax.annotate('', xy=(0.44, 0.72), xytext=(0.40, 0.72), arrowprops=arrow_props)
    # State -> D3QN
    ax.annotate('', xy=(0.64, 0.76), xytext=(0.60, 0.72), arrowprops=arrow_props)
    # State -> UQ
    ax.annotate('', xy=(0.64, 0.28), xytext=(0.52, 0.52), arrowprops=arrow_props)
    # UQ -> Supervisor
    ax.annotate('', xy=(0.84, 0.65), xytext=(0.80, 0.28), arrowprops=arrow_props)
    # D3QN -> Supervisor
    ax.annotate('', xy=(0.84, 0.76), xytext=(0.80, 0.76), arrowprops=arrow_props)
    # Fallback -> Supervisor
    ax.annotate('', xy=(0.84, 0.58), xytext=(0.60, 0.28), arrowprops=arrow_props)
    # Supervisor -> Physical FSM
    ax.annotate('', xy=(0.915, 0.44), xytext=(0.915, 0.52), arrowprops=dict(arrowstyle="->", color=c_safe_b, lw=1.5))

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig1_architecture.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("Fig 1 generated.")

# -------------------------------------------------------------
# Figure 2: Supervisor State Machine
# -------------------------------------------------------------
def generate_fig2_supervisor():
    fig, ax = plt.subplots(figsize=(5.5, 2.5), dpi=300)
    ax.axis('off')

    c_rl = '#E6F4EA'
    c_rl_b = '#137333'
    c_fb = '#FCE8E6'
    c_fb_b = '#C5221F'

    # RL ACTIVE Box
    rect1 = plt.Rectangle((0.08, 0.30), 0.34, 0.45, facecolor=c_rl, edgecolor=c_rl_b, linewidth=1.6, transform=ax.transAxes, zorder=2)
    ax.add_patch(rect1)
    ax.text(0.25, 0.58, "RL_ACTIVE", ha='center', va='center', fontsize=9.5, fontweight='bold', color=c_rl_b, transform=ax.transAxes)
    ax.text(0.25, 0.42, "Nominal D3QN Policy\nControls Signal Phase", ha='center', va='center', fontsize=7.5, color='#3C4043', transform=ax.transAxes)

    # FALLBACK ACTIVE Box
    rect2 = plt.Rectangle((0.58, 0.30), 0.34, 0.45, facecolor=c_fb, edgecolor=c_fb_b, linewidth=1.6, transform=ax.transAxes, zorder=2)
    ax.add_patch(rect2)
    ax.text(0.75, 0.58, "FALLBACK_ACTIVE", ha='center', va='center', fontsize=9.5, fontweight='bold', color=c_fb_b, transform=ax.transAxes)
    ax.text(0.75, 0.42, "Max-Pressure Fallback\nControls Signal Phase", ha='center', va='center', fontsize=7.5, color='#3C4043', transform=ax.transAxes)

    # Arrow RL -> Fallback
    ax.annotate('', xy=(0.58, 0.65), xytext=(0.42, 0.65),
                arrowprops=dict(arrowstyle="->", color=c_fb_b, lw=1.8, connectionstyle="arc3,rad=-0.15"))
    ax.text(0.50, 0.85, r"Trip: $u_t \geq \tau_{\mathrm{high}} = 0.65$", ha='center', va='center', fontsize=8, fontweight='bold', color=c_fb_b, transform=ax.transAxes)

    # Arrow Fallback -> RL
    ax.annotate('', xy=(0.42, 0.40), xytext=(0.58, 0.40),
                arrowprops=dict(arrowstyle="->", color=c_rl_b, lw=1.8, connectionstyle="arc3,rad=-0.15"))
    ax.text(0.50, 0.15, r"Recovery: $u_t \leq \tau_{\mathrm{low}} = 0.50$" "\n" r"and $t_{\mathrm{dwell}} \geq 8.0\,\mathrm{s}$ and $K_{\mathrm{rec}} \geq 10$", ha='center', va='center', fontsize=7.5, fontweight='bold', color=c_rl_b, transform=ax.transAxes)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig2_supervisor.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("Fig 2 generated.")

# -------------------------------------------------------------
# Figure 3: Reliability Boundary & Robustness Sweep
# -------------------------------------------------------------
def generate_fig3_robustness():
    # Data from results/final/table_reliability_boundary_v2.csv
    miss_rates = np.array([0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50])
    fixed_delay = np.array([15.12]*11)
    mp_delay = np.array([11.30]*11)
    d3qn_delay = np.array([15.30, 15.50, 15.42, 15.52, 15.14, 15.35, 15.38, 15.35, 15.33, 15.28, 15.37])
    flowsync_delay = np.array([15.24, 15.43, 15.37, 15.46, 15.10, 15.24, 15.28, 15.24, 15.16, 15.19, 15.36])

    fig, ax = plt.subplots(figsize=(4.8, 3.2), dpi=300)
    
    ax.plot(miss_rates * 100, mp_delay, 's--', color='#1A73E8', label='Max-Pressure (Clean Oracle)', alpha=0.85)
    ax.plot(miss_rates * 100, fixed_delay, '^:', color='#5F6368', label='Fixed-Time (Webster Baseline)', alpha=0.85)
    ax.plot(miss_rates * 100, d3qn_delay, 'o-', color='#EA8600', label='D3QN (Unshielded / Blind)', alpha=0.9)
    ax.plot(miss_rates * 100, flowsync_delay, 'd-', color='#137333', linewidth=2.2, label='FlowSync-UQ (Proposed)')

    ax.set_xlabel('Perception Miss Rate $p_{\\mathrm{miss}}$ (%)')
    ax.set_ylabel('Mean Vehicle Delay (s)')
    ax.set_ylim(10.5, 16.5)
    ax.set_xlim(-2, 52)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='lower right', frameon=True, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig3_robustness_sweep.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("Fig 3 generated.")

# -------------------------------------------------------------
# Figure 4: Component Ablation Study Bar Chart
# -------------------------------------------------------------
def generate_fig4_ablations():
    variants = ['V1: Full FlowSync-UQ', 'V2: Blind D3QN', 'V3: No-Shield', 'V4: No-Fallback', 'V5: Fixed Fallback']
    mean_delay = [15.08, 12.43, 15.04, 18.23, 16.59]
    starvations = [64, 78, 66, 82, 62]
    violations = [54, 68, 61, 75, 52]

    x = np.arange(len(variants))
    width = 0.55

    fig, ax1 = plt.subplots(figsize=(5.6, 3.0), dpi=300)

    colors = ['#137333', '#1A73E8', '#9AA0A6', '#C5221F', '#EA8600']
    bars = ax1.bar(x, mean_delay, width, color=colors, edgecolor='#202124', linewidth=0.8, alpha=0.88, zorder=3)
    ax1.set_ylabel('Mean Delay (s)', color='#202124', fontweight='bold')
    ax1.set_ylim(0, 22)
    ax1.set_xticks(x)
    ax1.set_xticklabels(['V1 (Full)', 'V2 (Blind)', 'V3 (No-Shield)', 'V4 (No-Fallback)', 'V5 (Fixed-FB)'], fontsize=8)
    ax1.grid(True, axis='y', linestyle='--', alpha=0.5, zorder=0)

    # Annotate values on bars
    for bar in bars:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., h + 0.4, f"{h:.2f}s", ha='center', va='bottom', fontsize=7.5, fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig4_ablations.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("Fig 4 generated.")

# -------------------------------------------------------------
# Figure 5: Latency Breakdown Bar Chart
# -------------------------------------------------------------
def generate_fig5_latency():
    stages = [
        'Frame Acquisition',
        'YOLOv8 Detection',
        'ByteTrack Tracking',
        'ROI & State Build',
        'UQ Feature Extraction',
        'D3QN Inference',
        'Max-Pressure Calc',
        'Supervisor & FSM'
    ]
    latencies = [4.50, 52.59, 0.14, 0.009, 0.168, 0.225, 0.014, 0.011]
    colors = ['#1A73E8', '#4285F4', '#669DF6', '#AECBFA', '#EA8600', '#34A853', '#FBBC04', '#7627BB']

    fig, ax = plt.subplots(figsize=(5.4, 3.2), dpi=300)
    y_pos = np.arange(len(stages))
    bars = ax.barh(y_pos, latencies, color=colors, edgecolor='#202124', linewidth=0.6, alpha=0.85, zorder=3)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(stages, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel('Execution Latency (ms)')
    ax.set_xlim(0, 65)
    ax.grid(True, axis='x', linestyle='--', alpha=0.5, zorder=0)

    # Annotate bars
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.8, bar.get_y() + bar.get_height()/2., f"{w:.2f} ms", ha='left', va='center', fontsize=7.5)

    ax.axvline(x=57.66, color='#C5221F', linestyle='--', linewidth=1.2, label='Mean End-to-End: 57.66 ms')
    ax.legend(loc='lower right', fontsize=8)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig5_latency.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("Fig 5 generated.")

# -------------------------------------------------------------
# Figure 6: CV Uncertainty Correlation by Environmental Regime
# -------------------------------------------------------------
def generate_fig6_cv_regimes():
    regimes = ['Daylight\n(Low Density)', 'Commute Peak\n(Dense)', 'Heavy Occlusion\n(Transit)', 'Adverse Rain\n(Low Light)']
    uncertainty_means = [0.137, 0.389, 0.626, 0.713]
    count_maes = [0.32, 0.87, 1.45, 1.72]

    x = np.arange(len(regimes))
    width = 0.35

    fig, ax1 = plt.subplots(figsize=(5.2, 3.0), dpi=300)

    color1 = '#EA8600'
    color2 = '#1A73E8'

    rects1 = ax1.bar(x - width/2, uncertainty_means, width, label=r'Calibrated Uncertainty $\bar{u}_t$', color=color1, edgecolor='#202124', linewidth=0.7, alpha=0.85)
    ax1.set_ylabel(r'Mean Calibrated Uncertainty $\bar{u}_t$', color=color1, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.set_ylim(0, 1.0)
    ax1.set_xticks(x)
    ax1.set_xticklabels(regimes, fontsize=7.8)

    ax2 = ax1.twinx()
    rects2 = ax2.bar(x + width/2, count_maes, width, label='Count MAE (veh)', color=color2, edgecolor='#202124', linewidth=0.7, alpha=0.85)
    ax2.set_ylabel('Vehicle Count MAE (veh)', color=color2, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.set_ylim(0, 2.2)

    # Pearson annotation
    fig.suptitle(r'Perception Uncertainty vs. Counting Error ($r = 0.928, p < 0.001$)', fontsize=9.5, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig6_cv_correlation.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("Fig 6 generated.")

if __name__ == '__main__':
    generate_fig1_architecture()
    generate_fig2_supervisor()
    generate_fig3_robustness()
    generate_fig4_ablations()
    generate_fig5_latency()
    generate_fig6_cv_regimes()
    print("All 6 publication figures generated successfully in", OUTPUT_DIR)
