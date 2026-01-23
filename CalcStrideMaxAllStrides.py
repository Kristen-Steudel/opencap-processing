# Load in MOT file for individual steps/strides, calculate the BFLH peak MTU length and velocity for each step/stride, 
# and save the maximum values to a new csv file.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import utilsKinematics

subject = 2
session = "S2"
base_path = rf'G:\Shared drives\Stanford Football\January_19\subject{subject}\Kinematics\Outputs'

# load stride times csv
# Load stride times csv
left_stride_times_file = rf'{base_path}\stride_times_left.csv'
left_stride_times_df = pd.read_csv(left_stride_times_file)
right_stride_times_file = rf'{base_path}\stride_times_right.csv'
right_stride_times_df = pd.read_csv(right_stride_times_file)

# load muscle-tendon unit lengths and velocities from csv in subject folder > Kinematics > Outputs
mtu_lengths_file = rf'{base_path}\muscle_tendon_lengths_ID{subject}_{session}_fly_LSTM.csv'
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
for i in range(0, len(right_stride_times_df) - 1, 2):
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
left_output_file = rf'{base_path}\bflh_mtu_max_left_strides_ID{subject}_{session}_fly_LSTM.csv'
right_output_file = rf'{base_path}\bflh_mtu_max_right_strides_ID{subject}_{session}_fly_LSTM.csv'

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
axes[0, 0].set_ylabel('Max MTU Length (m)')
axes[0, 0].set_title('Left BFLH Max Lengths Across Strides')
axes[0, 0].grid(True)

# Right max lengths
axes[0, 1].plot(range(len(right_bflh_r_max_lengths)), right_bflh_r_max_lengths, 'o-', color='red')
axes[0, 1].set_xlabel('Stride Number')
axes[0, 1].set_ylabel('Max MTU Length (m)')
axes[0, 1].set_title('Right BFLH Max Lengths Across Strides')
axes[0, 1].grid(True)

# Left max velocities
axes[1, 0].plot(range(len(left_bflh_l_max_velocities)), left_bflh_l_max_velocities, 'o-', color='blue')
axes[1, 0].set_xlabel('Stride Number')
axes[1, 0].set_ylabel('Max MTU Velocity (m/s)')
axes[1, 0].set_title('Left BFLH Max Velocities Across Strides')
axes[1, 0].grid(True)

# Right max velocities
axes[1, 1].plot(range(len(right_bflh_r_max_velocities)), right_bflh_r_max_velocities, 'o-', color='red')
axes[1, 1].set_xlabel('Stride Number')
axes[1, 1].set_ylabel('Max MTU Velocity (m/s)')
axes[1, 1].set_title('Right BFLH Max Velocities Across Strides')
axes[1, 1].grid(True)

plt.tight_layout()
plt.savefig(r'G:\Shared drives\Stanford Football\January_19\subject10\Kinematics\Outputs\bflh_mtu_all_strides_summary_ID10_S2_fly_LSTM.png')
plt.show()

print("\nPlot saved successfully!")

# Create overlay plots for all strides with peak markers
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Generate colors for each stride
from matplotlib import cm
n_left_strides = len(left_bflh_l_max_lengths)
n_right_strides = len(right_bflh_r_max_lengths)
left_colors = cm.rainbow(np.linspace(0, 1, n_left_strides))
right_colors = cm.rainbow(np.linspace(0, 1, n_right_strides))

# Plot LEFT BFLH LENGTHS
for idx, (start_time, end_time) in enumerate(zip(left_stride_start_times, left_stride_end_times)):
    stride_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(stride_mtu_df) > 0:
        # Normalize time to start at 0 for each stride
        normalized_time = stride_mtu_df['time'] - stride_mtu_df['time'].iloc[0]
        
        # Plot the stride
        axes[0, 0].plot(normalized_time, stride_mtu_df['bflh_l'], 
                       color=left_colors[idx], label=f'Stride {idx+1}', linewidth=2)
        
        # Mark the peak
        max_idx = stride_mtu_df['bflh_l'].idxmax()
        axes[0, 0].plot(normalized_time.iloc[max_idx], stride_mtu_df['bflh_l'].iloc[max_idx], 
                       'o', color=left_colors[idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[0, 0].set_xlabel('Time (s)', fontsize=12)
axes[0, 0].set_ylabel('MTU Length (m)', fontsize=12)
axes[0, 0].set_title('Left BFLH Lengths - All Strides Overlaid', fontsize=14, fontweight='bold')
axes[0, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
axes[0, 0].grid(True, alpha=0.3)

# Plot RIGHT BFLH LENGTHS
for idx, (start_time, end_time) in enumerate(zip(right_stride_start_times, right_stride_end_times)):
    stride_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(stride_mtu_df) > 0:
        # Normalize time to start at 0 for each stride
        normalized_time = stride_mtu_df['time'] - stride_mtu_df['time'].iloc[0]
        
        # Plot the stride
        axes[0, 1].plot(normalized_time, stride_mtu_df['bflh_r'], 
                       color=right_colors[idx], label=f'Stride {idx+1}', linewidth=2)
        
        # Mark the peak
        max_idx = stride_mtu_df['bflh_r'].idxmax()
        axes[0, 1].plot(normalized_time.iloc[max_idx], stride_mtu_df['bflh_r'].iloc[max_idx], 
                       'o', color=right_colors[idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[0, 1].set_xlabel('Time (s)', fontsize=12)
axes[0, 1].set_ylabel('MTU Length (m)', fontsize=12)
axes[0, 1].set_title('Right BFLH Lengths - All Strides Overlaid', fontsize=14, fontweight='bold')
axes[0, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
axes[0, 1].grid(True, alpha=0.3)

# Plot LEFT BFLH VELOCITIES
for idx, (start_time, end_time) in enumerate(zip(left_stride_start_times, left_stride_end_times)):
    stride_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(stride_mtu_df) > 0:
        # Calculate velocity
        stride_mtu_df['bflh_l_vel'] = np.gradient(stride_mtu_df['bflh_l'], stride_mtu_df['time'])
        
        # Normalize time to start at 0 for each stride
        normalized_time = stride_mtu_df['time'] - stride_mtu_df['time'].iloc[0]
        
        # Plot the stride
        axes[1, 0].plot(normalized_time, stride_mtu_df['bflh_l_vel'], 
                       color=left_colors[idx], label=f'Stride {idx+1}', linewidth=2)
        
        # Mark the peak
        max_idx = stride_mtu_df['bflh_l_vel'].idxmax()
        axes[1, 0].plot(normalized_time.iloc[max_idx], stride_mtu_df['bflh_l_vel'].iloc[max_idx], 
                       'o', color=left_colors[idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[1, 0].set_xlabel('Time (s)', fontsize=12)
axes[1, 0].set_ylabel('MTU Velocity (m/s)', fontsize=12)
axes[1, 0].set_title('Left BFLH Velocities - All Strides Overlaid', fontsize=14, fontweight='bold')
axes[1, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
axes[1, 0].grid(True, alpha=0.3)

# Plot RIGHT BFLH VELOCITIES
for idx, (start_time, end_time) in enumerate(zip(right_stride_start_times, right_stride_end_times)):
    stride_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(stride_mtu_df) > 0:
        # Calculate velocity
        stride_mtu_df['bflh_r_vel'] = np.gradient(stride_mtu_df['bflh_r'], stride_mtu_df['time'])
        
        # Normalize time to start at 0 for each stride
        normalized_time = stride_mtu_df['time'] - stride_mtu_df['time'].iloc[0]
        
        # Plot the stride
        axes[1, 1].plot(normalized_time, stride_mtu_df['bflh_r_vel'], 
                       color=right_colors[idx], label=f'Stride {idx+1}', linewidth=2)
        
        # Mark the peak
        max_idx = stride_mtu_df['bflh_r_vel'].idxmax()
        axes[1, 1].plot(normalized_time.iloc[max_idx], stride_mtu_df['bflh_r_vel'].iloc[max_idx], 
                       'o', color=right_colors[idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[1, 1].set_xlabel('Time (s)', fontsize=12)
axes[1, 1].set_ylabel('MTU Velocity (m/s)', fontsize=12)
axes[1, 1].set_title('Right BFLH Velocities - All Strides Overlaid', fontsize=14, fontweight='bold')
axes[1, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(rf'G:\Shared drives\Stanford Football\January_19\subject10\Kinematics\Outputs\bflh_mtu_all_strides_overlay_ID{subject}_{session}_fly_LSTM.png', 
            dpi=300, bbox_inches='tight')
plt.show()

print("\nOverlay plot saved successfully!")