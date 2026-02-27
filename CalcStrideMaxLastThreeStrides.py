# Load in MOT file for individual steps/strides, calculate the BFLH peak MTU length and velocity for each step/stride, 
# and save the maximum values to a new csv file.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

import utilsKinematics

subject = 2
session = "S5"
base_path = rf'G:\Shared drives\Stanford Football\February_9\subject{subject}\Kinematics\Outputs'

# Load stride times csv
left_stride_times_file = rf'{base_path}\stride_times_left.csv'
left_stride_times_df = pd.read_csv(left_stride_times_file)
right_stride_times_file = rf'{base_path}\stride_times_right.csv'
right_stride_times_df = pd.read_csv(right_stride_times_file)

# load muscle-tendon unit lengths and velocities from csv in subject folder > Kinematics > Outputs

# This is the path for bflh lengths that are not normalized yet
#mtu_lengths_file = rf'{base_path}\muscle_tendon_lengths_ID{subject}_{session}_fly_LSTM.csv'

# Plot the normalized lengths using this csv file instead
mtu_lengths_file = rf'{base_path}\normalized_bflh_length_ID{subject}_{session}_decel_LSTM_filtered.csv'
mtu_lengths_df = pd.read_csv(mtu_lengths_file)

print(f"Loaded {len(left_stride_times_df)} left stride time points")
print(f"Loaded {len(right_stride_times_df)} right stride time points")

# Initialize lists to store max values for each stride
left_bflh_l_max_lengths = []
left_bflh_l_max_velocities = []
left_stride_start_times = []
left_stride_end_times = []

right_bflh_r_max_lengths = []
right_bflh_r_max_velocities = []
right_stride_start_times = []
right_stride_end_times = []

# Process LEFT strides
# Assumes stride times alternate between takeoff and touchdown
for i in range(0, len(left_stride_times_df) - 1):
    takeoff_time = left_stride_times_df['time'].iloc[i]
    touchdown_time = left_stride_times_df['time'].iloc[i + 1]
    
    # Extract stride data
    stride_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= takeoff_time) & 
        (mtu_lengths_df['time'] <= touchdown_time)
    ].reset_index(drop=True)
    
    if len(stride_mtu_df) > 0:
        # Calculate velocity
        stride_mtu_df['bflh_l_vel'] = np.gradient(stride_mtu_df['bflh_l'], stride_mtu_df['time'])
        
        # Find max values
        max_length = stride_mtu_df['bflh_l'].max()
        max_velocity = stride_mtu_df['bflh_l_vel'].max()
        
        # Store results
        left_bflh_l_max_lengths.append(max_length)
        left_bflh_l_max_velocities.append(max_velocity)
        left_stride_start_times.append(takeoff_time)
        left_stride_end_times.append(touchdown_time)

# Process RIGHT strides
for i in range(0, len(right_stride_times_df) - 1):
    takeoff_time = right_stride_times_df['time'].iloc[i]
    touchdown_time = right_stride_times_df['time'].iloc[i + 1]
    
    # Extract stride data
    stride_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= takeoff_time) & 
        (mtu_lengths_df['time'] <= touchdown_time)
    ].reset_index(drop=True)
    
    if len(stride_mtu_df) > 0:
        # Calculate velocity
        stride_mtu_df['bflh_r_vel'] = np.gradient(stride_mtu_df['bflh_r'], stride_mtu_df['time'])
        
        # Find max values
        max_length = stride_mtu_df['bflh_r'].max()
        max_velocity = stride_mtu_df['bflh_r_vel'].max()
        
        # Store results
        right_bflh_r_max_lengths.append(max_length)
        right_bflh_r_max_velocities.append(max_velocity)
        right_stride_start_times.append(takeoff_time)
        right_stride_end_times.append(touchdown_time)

# Create output dataframes
left_output_df = pd.DataFrame({
    'stride_start_time': left_stride_start_times,
    'stride_end_time': left_stride_end_times,
    'left_bflh_max_length': left_bflh_l_max_lengths,
    'left_bflh_max_velocity': left_bflh_l_max_velocities
})

right_output_df = pd.DataFrame({
    'stride_start_time': right_stride_start_times,
    'stride_end_time': right_stride_end_times,
    'right_bflh_max_length': right_bflh_r_max_lengths,
    'right_bflh_max_velocity': right_bflh_r_max_velocities
})

# Save to CSV files
left_output_file = rf'{base_path}\bflh_mtu_max_left_strides_ID{subject}_{session}_decel_LSTM_filtered.csv'
right_output_file = rf'{base_path}\bflh_mtu_max_right_strides_ID{subject}_{session}_decel_LSTM_filtered.csv'

left_output_df.to_csv(left_output_file, index=False)
right_output_df.to_csv(right_output_file, index=False)

print(f"Processed {len(left_output_df)} left strides")
print(f"Processed {len(right_output_df)} right strides")
print(f"Saved left stride data to {left_output_file}")
print(f"Saved right stride data to {right_output_file}")

# Display summary statistics
print("\nLeft Stride Summary:")
print(left_output_df.describe())
print("\nRight Stride Summary:")
print(right_output_df.describe())

# Create visualization for all strides
fig, axes = plt.subplots(2, 2, figsize=(15, 10))

# Left max lengths
axes[0, 0].plot(range(len(left_bflh_l_max_lengths)), left_bflh_l_max_lengths, 'o-', color='blue')
axes[0, 0].set_xlabel('Stride Number')
axes[0, 0].set_ylabel('Max MTU Length (Normalized lengths)')
axes[0, 0].set_title('Left BFLH Max Lengths Across Strides')
axes[0, 0].grid(True)

# Right max lengths
axes[0, 1].plot(range(len(right_bflh_r_max_lengths)), right_bflh_r_max_lengths, 'o-', color='red')
axes[0, 1].set_xlabel('Stride Number')
axes[0, 1].set_ylabel('Max MTU Length (Normalized Lengths)')
axes[0, 1].set_title('Right BFLH Max Lengths Across Strides')
axes[0, 1].grid(True)

# Left max velocities
axes[1, 0].plot(range(len(left_bflh_l_max_velocities)), left_bflh_l_max_velocities, 'o-', color='blue')
axes[1, 0].set_xlabel('Stride Number')
axes[1, 0].set_ylabel('Max MTU Velocity (Normalzied Lengths/s)')
axes[1, 0].set_title('Left BFLH Max Velocities Across Strides')
axes[1, 0].grid(True)

# Right max velocities
axes[1, 1].plot(range(len(right_bflh_r_max_velocities)), right_bflh_r_max_velocities, 'o-', color='red')
axes[1, 1].set_xlabel('Stride Number')
axes[1, 1].set_ylabel('Max MTU Velocity (Normalzied Lengths/s)')
axes[1, 1].set_title('Right BFLH Max Velocities Across Strides')
axes[1, 1].grid(True)

plt.tight_layout()
plt.savefig(r'G:\Shared drives\Stanford Football\February_9\subject2\Kinematics\Outputs\bflh_mtu_all_strides_summary_ID2_S5_decel_LSTM_filtered.png')
plt.show()

print("\nPlot saved successfully!")

# ========== MODIFIED SECTION: Plot only last 3 strides ==========

# Create overlay plots for LAST 3 STRIDES ONLY with peak markers
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Generate colors for each stride
from matplotlib import cm

# Get indices for last 3 strides
n_left_strides = len(left_bflh_l_max_lengths)
n_right_strides = len(right_bflh_r_max_lengths)

# Determine how many strides to plot (up to 3)
n_left_to_plot = min(6, n_left_strides) #changed from 3 to 6 for decels
n_right_to_plot = min(6, n_right_strides) #changed from 3 to 6 for decels

# Get indices of last 3 strides
left_stride_indices = list(range(n_left_strides - n_left_to_plot, n_left_strides))
right_stride_indices = list(range(n_right_strides - n_right_to_plot, n_right_strides))

# Generate colors for the strides we're plotting
left_colors = cm.rainbow(np.linspace(0, 1, n_left_to_plot))
right_colors = cm.rainbow(np.linspace(0, 1, n_right_to_plot))

# Define normalized x-axis (0 to 100%)
normalized_x = np.linspace(0, 100, 101)

# Plot LEFT BFLH LENGTHS (last 3 strides only)
for plot_idx, stride_idx in enumerate(left_stride_indices):
    start_time = left_stride_start_times[stride_idx]
    end_time = left_stride_end_times[stride_idx]
    
    stride_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(stride_mtu_df) > 0:
        # Create interpolation function
        stride_percent = np.linspace(0, 100, len(stride_mtu_df))
        interp_func = interp1d(stride_percent, stride_mtu_df['bflh_l'], 
                              kind='linear', fill_value='extrapolate')
        
        # Interpolate to normalized grid
        normalized_length = interp_func(normalized_x)
        
        # Plot the stride
        axes[0, 0].plot(normalized_x, normalized_length, 
                       color=left_colors[plot_idx], label=f'Stride {stride_idx+1}', linewidth=2)
        
        # Mark the peak
        max_idx = np.argmax(normalized_length)
        axes[0, 0].plot(normalized_x[max_idx], normalized_length[max_idx], 
                       'o', color=left_colors[plot_idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[0, 0].set_xlabel('Stride Cycle (%)', fontsize=18)
axes[0, 0].set_ylabel('MTU Length (Normalized Lengths)', fontsize=18)
axes[0, 0].set_title('Left BFLH Lengths - Last 6 Strides Overlaid', fontsize=18, fontweight='bold')
axes[0, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=18)
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].set_xlim([0, 100])

# Plot RIGHT BFLH LENGTHS (last 3 strides only)
for plot_idx, stride_idx in enumerate(right_stride_indices):
    start_time = right_stride_start_times[stride_idx]
    end_time = right_stride_end_times[stride_idx]
    
    stride_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(stride_mtu_df) > 0:
        # Create interpolation function
        stride_percent = np.linspace(0, 100, len(stride_mtu_df))
        interp_func = interp1d(stride_percent, stride_mtu_df['bflh_r'], 
                              kind='linear', fill_value='extrapolate')
        
        # Interpolate to normalized grid
        normalized_length = interp_func(normalized_x)
        
        # Plot the stride
        axes[0, 1].plot(normalized_x, normalized_length, 
                       color=right_colors[plot_idx], label=f'Stride {stride_idx+1}', linewidth=2)
        
        # Mark the peak
        max_idx = np.argmax(normalized_length)
        axes[0, 1].plot(normalized_x[max_idx], normalized_length[max_idx], 
                       'o', color=right_colors[plot_idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[0, 1].set_xlabel('Stride Cycle (%)', fontsize=18)
axes[0, 1].set_ylabel('MTU Length (Normalized Lengths)', fontsize=18)
axes[0, 1].set_title('Right BFLH Lengths - Last 6 Strides Overlaid', fontsize=18, fontweight='bold')
axes[0, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=18)
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].set_xlim([0, 100])

# Plot LEFT BFLH VELOCITIES (last 3 strides only)
for plot_idx, stride_idx in enumerate(left_stride_indices):
    start_time = left_stride_start_times[stride_idx]
    end_time = left_stride_end_times[stride_idx]
    
    stride_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(stride_mtu_df) > 0:
        # Calculate velocity
        stride_mtu_df['bflh_l_vel'] = np.gradient(stride_mtu_df['bflh_l'], stride_mtu_df['time'])
        
        # Create interpolation function
        stride_percent = np.linspace(0, 100, len(stride_mtu_df))
        interp_func = interp1d(stride_percent, stride_mtu_df['bflh_l_vel'], 
                              kind='linear', fill_value='extrapolate')
        
        # Interpolate to normalized grid
        normalized_velocity = interp_func(normalized_x)
        
        # Plot the stride
        axes[1, 0].plot(normalized_x, normalized_velocity, 
                       color=left_colors[plot_idx], label=f'Stride {stride_idx+1}', linewidth=2)
        
        # Mark the peak
        max_idx = np.argmax(normalized_velocity)
        axes[1, 0].plot(normalized_x[max_idx], normalized_velocity[max_idx], 
                       'o', color=left_colors[plot_idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[1, 0].set_xlabel('Stride Cycle (%)', fontsize=18)
axes[1, 0].set_ylabel('MTU Velocity (Norm Lengths/s)', fontsize=18)
axes[1, 0].set_title('Left BFLH Velocities - Last 6 Strides Overlaid', fontsize=18, fontweight='bold')
axes[1, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=18)
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].set_xlim([0, 100])


# Plot RIGHT BFLH VELOCITIES (last 3 strides only)
for plot_idx, stride_idx in enumerate(right_stride_indices):
    start_time = right_stride_start_times[stride_idx]
    end_time = right_stride_end_times[stride_idx]
    
    stride_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(stride_mtu_df) > 0:
        # Calculate velocity
        stride_mtu_df['bflh_r_vel'] = np.gradient(stride_mtu_df['bflh_r'], stride_mtu_df['time'])
        
        # Create interpolation function
        stride_percent = np.linspace(0, 100, len(stride_mtu_df))
        interp_func = interp1d(stride_percent, stride_mtu_df['bflh_r_vel'], 
                              kind='linear', fill_value='extrapolate')
        
        # Interpolate to normalized grid
        normalized_velocity = interp_func(normalized_x)
        
        # Plot the stride
        axes[1, 1].plot(normalized_x, normalized_velocity, 
                       color=right_colors[plot_idx], label=f'Stride {stride_idx+1}', linewidth=2)
        
        # Mark the peak
        max_idx = np.argmax(normalized_velocity)
        axes[1, 1].plot(normalized_x[max_idx], normalized_velocity[max_idx], 
                       'o', color=right_colors[plot_idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[1, 1].set_xlabel('Stride Cycle (%)', fontsize=18)
axes[1, 1].set_ylabel('MTU Velocity (Norm Lengths/s)', fontsize=18)
axes[1, 1].set_title('Right BFLH Velocities - Last 6 Strides Overlaid', fontsize=18, fontweight='bold')
axes[1, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=18)
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].set_xlim([0, 100])

plt.tight_layout()
plt.savefig(rf'{base_path}\bflh_mtu_last6_strides_overlay_ID{subject}_{session}_fly_LSTM.png', 
            dpi=300, bbox_inches='tight')
plt.show()

print("\nOverlay plot saved successfully!")
print(f"Plotted last {n_left_to_plot} left strides and last {n_right_to_plot} right strides")