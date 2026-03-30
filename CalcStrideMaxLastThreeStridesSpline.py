import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from matplotlib import cm

# Requirements to change for each run
subject = 10
session = "S6"
date = "February_23"
trial_type = "fly"
filt_freq = 10
n_strides_to_plot = 3  # set to 3 for last three strides

base_path = (
    rf'G:\Shared drives\Stanford Football\{date}\subject{subject}'
    r'\CleanedKinematics\Outputs'
)
trial_name = f'ID{subject}_{session}_{trial_type}_LSTM_filtered_{filt_freq}Hz'

# Load stride times.
left_stride_times_file = rf'{base_path}\stride_times_left.csv'
right_stride_times_file = rf'{base_path}\stride_times_right.csv'
left_stride_times_df = pd.read_csv(left_stride_times_file)
right_stride_times_df = pd.read_csv(right_stride_times_file)

# Load filtered normalized lengths and spline velocities.
mtu_lengths_file = rf'{base_path}\normalized_muscle_tendon_lengths_{trial_name}_filtered_{filt_freq}Hz.csv'
mtu_velocities_file = rf'{base_path}\muscle_tendon_velocities_spline_{trial_name}_filtered_{filt_freq}Hz.csv'
mtu_lengths_df = pd.read_csv(mtu_lengths_file)
mtu_velocities_df = pd.read_csv(mtu_velocities_file)

print(f"Loaded {len(left_stride_times_df)} left stride time points")
print(f"Loaded {len(right_stride_times_df)} right stride time points")
print(f"Loaded lengths from: {mtu_lengths_file}")
print(f"Loaded spline velocities from: {mtu_velocities_file}")


def get_stride_window(df, start_time, end_time):
    return df[(df['time'] >= start_time) & (df['time'] <= end_time)].reset_index(drop=True)


# Store per-stride metrics.
left_bflh_l_max_lengths = []
left_bflh_l_max_velocities = []
left_bflh_l_avg_velocities = []
left_stride_start_times = []
left_stride_end_times = []

right_bflh_r_max_lengths = []
right_bflh_r_max_velocities = []
right_bflh_r_avg_velocities = []
right_stride_start_times = []
right_stride_end_times = []

# Process left strides.
for i in range(0, len(left_stride_times_df) - 1):
    takeoff_time = left_stride_times_df['time'].iloc[i]
    touchdown_time = left_stride_times_df['time'].iloc[i + 1]

    stride_lengths = get_stride_window(mtu_lengths_df, takeoff_time, touchdown_time)
    stride_velocities = get_stride_window(mtu_velocities_df, takeoff_time, touchdown_time)

    if len(stride_lengths) > 0 and len(stride_velocities) > 0:
        max_length = stride_lengths['bflh_l'].max()
        max_velocity = stride_velocities['bflh_l'].max()
        avg_velocity = stride_velocities.loc[
            stride_velocities['bflh_l'] > 0, 'bflh_l'
        ].mean()

        left_bflh_l_max_lengths.append(max_length)
        left_bflh_l_max_velocities.append(max_velocity)
        left_bflh_l_avg_velocities.append(avg_velocity)
        left_stride_start_times.append(takeoff_time)
        left_stride_end_times.append(touchdown_time)

# Process right strides.
for i in range(0, len(right_stride_times_df) - 1):
    takeoff_time = right_stride_times_df['time'].iloc[i]
    touchdown_time = right_stride_times_df['time'].iloc[i + 1]

    stride_lengths = get_stride_window(mtu_lengths_df, takeoff_time, touchdown_time)
    stride_velocities = get_stride_window(mtu_velocities_df, takeoff_time, touchdown_time)

    if len(stride_lengths) > 0 and len(stride_velocities) > 0:
        max_length = stride_lengths['bflh_r'].max()
        max_velocity = stride_velocities['bflh_r'].max()
        avg_velocity = stride_velocities.loc[
            stride_velocities['bflh_r'] > 0, 'bflh_r'
        ].mean()

        right_bflh_r_max_lengths.append(max_length)
        right_bflh_r_max_velocities.append(max_velocity)
        right_bflh_r_avg_velocities.append(avg_velocity)
        right_stride_start_times.append(takeoff_time)
        right_stride_end_times.append(touchdown_time)

# Save stride max metrics.
left_output_df = pd.DataFrame({
    'stride_start_time': left_stride_start_times,
    'stride_end_time': left_stride_end_times,
    'left_bflh_max_length': left_bflh_l_max_lengths,
    'left_bflh_max_velocity_spline': left_bflh_l_max_velocities,
    'left_bflh_avg_velocity_spline': left_bflh_l_avg_velocities,
})

right_output_df = pd.DataFrame({
    'stride_start_time': right_stride_start_times,
    'stride_end_time': right_stride_end_times,
    'right_bflh_max_length': right_bflh_r_max_lengths,
    'right_bflh_max_velocity_spline': right_bflh_r_max_velocities,
    'right_bflh_avg_velocity_spline': right_bflh_r_avg_velocities,
})

left_output_file = rf'{base_path}\bflh_mtu_max_left_strides_spline_ID{subject}_{session}_{trial_type}_LSTM_filtered_{filt_freq}Hz.csv'
right_output_file = rf'{base_path}\bflh_mtu_max_right_strides_spline_ID{subject}_{session}_{trial_type}_LSTM_filtered_{filt_freq}Hz.csv'

left_output_df.to_csv(left_output_file, index=False)
right_output_df.to_csv(right_output_file, index=False)

print(f"Processed {len(left_output_df)} left strides")
print(f"Processed {len(right_output_df)} right strides")
print(f"Saved left stride data to {left_output_file}")
print(f"Saved right stride data to {right_output_file}")

print("\nLeft Stride Summary:")
print(left_output_df.describe())
print("\nRight Stride Summary:")
print(right_output_df.describe())

# Summary plots across all strides.
fig, axes = plt.subplots(2, 3, figsize=(15, 10))

axes[0, 0].plot(range(len(left_bflh_l_max_lengths)), left_bflh_l_max_lengths, 'o-', color='blue')
axes[0, 0].set_xlabel('Stride Number')
axes[0, 0].set_ylabel('Max MTU Length (Normalized)')
axes[0, 0].set_title('Left BFLH Max Lengths Across Strides')
axes[0, 0].grid(True)

axes[0, 1].plot(range(len(right_bflh_r_max_lengths)), right_bflh_r_max_lengths, 'o-', color='red')
axes[0, 1].set_xlabel('Stride Number')
axes[0, 1].set_ylabel('Max MTU Length (Normalized)')
axes[0, 1].set_title('Right BFLH Max Lengths Across Strides')
axes[0, 1].grid(True)

axes[1, 0].plot(range(len(left_bflh_l_max_velocities)), left_bflh_l_max_velocities, 'o-', color='blue')
axes[1, 0].set_xlabel('Stride Number')
axes[1, 0].set_ylabel('Max MTU Velocity (Norm Length/s)')
axes[1, 0].set_title('Left BFLH Max Spline Velocities')
axes[1, 0].grid(True)

axes[1, 1].plot(range(len(right_bflh_r_max_velocities)), right_bflh_r_max_velocities, 'o-', color='red')
axes[1, 1].set_xlabel('Stride Number')
axes[1, 1].set_ylabel('Max MTU Velocity (Norm Length/s)')
axes[1, 1].set_title('Right BFLH Max Spline Velocities')
axes[1, 1].grid(True)

axes[0, 2].plot(range(len(left_bflh_l_avg_velocities)), left_bflh_l_avg_velocities, 'o-', color='blue')
axes[0, 2].set_xlabel('Stride Number')
axes[0, 2].set_ylabel('Avg Lengthening Velocity (Norm Length/s)')
axes[0, 2].set_title('Left BFLH Avg Spline Lengthening Velocities')
axes[0, 2].grid(True)

axes[1, 2].plot(range(len(right_bflh_r_avg_velocities)), right_bflh_r_avg_velocities, 'o-', color='red')
axes[1, 2].set_xlabel('Stride Number')
axes[1, 2].set_ylabel('Avg Lengthening Velocity (Norm Length/s)')
axes[1, 2].set_title('Right BFLH Avg Spline Lengthening Velocities')
axes[1, 2].grid(True)

plt.tight_layout()
summary_plot_path = (
    rf'{base_path}\bflh_mtu_all_strides_summary_spline_ID{subject}_{session}_{trial_type}_LSTM_filtered_{filt_freq}Hz.png'
)
plt.savefig(summary_plot_path)
plt.show()
print("\nSummary plot saved successfully!")

# Overlay plots for last N strides.
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
n_left_strides = len(left_bflh_l_max_lengths)
n_right_strides = len(right_bflh_r_max_lengths)
n_left_to_plot = min(n_strides_to_plot, n_left_strides)
n_right_to_plot = min(n_strides_to_plot, n_right_strides)

left_stride_indices = list(range(n_left_strides - n_left_to_plot, n_left_strides))
right_stride_indices = list(range(n_right_strides - n_right_to_plot, n_right_strides))
left_colors = cm.rainbow(np.linspace(0, 1, max(n_left_to_plot, 1)))
right_colors = cm.rainbow(np.linspace(0, 1, max(n_right_to_plot, 1)))
normalized_x = np.linspace(0, 100, 101)

# Left lengths.
for plot_idx, stride_idx in enumerate(left_stride_indices):
    start_time = left_stride_start_times[stride_idx]
    end_time = left_stride_end_times[stride_idx]
    stride_df = get_stride_window(mtu_lengths_df, start_time, end_time)
    if len(stride_df) > 1:
        stride_percent = np.linspace(0, 100, len(stride_df))
        interp_func = interp1d(stride_percent, stride_df['bflh_l'], kind='linear', fill_value='extrapolate')
        normalized_length = interp_func(normalized_x)
        axes[0, 0].plot(normalized_x, normalized_length, color=left_colors[plot_idx], label=f'Stride {stride_idx + 1}', linewidth=2)
        max_idx = np.argmax(normalized_length)
        axes[0, 0].plot(normalized_x[max_idx], normalized_length[max_idx], 'o', color=left_colors[plot_idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[0, 0].set_xlabel('Stride Cycle (%)', fontsize=14)
axes[0, 0].set_ylabel('MTU Length (Normalized)', fontsize=14)
axes[0, 0].set_title(f'Left BFLH Lengths - Last {n_left_to_plot} Strides', fontsize=14, fontweight='bold')
axes[0, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].set_xlim([0, 100])

# Right lengths.
for plot_idx, stride_idx in enumerate(right_stride_indices):
    start_time = right_stride_start_times[stride_idx]
    end_time = right_stride_end_times[stride_idx]
    stride_df = get_stride_window(mtu_lengths_df, start_time, end_time)
    if len(stride_df) > 1:
        stride_percent = np.linspace(0, 100, len(stride_df))
        interp_func = interp1d(stride_percent, stride_df['bflh_r'], kind='linear', fill_value='extrapolate')
        normalized_length = interp_func(normalized_x)
        axes[0, 1].plot(normalized_x, normalized_length, color=right_colors[plot_idx], label=f'Stride {stride_idx + 1}', linewidth=2)
        max_idx = np.argmax(normalized_length)
        axes[0, 1].plot(normalized_x[max_idx], normalized_length[max_idx], 'o', color=right_colors[plot_idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[0, 1].set_xlabel('Stride Cycle (%)', fontsize=14)
axes[0, 1].set_ylabel('MTU Length (Normalized)', fontsize=14)
axes[0, 1].set_title(f'Right BFLH Lengths - Last {n_right_to_plot} Strides', fontsize=14, fontweight='bold')
axes[0, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].set_xlim([0, 100])

# Left velocities (from spline output).
for plot_idx, stride_idx in enumerate(left_stride_indices):
    start_time = left_stride_start_times[stride_idx]
    end_time = left_stride_end_times[stride_idx]
    stride_df = get_stride_window(mtu_velocities_df, start_time, end_time)
    if len(stride_df) > 1:
        stride_percent = np.linspace(0, 100, len(stride_df))
        interp_func = interp1d(stride_percent, stride_df['bflh_l'], kind='linear', fill_value='extrapolate')
        normalized_velocity = interp_func(normalized_x)
        axes[1, 0].plot(normalized_x, normalized_velocity, color=left_colors[plot_idx], label=f'Stride {stride_idx + 1}', linewidth=2)
        max_idx = np.argmax(normalized_velocity)
        axes[1, 0].plot(normalized_x[max_idx], normalized_velocity[max_idx], 'o', color=left_colors[plot_idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[1, 0].set_xlabel('Stride Cycle (%)', fontsize=14)
axes[1, 0].set_ylabel('MTU Velocity (Norm Length/s)', fontsize=14)
axes[1, 0].set_title(f'Left BFLH Spline Velocities - Last {n_left_to_plot} Strides', fontsize=14, fontweight='bold')
axes[1, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].set_xlim([0, 100])

# Right velocities (from spline output).
for plot_idx, stride_idx in enumerate(right_stride_indices):
    start_time = right_stride_start_times[stride_idx]
    end_time = right_stride_end_times[stride_idx]
    stride_df = get_stride_window(mtu_velocities_df, start_time, end_time)
    if len(stride_df) > 1:
        stride_percent = np.linspace(0, 100, len(stride_df))
        interp_func = interp1d(stride_percent, stride_df['bflh_r'], kind='linear', fill_value='extrapolate')
        normalized_velocity = interp_func(normalized_x)
        axes[1, 1].plot(normalized_x, normalized_velocity, color=right_colors[plot_idx], label=f'Stride {stride_idx + 1}', linewidth=2)
        max_idx = np.argmax(normalized_velocity)
        axes[1, 1].plot(normalized_x[max_idx], normalized_velocity[max_idx], 'o', color=right_colors[plot_idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[1, 1].set_xlabel('Stride Cycle (%)', fontsize=14)
axes[1, 1].set_ylabel('MTU Velocity (Norm Length/s)', fontsize=14)
axes[1, 1].set_title(f'Right BFLH Spline Velocities - Last {n_right_to_plot} Strides', fontsize=14, fontweight='bold')
axes[1, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].set_xlim([0, 100])

plt.tight_layout()
overlay_plot_path = (
    rf'{base_path}\bflh_mtu_last{n_strides_to_plot}_strides_overlay_spline_ID{subject}_{session}_{trial_type}_LSTM_filtered_{filt_freq}Hz.png'
)
plt.savefig(overlay_plot_path, dpi=300, bbox_inches='tight')
plt.show()

print("\nOverlay plot saved successfully!")
print(f"Plotted last {n_left_to_plot} left strides and last {n_right_to_plot} right strides")
