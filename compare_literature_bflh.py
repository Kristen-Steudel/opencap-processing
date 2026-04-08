# Compare per-stride BFLH length and velocity curves against Bing Yu et al.
# literature data using Pearson correlation.
#
# Both curves are interpolated onto a common 0-100% gait cycle grid before
# computing the correlation, so differences in units (normalized vs. meters)
# do not affect the result.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.stats import pearsonr
from matplotlib import cm

# ===== CONFIGURATION =====
subject = 2
session = "S7"
base_path = rf'G:\Shared drives\Stanford Football\March_2\subject{subject}\CleanedKinematics\filtered_post_augmentation\Outputs'
trial_type = 'sprint'
n_strides_to_plot = 2

lit_lengths_file = r'C:\Users\steudelkri\Documents\opencap-processing\experiments\LiteratureData\BingYuBFLHLengths.csv'
lit_velocities_file = r'C:\Users\steudelkri\Documents\opencap-processing\experiments\LiteratureData\BingYuBFLHVelocities.csv'

# ===== LOAD DATA =====
left_stride_times_df = pd.read_csv(rf'{base_path}\step_times_left.csv')
right_stride_times_df = pd.read_csv(rf'{base_path}\step_times_right.csv')
mtu_lengths_file = rf'{base_path}\normalized_muscle_tendon_lengths_ID{subject}_{session}_{trial_type}_LSTM_filtpostaug15Hz_filteredkinematics_15Hz_filtered_15Hz.csv'
mtu_lengths_df = pd.read_csv(mtu_lengths_file)

# Literature data (headerless CSVs: column 0 = gait cycle %, column 1 = value)
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

metrics_file = rf'{base_path}\bflh_literature_correlation_ID{subject}_{session}_{trial_type}.csv'
metrics_df.to_csv(metrics_file, index=False)

print(f"{'='*70}")
print("BFLH Literature Comparison (Pearson r) — Bing Yu et al.")
print(f"{'='*70}")
print(metrics_df.to_string(index=False))
print(f"\nSaved to: {metrics_file}")

# ===== PLOT: OVERLAY LAST N STRIDES WITH LITERATURE =====
fig, axes = plt.subplots(2, 2, figsize=(18, 13))

left_results = sorted([r for r in results if r['side'] == 'left'], key=lambda r: r['stride_number'])
right_results = sorted([r for r in results if r['side'] == 'right'], key=lambda r: r['stride_number'])

n_left = min(n_strides_to_plot, len(left_results))
n_right = min(n_strides_to_plot, len(right_results))

left_to_plot = left_results[:n_left]
right_to_plot = right_results[:n_right]

left_colors = cm.Blues(np.linspace(0.45, 0.9, max(n_left, 1)))
right_colors = cm.Reds(np.linspace(0.45, 0.9, max(n_right, 1)))

# Top-left: left lengths vs literature
for idx, r in enumerate(left_to_plot):
    axes[0, 0].plot(normalized_x, r['length_curve'], color=left_colors[idx],
                    label=f'Stride {r["stride_number"]} (r={r["r_length"]:.3f})', linewidth=2)
axes[0, 0].plot(normalized_x, lit_len_interp, 'k--', linewidth=2.5, label='Bing Yu et al.')
axes[0, 0].set_xlabel('Gait Cycle (%)', fontsize=13)
axes[0, 0].set_ylabel('BFLH Length', fontsize=13)
axes[0, 0].set_title(f'Left BFLH Lengths vs Literature (last {n_left})', fontsize=13, fontweight='bold')
axes[0, 0].legend(fontsize=9, loc='best')
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].set_xlim([0, 100])
ax0_twin = axes[0, 0].twinx()
ax0_twin.set_ylabel('Literature (m)', fontsize=11, color='gray')
ax0_twin.tick_params(axis='y', labelcolor='gray')
ax0_twin.set_ylim([lit_len_interp.min() - 0.01, lit_len_interp.max() + 0.01])

# Top-right: right lengths vs literature
for idx, r in enumerate(right_to_plot):
    axes[0, 1].plot(normalized_x, r['length_curve'], color=right_colors[idx],
                    label=f'Stride {r["stride_number"]} (r={r["r_length"]:.3f})', linewidth=2)
axes[0, 1].plot(normalized_x, lit_len_interp, 'k--', linewidth=2.5, label='Bing Yu et al.')
axes[0, 1].set_xlabel('Gait Cycle (%)', fontsize=13)
axes[0, 1].set_ylabel('BFLH Length', fontsize=13)
axes[0, 1].set_title(f'Right BFLH Lengths vs Literature (last {n_right})', fontsize=13, fontweight='bold')
axes[0, 1].legend(fontsize=9, loc='best')
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].set_xlim([0, 100])
ax1_twin = axes[0, 1].twinx()
ax1_twin.set_ylabel('Literature (m)', fontsize=11, color='gray')
ax1_twin.tick_params(axis='y', labelcolor='gray')
ax1_twin.set_ylim([lit_len_interp.min() - 0.01, lit_len_interp.max() + 0.01])

# Bottom-left: left velocities vs literature
for idx, r in enumerate(left_to_plot):
    axes[1, 0].plot(normalized_x, r['velocity_curve'], color=left_colors[idx],
                    label=f'Stride {r["stride_number"]} (r={r["r_velocity"]:.3f})', linewidth=2)
axes[1, 0].plot(normalized_x, lit_vel_interp, 'k--', linewidth=2.5, label='Bing Yu et al.')
axes[1, 0].set_xlabel('Gait Cycle (%)', fontsize=13)
axes[1, 0].set_ylabel('BFLH Velocity', fontsize=13)
axes[1, 0].set_title(f'Left BFLH Velocities vs Literature (last {n_left})', fontsize=13, fontweight='bold')
axes[1, 0].legend(fontsize=9, loc='best')
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].set_xlim([0, 100])
ax2_twin = axes[1, 0].twinx()
ax2_twin.set_ylabel('Literature (m/s)', fontsize=11, color='gray')
ax2_twin.tick_params(axis='y', labelcolor='gray')
ax2_twin.set_ylim([lit_vel_interp.min() - 0.1, lit_vel_interp.max() + 0.1])

# Bottom-right: right velocities vs literature
for idx, r in enumerate(right_to_plot):
    axes[1, 1].plot(normalized_x, r['velocity_curve'], color=right_colors[idx],
                    label=f'Stride {r["stride_number"]} (r={r["r_velocity"]:.3f})', linewidth=2)
axes[1, 1].plot(normalized_x, lit_vel_interp, 'k--', linewidth=2.5, label='Bing Yu et al.')
axes[1, 1].set_xlabel('Gait Cycle (%)', fontsize=13)
axes[1, 1].set_ylabel('BFLH Velocity', fontsize=13)
axes[1, 1].set_title(f'Right BFLH Velocities vs Literature (last {n_right})', fontsize=13, fontweight='bold')
axes[1, 1].legend(fontsize=9, loc='best')
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].set_xlim([0, 100])
ax3_twin = axes[1, 1].twinx()
ax3_twin.set_ylabel('Literature (m/s)', fontsize=11, color='gray')
ax3_twin.tick_params(axis='y', labelcolor='gray')
ax3_twin.set_ylim([lit_vel_interp.min() - 0.1, lit_vel_interp.max() + 0.1])

plt.tight_layout()
plot_file = rf'{base_path}\bflh_literature_comparison_ID{subject}_{session}_{trial_type}.png'
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
