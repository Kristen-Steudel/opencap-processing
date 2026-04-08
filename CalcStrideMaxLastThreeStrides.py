# Load in MTU length data for individual strides (full gait cycles),
# calculate the BFLH peak MTU length and velocity for each stride,
# and save the maximum values to a new csv file.
#
# STRIDE DEFINITION (full gait cycle, comparable to literature):
#   - LEFT stride  = left foot contact[i] → left foot contact[i+1]
#   - RIGHT stride = right foot contact[i] → right foot contact[i+1]
# The analyzed muscle matches the stride side (bflh_l for left, bflh_r for right).

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from matplotlib import cm

import utilsKinematics

subject = 2
session = "S7"
base_path = rf'G:\Shared drives\Stanford Football\March_2\subject{subject}\CleanedKinematics\filtered_post_augmentation\Outputs'
trial_type = 'sprint'
filt_freq = 8  # Hz, was 15 Hz
n_strides_to_plot = 2

# Load foot contact times (one file per side)
left_stride_times_file = rf'{base_path}\step_times_left.csv'
left_stride_times_df = pd.read_csv(left_stride_times_file)
right_stride_times_file = rf'{base_path}\step_times_right.csv'
right_stride_times_df = pd.read_csv(right_stride_times_file)

# Load normalized muscle-tendon unit lengths
mtu_lengths_file = rf'{base_path}\normalized_muscle_tendon_lengths_ID{subject}_{session}_{trial_type}_LSTM_filtpostaug15Hz_filteredkinematics_15Hz_filtered_15Hz.csv'
mtu_lengths_df = pd.read_csv(mtu_lengths_file)

print(f"Loaded {len(left_stride_times_df)} left foot contact times")
print(f"Loaded {len(right_stride_times_df)} right foot contact times")


def get_stride_window(df, start_time, end_time):
    return df[(df['time'] >= start_time) & (df['time'] <= end_time)].reset_index(drop=True)


# ===== PROCESS FULL STRIDES (GAIT CYCLES) =====
# Left strides: left contact[i] → left contact[i+1], analyze bflh_l
# Right strides: right contact[i] → right contact[i+1], analyze bflh_r
left_stride_data = []
right_stride_data = []

for i in range(len(left_stride_times_df) - 1):
    start_time = left_stride_times_df['time'].iloc[i]
    end_time = left_stride_times_df['time'].iloc[i + 1]

    stride_mtu_df = get_stride_window(mtu_lengths_df, start_time, end_time)
    if len(stride_mtu_df) < 2:
        continue

    stride_mtu_df = stride_mtu_df.copy()
    stride_mtu_df['bflh_vel'] = np.gradient(stride_mtu_df['bflh_l'], stride_mtu_df['time'])

    left_stride_data.append({
        'stride_side': 'left',
        'start_time': start_time,
        'end_time': end_time,
        'stride_duration': end_time - start_time,
        'bflh_max_length': stride_mtu_df['bflh_l'].max(),
        'bflh_max_velocity': stride_mtu_df['bflh_vel'].max(),
        'bflh_avg_lengthening_velocity': stride_mtu_df.loc[stride_mtu_df['bflh_vel'] > 0, 'bflh_vel'].mean(),
    })

for i in range(len(right_stride_times_df) - 1):
    start_time = right_stride_times_df['time'].iloc[i]
    end_time = right_stride_times_df['time'].iloc[i + 1]

    stride_mtu_df = get_stride_window(mtu_lengths_df, start_time, end_time)
    if len(stride_mtu_df) < 2:
        continue

    stride_mtu_df = stride_mtu_df.copy()
    stride_mtu_df['bflh_vel'] = np.gradient(stride_mtu_df['bflh_r'], stride_mtu_df['time'])

    right_stride_data.append({
        'stride_side': 'right',
        'start_time': start_time,
        'end_time': end_time,
        'stride_duration': end_time - start_time,
        'bflh_max_length': stride_mtu_df['bflh_r'].max(),
        'bflh_max_velocity': stride_mtu_df['bflh_vel'].max(),
        'bflh_avg_lengthening_velocity': stride_mtu_df.loc[stride_mtu_df['bflh_vel'] > 0, 'bflh_vel'].mean(),
    })

left_output_df = pd.DataFrame(left_stride_data)
right_output_df = pd.DataFrame(right_stride_data)

# Number strides in reverse order (stride 1 = closest to capture volume / latest chronologically)
for df_side in [left_output_df, right_output_df]:
    if len(df_side) > 0:
        df_side['stride_number'] = range(len(df_side), 0, -1)

# Combine into a single output for convenience
stride_output_df = pd.concat([left_output_df, right_output_df], ignore_index=True)
stride_output_df = stride_output_df.sort_values(['stride_side', 'stride_number']).reset_index(drop=True)

# Save to CSV files
left_output_file = rf'{base_path}\bflh_mtu_max_left_strides_ID{subject}_{session}_{trial_type}_LSTM_filtered.csv'
right_output_file = rf'{base_path}\bflh_mtu_max_right_strides_ID{subject}_{session}_{trial_type}_LSTM_filtered.csv'
combined_output_file = rf'{base_path}\bflh_mtu_max_strides_ID{subject}_{session}_{trial_type}_LSTM_filtered.csv'
left_output_df.to_csv(left_output_file, index=False)
right_output_df.to_csv(right_output_file, index=False)
stride_output_df.to_csv(combined_output_file, index=False)

print(f"\n{'='*60}")
print(f"Processed {len(left_output_df)} LEFT strides and {len(right_output_df)} RIGHT strides")
print(f"(Strides = full gait cycle: same-foot contact to same-foot contact)")
print(f"{'='*60}")
print("\nLeft strides:")
print(left_output_df)
print("\nRight strides:")
print(right_output_df)
print(f"\nSaved to:\n  {left_output_file}\n  {right_output_file}\n  {combined_output_file}")
print("\nLeft stride summary:")
print(left_output_df.describe())
print("\nRight stride summary:")
print(right_output_df.describe())

# ===== SUMMARY PLOTS =====
fig, axes = plt.subplots(2, 3, figsize=(15, 10))

# Left max lengths
axes[0, 0].plot(left_output_df['stride_number'], left_output_df['bflh_max_length'], 'o-', color='blue')
axes[0, 0].set_xlabel('Stride Number')
axes[0, 0].set_ylabel('Max MTU Length (Normalized)')
axes[0, 0].set_title('Left BFLH Max Lengths Across Strides')
axes[0, 0].grid(True, alpha=0.3)

# Right max lengths
axes[0, 1].plot(right_output_df['stride_number'], right_output_df['bflh_max_length'], 'o-', color='red')
axes[0, 1].set_xlabel('Stride Number')
axes[0, 1].set_ylabel('Max MTU Length (Normalized)')
axes[0, 1].set_title('Right BFLH Max Lengths Across Strides')
axes[0, 1].grid(True, alpha=0.3)

# Left max velocities
axes[1, 0].plot(left_output_df['stride_number'], left_output_df['bflh_max_velocity'], 'o-', color='blue')
axes[1, 0].set_xlabel('Stride Number')
axes[1, 0].set_ylabel('Max MTU Velocity (Norm/s)')
axes[1, 0].set_title('Left BFLH Max Velocities Across Strides')
axes[1, 0].grid(True, alpha=0.3)

# Right max velocities
axes[1, 1].plot(right_output_df['stride_number'], right_output_df['bflh_max_velocity'], 'o-', color='red')
axes[1, 1].set_xlabel('Stride Number')
axes[1, 1].set_ylabel('Max MTU Velocity (Norm/s)')
axes[1, 1].set_title('Right BFLH Max Velocities Across Strides')
axes[1, 1].grid(True, alpha=0.3)

# Left avg lengthening velocities
axes[0, 2].plot(left_output_df['stride_number'], left_output_df['bflh_avg_lengthening_velocity'], 'o-', color='blue')
axes[0, 2].set_xlabel('Stride Number')
axes[0, 2].set_ylabel('Avg Lengthening Velocity (Norm/s)')
axes[0, 2].set_title('Left BFLH Avg Lengthening Velocities')
axes[0, 2].grid(True, alpha=0.3)

# Right avg lengthening velocities
axes[1, 2].plot(right_output_df['stride_number'], right_output_df['bflh_avg_lengthening_velocity'], 'o-', color='red')
axes[1, 2].set_xlabel('Stride Number')
axes[1, 2].set_ylabel('Avg Lengthening Velocity (Norm/s)')
axes[1, 2].set_title('Right BFLH Avg Lengthening Velocities')
axes[1, 2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(rf'{base_path}\bflh_mtu_all_strides_summary_ID{subject}_{session}_{trial_type}_LSTM_filtered.png', dpi=300, bbox_inches='tight')
plt.show()

print("\nSummary plot saved successfully!")

# ===== OVERLAY PLOTS: Last N strides by side (normalized to gait cycle %) =====
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
normalized_x = np.linspace(0, 100, 101)

n_left_strides = len(left_output_df)
n_right_strides = len(right_output_df)
n_left_to_plot = min(n_strides_to_plot, n_left_strides)
n_right_to_plot = min(n_strides_to_plot, n_right_strides)

# Select last N strides chronologically (lowest stride_number = closest to capture volume)
left_strides_to_plot = left_output_df.nsmallest(n_left_to_plot, 'stride_number')
right_strides_to_plot = right_output_df.nsmallest(n_right_to_plot, 'stride_number')

left_colors = cm.Blues(np.linspace(0.5, 0.95, max(n_left_to_plot, 1)))
right_colors = cm.Reds(np.linspace(0.5, 0.95, max(n_right_to_plot, 1)))

# Left BFLH lengths
for plot_idx, (_, row) in enumerate(left_strides_to_plot.iterrows()):
    stride_df = get_stride_window(mtu_lengths_df, row['start_time'], row['end_time'])
    if len(stride_df) > 1:
        stride_percent = np.linspace(0, 100, len(stride_df))
        interp_func = interp1d(stride_percent, stride_df['bflh_l'], kind='linear', fill_value='extrapolate')
        normalized_length = interp_func(normalized_x)
        axes[0, 0].plot(normalized_x, normalized_length,
                       color=left_colors[plot_idx], label=f'Stride {int(row["stride_number"])}', linewidth=2.5)
        max_idx = np.argmax(normalized_length)
        axes[0, 0].plot(normalized_x[max_idx], normalized_length[max_idx],
                       'o', color=left_colors[plot_idx], markersize=10,
                       markeredgecolor='black', markeredgewidth=2)

axes[0, 0].set_xlabel('Gait Cycle (%)', fontsize=14)
axes[0, 0].set_ylabel('MTU Length (Normalized)', fontsize=14)
axes[0, 0].set_title(f'Left BFLH Lengths - Last {n_left_to_plot} Strides', fontsize=14, fontweight='bold')
axes[0, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=11)
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].set_xlim([0, 100])

# Right BFLH lengths
for plot_idx, (_, row) in enumerate(right_strides_to_plot.iterrows()):
    stride_df = get_stride_window(mtu_lengths_df, row['start_time'], row['end_time'])
    if len(stride_df) > 1:
        stride_percent = np.linspace(0, 100, len(stride_df))
        interp_func = interp1d(stride_percent, stride_df['bflh_r'], kind='linear', fill_value='extrapolate')
        normalized_length = interp_func(normalized_x)
        axes[0, 1].plot(normalized_x, normalized_length,
                       color=right_colors[plot_idx], label=f'Stride {int(row["stride_number"])}', linewidth=2.5)
        max_idx = np.argmax(normalized_length)
        axes[0, 1].plot(normalized_x[max_idx], normalized_length[max_idx],
                       'o', color=right_colors[plot_idx], markersize=10,
                       markeredgecolor='black', markeredgewidth=2)

axes[0, 1].set_xlabel('Gait Cycle (%)', fontsize=14)
axes[0, 1].set_ylabel('MTU Length (Normalized)', fontsize=14)
axes[0, 1].set_title(f'Right BFLH Lengths - Last {n_right_to_plot} Strides', fontsize=14, fontweight='bold')
axes[0, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=11)
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].set_xlim([0, 100])

# Left BFLH velocities
for plot_idx, (_, row) in enumerate(left_strides_to_plot.iterrows()):
    stride_df = get_stride_window(mtu_lengths_df, row['start_time'], row['end_time'])
    if len(stride_df) > 1:
        stride_df = stride_df.copy()
        stride_df['bflh_l_vel'] = np.gradient(stride_df['bflh_l'], stride_df['time'])
        stride_percent = np.linspace(0, 100, len(stride_df))
        interp_func = interp1d(stride_percent, stride_df['bflh_l_vel'], kind='linear', fill_value='extrapolate')
        normalized_velocity = interp_func(normalized_x)
        axes[1, 0].plot(normalized_x, normalized_velocity,
                       color=left_colors[plot_idx], label=f'Stride {int(row["stride_number"])}', linewidth=2.5)
        max_idx = np.argmax(normalized_velocity)
        axes[1, 0].plot(normalized_x[max_idx], normalized_velocity[max_idx],
                       'o', color=left_colors[plot_idx], markersize=10,
                       markeredgecolor='black', markeredgewidth=2)

axes[1, 0].set_xlabel('Gait Cycle (%)', fontsize=14)
axes[1, 0].set_ylabel('MTU Velocity (Norm Units/s)', fontsize=14)
axes[1, 0].set_title(f'Left BFLH Velocities - Last {n_left_to_plot} Strides', fontsize=14, fontweight='bold')
axes[1, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=11)
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].set_xlim([0, 100])

# Right BFLH velocities
for plot_idx, (_, row) in enumerate(right_strides_to_plot.iterrows()):
    stride_df = get_stride_window(mtu_lengths_df, row['start_time'], row['end_time'])
    if len(stride_df) > 1:
        stride_df = stride_df.copy()
        stride_df['bflh_r_vel'] = np.gradient(stride_df['bflh_r'], stride_df['time'])
        stride_percent = np.linspace(0, 100, len(stride_df))
        interp_func = interp1d(stride_percent, stride_df['bflh_r_vel'], kind='linear', fill_value='extrapolate')
        normalized_velocity = interp_func(normalized_x)
        axes[1, 1].plot(normalized_x, normalized_velocity,
                       color=right_colors[plot_idx], label=f'Stride {int(row["stride_number"])}', linewidth=2.5)
        max_idx = np.argmax(normalized_velocity)
        axes[1, 1].plot(normalized_x[max_idx], normalized_velocity[max_idx],
                       'o', color=right_colors[plot_idx], markersize=10,
                       markeredgecolor='black', markeredgewidth=2)

axes[1, 1].set_xlabel('Gait Cycle (%)', fontsize=14)
axes[1, 1].set_ylabel('MTU Velocity (Norm Units/s)', fontsize=14)
axes[1, 1].set_title(f'Right BFLH Velocities - Last {n_right_to_plot} Strides', fontsize=14, fontweight='bold')
axes[1, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=11)
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].set_xlim([0, 100])

plt.tight_layout()
plt.savefig(rf'{base_path}\bflh_mtu_last{n_strides_to_plot}_strides_overlay_ID{subject}_{session}_{trial_type}_LSTM_filtered.png',
            dpi=300, bbox_inches='tight')
plt.show()

print(f"\nOverlay plot saved successfully!")
print(f"Plotted last {n_left_to_plot} LEFT strides and last {n_right_to_plot} RIGHT strides")