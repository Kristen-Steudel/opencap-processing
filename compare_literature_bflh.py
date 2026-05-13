# Compare per-stride BFLH length and velocity curves against Bing Yu et al.
# literature data using Pearson correlation.
#
# Both curves are interpolated onto a common 0-100% gait cycle grid before
# computing the correlation, so differences in units (normalized vs. meters)
# do not affect the result.

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.stats import pearsonr
from matplotlib import cm

# Configuration imported from pipeline_config.py (edit once, used by all scripts)
import pipeline_config as cfg
paths = cfg.PATHS
subject = cfg.SUBJECT_NUM
session = f'S{cfg.SESSION}'
base_path = paths['outputs_dir']
trial_type = cfg.TRIAL_TYPE
n_strides_to_plot = 2

lit_lengths_file = paths['lit_lengths_file']
lit_velocities_file = paths['lit_velocities_file']
lit_hamstrings_file = paths['lit_hamstrings_combined']

# Speed bin to use from the hamstrings CSV
NORDSPRINT_SPEED = '7p0'

# ===== LOAD DATA =====
left_stride_times_df = pd.read_csv(paths['step_times_left'])
right_stride_times_df = pd.read_csv(paths['step_times_right'])
mtu_lengths_file = paths['normalized_bflh_csv']
mtu_lengths_df = pd.read_csv(mtu_lengths_file)

# Bing Yu literature (headerless CSVs: column 0 = gait cycle %, column 1 = value)
lit_lengths_raw = np.loadtxt(lit_lengths_file, delimiter=',')
lit_velocities_raw = np.loadtxt(lit_velocities_file, delimiter=',')

# Sort by gait cycle % and remove duplicate x-values for clean interpolation
def prepare_literature_curve(raw):
    order = np.argsort(raw[:, 0])
    x_sorted = raw[order, 0]
    y_sorted = raw[order, 1]
    _, unique_idx = np.unique(x_sorted, return_index=True)
    return x_sorted[unique_idx], y_sorted[unique_idx]

lit_len_x, lit_len_y = prepare_literature_curve(lit_lengths_raw)
lit_vel_x, lit_vel_y = prepare_literature_curve(lit_velocities_raw)

# Interpolate literature curves onto a common 101-point grid
normalized_x = np.linspace(0, 100, 101)
lit_len_interp = interp1d(lit_len_x, lit_len_y, kind='linear', fill_value='extrapolate')(normalized_x)
lit_vel_interp = interp1d(lit_vel_x, lit_vel_y, kind='linear', fill_value='extrapolate')(normalized_x)

# Hamstring MTU reference curves — right-side, 7 m/s
# Lengths and velocities are pre-computed in MATLAB/OpenSim.
# Column naming: BFLH_Right_{speed}_Len_Mean/Std and BFLH_Right_{speed}_Vel_Mean/Std
ns_len_mean  = None
ns_len_std   = None
ns_vel_mean  = None
ns_vel_upper = None
ns_vel_lower = None
if os.path.exists(lit_hamstrings_file):
    ns_df = pd.read_csv(lit_hamstrings_file)
    ns_pct = ns_df['Percent_Stride'].values
    spd = NORDSPRINT_SPEED

    len_mean_col = f'BFLH_Right_{spd}_Len_Mean'
    len_std_col  = f'BFLH_Right_{spd}_Len_Std'
    vel_mean_col = f'BFLH_Right_{spd}_Vel_Mean'
    vel_std_col  = f'BFLH_Right_{spd}_Vel_Std'

    def _interp(col):
        return interp1d(ns_pct, ns_df[col].values,
                        kind='linear', fill_value='extrapolate')(normalized_x)

    if len_mean_col in ns_df.columns:
        ns_len_mean = _interp(len_mean_col)
        ns_len_std  = _interp(len_std_col)

    if vel_mean_col in ns_df.columns:
        vel_vals = ns_df[vel_mean_col].values
        # Velocity column may still be all-zeros if MATLAB hasn't been run yet
        if vel_vals.max() != 0 or vel_vals.min() != 0:
            ns_vel_mean  = _interp(vel_mean_col)
            ns_vel_std   = _interp(vel_std_col)
            ns_vel_upper = ns_vel_mean + ns_vel_std
            ns_vel_lower = ns_vel_mean - ns_vel_std
        else:
            print(f"NOTE: velocity columns in hamstrings CSV are all zero — "
                  f"populate them from MATLAB to enable the velocity overlay.")

    speed_str = spd.replace('p', '.')
    print(f"Loaded hamstrings reference ({speed_str} m/s): "
          f"length={'OK' if ns_len_mean is not None else 'missing'}, "
          f"velocity={'OK' if ns_vel_mean is not None else 'zeros/missing'}")
else:
    print(f"WARNING: hamstrings file not found, skipping overlay:\n  {lit_hamstrings_file}")


# ===== HELPER FUNCTIONS =====
def get_stride_window(df, start_time, end_time):
    return df[(df['time'] >= start_time) & (df['time'] <= end_time)].reset_index(drop=True)


def interpolate_stride(stride_df, col):
    pct = np.linspace(0, 100, len(stride_df))
    return interp1d(pct, stride_df[col], kind='linear', fill_value='extrapolate')(normalized_x)


# ===== BUILD PER-STRIDE CURVES AND CORRELATIONS =====
results = []

def process_side(stride_times_df, side, muscle_col):
    for i in range(len(stride_times_df) - 1):
        t0 = stride_times_df['time'].iloc[i]
        t1 = stride_times_df['time'].iloc[i + 1]
        stride_df = get_stride_window(mtu_lengths_df, t0, t1)
        if len(stride_df) < 2:
            continue

        stride_df = stride_df.copy()
        length_curve = interpolate_stride(stride_df, muscle_col)
        stride_df['bflh_vel'] = np.gradient(stride_df[muscle_col], stride_df['time'])
        velocity_curve = interpolate_stride(stride_df, 'bflh_vel')

        r_len, p_len = pearsonr(length_curve, lit_len_interp)
        r_vel, p_vel = pearsonr(velocity_curve, lit_vel_interp)

        results.append({
            'side': side,
            'stride_index': i,
            'start_time': t0,
            'end_time': t1,
            'length_curve': length_curve,
            'velocity_curve': velocity_curve,
            'r_length': r_len,
            'p_length': p_len,
            'r_velocity': r_vel,
            'p_velocity': p_vel,
        })

process_side(left_stride_times_df, 'left', 'bflh_l')
process_side(right_stride_times_df, 'right', 'bflh_r')

# Number strides per side in reverse order (stride 1 = latest chronologically)
for side in ['left', 'right']:
    side_results = [r for r in results if r['side'] == side]
    for rank, r in enumerate(reversed(side_results), start=1):
        r['stride_number'] = rank

# ===== SAVE CORRELATION METRICS =====
metrics_df = pd.DataFrame([{
    'side': r['side'],
    'stride_number': r['stride_number'],
    'start_time': r['start_time'],
    'end_time': r['end_time'],
    'pearson_r_length': r['r_length'],
    'p_value_length': r['p_length'],
    'pearson_r_velocity': r['r_velocity'],
    'p_value_velocity': r['p_velocity'],
} for r in results])
metrics_df = metrics_df.sort_values(['side', 'stride_number']).reset_index(drop=True)

tag = paths['file_tag']
metrics_file = rf'{base_path}\bflh_lit_corr_{tag}.csv'
metrics_df.to_csv(metrics_file, index=False)

print(f"{'='*70}")
print("BFLH Literature Comparison (Pearson r) — Bing Yu et al.")
print(f"{'='*70}")
print(metrics_df.to_string(index=False))
print(f"\nSaved to: {metrics_file}")

# ===== PLOT: OVERLAY LAST N STRIDES WITH LITERATURE =====
fig, axes = plt.subplots(2, 2, figsize=(18, 13))

left_results  = sorted([r for r in results if r['side'] == 'left'],  key=lambda r: r['stride_number'])
right_results = sorted([r for r in results if r['side'] == 'right'], key=lambda r: r['stride_number'])

n_left  = min(n_strides_to_plot, len(left_results))
n_right = min(n_strides_to_plot, len(right_results))

left_to_plot  = left_results[:n_left]
right_to_plot = right_results[:n_right]

left_colors  = cm.Blues(np.linspace(0.45, 0.9, max(n_left,  1)))
right_colors = cm.Reds( np.linspace(0.45, 0.9, max(n_right, 1)))

speed_label = NORDSPRINT_SPEED.replace('p', '.')


def add_nordsprint_length(ax, first=False):
    """Overlay right-side NordSprint mean (solid black) and ±1 SD (dotted black)."""
    if ns_len_mean is None:
        return
    ax.plot(normalized_x, ns_len_mean,
            color='black', linewidth=2.0, linestyle='-',
            label=f'NordSprint {speed_label} m/s mean' if first else None)
    ax.plot(normalized_x, ns_len_mean + ns_len_std,
            color='black', linewidth=1.2, linestyle=':',
            label=f'NordSprint ± 1 SD' if first else None)
    ax.plot(normalized_x, ns_len_mean - ns_len_std,
            color='black', linewidth=1.2, linestyle=':')


def aligned_limits(exp_curves, lit_curve, pad_frac=0.05):
    """Align primary and twin y-axes so both datasets span the same fraction."""
    all_exp = np.concatenate(exp_curves)
    exp_lo, exp_hi = all_exp.min(), all_exp.max()
    lit_lo, lit_hi = lit_curve.min(), lit_curve.max()
    exp_pad = (exp_hi - exp_lo) * pad_frac
    lit_pad = (lit_hi - lit_lo) * pad_frac
    return ([exp_lo - exp_pad, exp_hi + exp_pad],
            [lit_lo - lit_pad, lit_hi + lit_pad])


def finish_length_ax(ax, twin, exp_curves, ns_curves):
    """Apply limits, labels, and legend for a length subplot."""
    all_primary = exp_curves + ns_curves
    if all_primary:
        exp_lim, lit_lim = aligned_limits(all_primary, lit_len_interp)
        ax.set_ylim(exp_lim)
        twin.set_ylim(lit_lim)
    ax.set_ylabel('BFLH Length (normalized)', fontsize=16)
    ax.tick_params(axis='both', labelsize=13)
    twin.set_ylabel('Bing Yu et al. (m)', fontsize=14, color='gray')
    twin.tick_params(axis='y', labelcolor='gray', labelsize=13)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = twin.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=12, loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xlim([0, 100])


def finish_velocity_ax(ax, twin_by, exp_curves, show_ns_legend=False):
    """Apply limits, labels, and legend for a velocity subplot.

    NordSprint velocity is in m/s (same units as Bing Yu), so both are
    plotted on the single twin axis and share its scale.

    twin_by        : twinx axis (Bing Yu already plotted on it)
    show_ns_legend : include NordSprint legend entries (left subplot only)
    """
    # ── NordSprint velocity on the primary axis (both in norm/s) ─────
    if ns_vel_mean is not None:
        ax.plot(normalized_x, ns_vel_mean,
                color='black', linewidth=2.0, linestyle='-',
                label=f'NordSprint {speed_label} m/s mean' if show_ns_legend else '_nolegend_')
        ax.plot(normalized_x, ns_vel_upper,
                color='black', linewidth=1.2, linestyle=':',
                label='NordSprint ± 1 SD' if show_ns_legend else '_nolegend_')
        ax.plot(normalized_x, ns_vel_lower,
                color='black', linewidth=1.2, linestyle=':',
                label='_nolegend_')

    # ── align primary (exp + NordSprint, norm/s) ↔ twin (Bing Yu, m/s) ─
    if exp_curves:
        primary_data = list(exp_curves)
        if ns_vel_mean is not None:
            primary_data += [ns_vel_mean, ns_vel_upper, ns_vel_lower]
        exp_lim, by_lim = aligned_limits(primary_data, lit_vel_interp)
        ax.set_ylim(exp_lim)
        twin_by.set_ylim(by_lim)

    # ── common styling & combined legend ─────────────────────────────
    ax.set_xlabel('Gait Cycle (%)', fontsize=16)
    ax.set_ylabel('BFLH Velocity (norm units/s)', fontsize=16)
    ax.tick_params(axis='both', labelsize=13)
    twin_by.set_ylabel('Bing Yu et al. (m/s)', fontsize=14, color='gray')
    twin_by.tick_params(axis='y', labelcolor='gray', labelsize=13)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = twin_by.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=12, loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xlim([0, 100])


# ── Top-left: left lengths ──────────────────────────────────────────
exp_curves_00 = []
for idx, r in enumerate(left_to_plot):
    axes[0, 0].plot(normalized_x, r['length_curve'], color=left_colors[idx],
                    label=f'Stride {r["stride_number"]} (r={r["r_length"]:.3f})', linewidth=2)
    exp_curves_00.append(r['length_curve'])
add_nordsprint_length(axes[0, 0], first=True)
ax0_twin = axes[0, 0].twinx()
ax0_twin.plot(normalized_x, lit_len_interp, 'k--', linewidth=2.5, label='Bing Yu et al.')
ns_curves_00 = ([ns_len_mean, ns_len_mean + ns_len_std, ns_len_mean - ns_len_std]
                if ns_len_mean is not None else [])
axes[0, 0].set_title(f'Left BFLH Lengths vs Literature (last {n_left})', fontsize=17, fontweight='bold')
finish_length_ax(axes[0, 0], ax0_twin, exp_curves_00, ns_curves_00)

# ── Top-right: right lengths ────────────────────────────────────────
exp_curves_01 = []
for idx, r in enumerate(right_to_plot):
    axes[0, 1].plot(normalized_x, r['length_curve'], color=right_colors[idx],
                    label=f'Stride {r["stride_number"]} (r={r["r_length"]:.3f})', linewidth=2)
    exp_curves_01.append(r['length_curve'])
add_nordsprint_length(axes[0, 1])
ax1_twin = axes[0, 1].twinx()
ax1_twin.plot(normalized_x, lit_len_interp, 'k--', linewidth=2.5, label='Bing Yu et al.')
ns_curves_01 = ([ns_len_mean, ns_len_mean + ns_len_std, ns_len_mean - ns_len_std]
                if ns_len_mean is not None else [])
axes[0, 1].set_title(f'Right BFLH Lengths vs Literature (last {n_right})', fontsize=17, fontweight='bold')
finish_length_ax(axes[0, 1], ax1_twin, exp_curves_01, ns_curves_01)

# ── Bottom-left: left velocities ────────────────────────────────────
exp_curves_10 = []
for idx, r in enumerate(left_to_plot):
    axes[1, 0].plot(normalized_x, r['velocity_curve'], color=left_colors[idx],
                    label=f'Stride {r["stride_number"]} (r={r["r_velocity"]:.3f})', linewidth=2)
    exp_curves_10.append(r['velocity_curve'])
ax2_twin = axes[1, 0].twinx()
ax2_twin.plot(normalized_x, lit_vel_interp, 'k--', linewidth=2.5, label='Bing Yu et al.')
axes[1, 0].set_title(f'Left BFLH Velocities vs Literature (last {n_left})', fontsize=17, fontweight='bold')
finish_velocity_ax(axes[1, 0], ax2_twin, exp_curves_10, show_ns_legend=True)

# ── Bottom-right: right velocities ──────────────────────────────────
exp_curves_11 = []
for idx, r in enumerate(right_to_plot):
    axes[1, 1].plot(normalized_x, r['velocity_curve'], color=right_colors[idx],
                    label=f'Stride {r["stride_number"]} (r={r["r_velocity"]:.3f})', linewidth=2)
    exp_curves_11.append(r['velocity_curve'])
ax3_twin = axes[1, 1].twinx()
ax3_twin.plot(normalized_x, lit_vel_interp, 'k--', linewidth=2.5, label='Bing Yu et al.')
axes[1, 1].set_title(f'Right BFLH Velocities vs Literature (last {n_right})', fontsize=17, fontweight='bold')
finish_velocity_ax(axes[1, 1], ax3_twin, exp_curves_11, show_ns_legend=False)

plt.tight_layout()
plot_file = rf'{base_path}\bflh_lit_compare_{tag}.png'
plt.savefig(plot_file, dpi=300, bbox_inches='tight')
plt.show()

print(f"\nComparison plot saved to: {plot_file}")

# ===== SUMMARY STATS =====
for side in ['left', 'right']:
    side_df = metrics_df[metrics_df['side'] == side]
    if len(side_df) == 0:
        continue
    print(f"\n{side.upper()} strides:")
    print(f"  Length  Pearson r — mean: {side_df['pearson_r_length'].mean():.4f}, "
          f"range: [{side_df['pearson_r_length'].min():.4f}, {side_df['pearson_r_length'].max():.4f}]")
    print(f"  Velocity Pearson r — mean: {side_df['pearson_r_velocity'].mean():.4f}, "
          f"range: [{side_df['pearson_r_velocity'].min():.4f}, {side_df['pearson_r_velocity'].max():.4f}]")
