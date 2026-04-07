# Load in MOT file for individual steps/steps, calculate the BFLH peak MTU length and velocity for each step/step, 
# and save the maximum values to a new csv file.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

import utilsKinematics

subject = 2
session = "S7"
base_path = rf'G:\Shared drives\Stanford Football\March_2\subject{subject}\CleanedKinematics\filtered_post_augmentation\Outputs'
type = 'sprint'
filt_freq = 8  # Hz, was 15 Hz

# Load step times csv
left_step_times_file = rf'{base_path}\step_times_left.csv'
left_step_times_df = pd.read_csv(left_step_times_file)
right_step_times_file = rf'{base_path}\step_times_right.csv'
right_step_times_df = pd.read_csv(right_step_times_file)

# load muscle-tendon unit lengths and velocities from csv in subject folder > Kinematics > Outputs

# This is the path for bflh lengths that are not normalized yet
#mtu_lengths_file = rf'{base_path}\muscle_tendon_lengths_ID{subject}_{session}_fly_LSTM.csv'

# Plot the normalized lengths using this csv file instead
mtu_lengths_file = rf'{base_path}\normalized_muscle_tendon_lengths_ID{subject}_{session}_{type}_LSTM_filtpostaug15Hz_filteredkinematics_15Hz_filtered_15Hz.csv'
#normalized_muscle_tendon_lengths_ID2_S7_sprint_LSTM_filtpostaug15Hz_filteredkinematics_15Hz_filtered_15Hz
mtu_lengths_df = pd.read_csv(mtu_lengths_file)

print(f"Loaded {len(left_step_times_df)} left step time points")
print(f"Loaded {len(right_step_times_df)} right step time points")

# Initialize lists to store max values for each step
left_bflh_l_max_lengths = []
left_bflh_l_max_velocities = []
left_bflh_l_avg_velocities = []
left_step_start_times = []
left_step_end_times = []

right_bflh_r_max_lengths = []
right_bflh_r_max_velocities = []
right_bflh_r_avg_velocities = []
right_step_start_times = []
right_step_end_times = []

# Process LEFT steps
# Assumes step times alternate between takeoff and touchdown
for i in range(0, len(left_step_times_df) - 1):
    takeoff_time = left_step_times_df['time'].iloc[i]
    touchdown_time = left_step_times_df['time'].iloc[i + 1]
    
    # Extract step data
    step_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= takeoff_time) & 
        (mtu_lengths_df['time'] <= touchdown_time)
    ].reset_index(drop=True)
    
    if len(step_mtu_df) > 0:
        # Calculate velocity
        step_mtu_df['bflh_l_vel'] = np.gradient(step_mtu_df['bflh_l'], step_mtu_df['time'])
        
        # Find max values
        max_length = step_mtu_df['bflh_l'].max()
        max_velocity = step_mtu_df['bflh_l_vel'].max()
        avg_velocity = step_mtu_df[step_mtu_df['bflh_l_vel'] > 0]['bflh_l_vel'].mean()
        
        # Store results
        left_bflh_l_max_lengths.append(max_length)
        left_bflh_l_max_velocities.append(max_velocity)
        left_bflh_l_avg_velocities.append(avg_velocity)
        left_step_start_times.append(takeoff_time)
        left_step_end_times.append(touchdown_time)

# Process RIGHT steps
for i in range(0, len(right_step_times_df) - 1):
    takeoff_time = right_step_times_df['time'].iloc[i]
    touchdown_time = right_step_times_df['time'].iloc[i + 1]
    
    # Extract step data
    step_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= takeoff_time) & 
        (mtu_lengths_df['time'] <= touchdown_time)
    ].reset_index(drop=True)
    
    if len(step_mtu_df) > 0:
        # Calculate velocity
        step_mtu_df['bflh_r_vel'] = np.gradient(step_mtu_df['bflh_r'], step_mtu_df['time'])
        
        # Find max values
        max_length = step_mtu_df['bflh_r'].max()
        max_velocity = step_mtu_df['bflh_r_vel'].max()

        # Find the average lengthening velocity, implement a boolean mask to select only the positive velocity values
        avg_velocity = step_mtu_df[step_mtu_df['bflh_r_vel'] > 0]['bflh_r_vel'].mean()
        
        # Store results
        right_bflh_r_max_lengths.append(max_length)
        right_bflh_r_max_velocities.append(max_velocity)
        right_bflh_r_avg_velocities.append(avg_velocity)
        right_step_start_times.append(takeoff_time)
        right_step_end_times.append(touchdown_time)

# Create output dataframes
left_output_df = pd.DataFrame({
    'step_start_time': left_step_start_times,
    'step_end_time': left_step_end_times,
    'left_bflh_max_length': left_bflh_l_max_lengths,
    'left_bflh_max_velocity': left_bflh_l_max_velocities,
    'left_bflh_avg_velocity': left_bflh_l_avg_velocities
})

right_output_df = pd.DataFrame({
    'step_start_time': right_step_start_times,
    'step_end_time': right_step_end_times,
    'right_bflh_max_length': right_bflh_r_max_lengths,
    'right_bflh_max_velocity': right_bflh_r_max_velocities,
    'right_bflh_avg_velocity': right_bflh_r_avg_velocities
})

# Save to CSV files
left_output_file = rf'{base_path}\bflh_mtu_max_left_steps_ID{subject}_{session}_{type}_LSTM_filtered.csv'
right_output_file = rf'{base_path}\bflh_mtu_max_right_steps_ID{subject}_{session}_{type}_LSTM_filtered.csv'

left_output_df.to_csv(left_output_file, index=False)
right_output_df.to_csv(right_output_file, index=False)

print(f"Processed {len(left_output_df)} left steps")
print(f"Processed {len(right_output_df)} right steps")
print(f"Saved left step data to {left_output_file}")
print(f"Saved right step data to {right_output_file}")

# Display summary statistics
print("\nLeft step Summary:")
print(left_output_df.describe())
print("\nRight step Summary:")
print(right_output_df.describe())

# Create visualization for all steps
fig, axes = plt.subplots(2, 3, figsize=(15, 10))

# Left max lengths
axes[0, 0].plot(range(len(left_bflh_l_max_lengths)), left_bflh_l_max_lengths, 'o-', color='blue')
axes[0, 0].set_xlabel('step Number')
axes[0, 0].set_ylabel('Max MTU Length (Normalized lengths)')
axes[0, 0].set_title('Left BFLH Max Lengths Across steps')
axes[0, 0].grid(True)

# Right max lengths
axes[0, 1].plot(range(len(right_bflh_r_max_lengths)), right_bflh_r_max_lengths, 'o-', color='red')
axes[0, 1].set_xlabel('step Number')
axes[0, 1].set_ylabel('Max MTU Length (Normalized Lengths)')
axes[0, 1].set_title('Right BFLH Max Lengths Across steps')
axes[0, 1].grid(True)

# Left max velocities
axes[1, 0].plot(range(len(left_bflh_l_max_velocities)), left_bflh_l_max_velocities, 'o-', color='blue')
axes[1, 0].set_xlabel('step Number')
axes[1, 0].set_ylabel('Max MTU Velocity (Normalized Lengths/s)')
axes[1, 0].set_title('Left BFLH Max Velocities Across steps')
axes[1, 0].grid(True)

# Right max velocities
axes[1, 1].plot(range(len(right_bflh_r_max_velocities)), right_bflh_r_max_velocities, 'o-', color='red')
axes[1, 1].set_xlabel('step Number')
axes[1, 1].set_ylabel('Max MTU Velocity (Normalized Lengths/s)')
axes[1, 1].set_title('Right BFLH Max Velocities Across steps')
axes[1, 1].grid(True)

# Left max velocities
axes[0, 2].plot(range(len(left_bflh_l_avg_velocities)), left_bflh_l_avg_velocities, 'o-', color='blue')
axes[0, 2].set_xlabel('step Number')
axes[0, 2].set_ylabel('Avg MTU Lengthening Velocity (Normalized Lengths/s)')
axes[0, 2].set_title('Left BFLH Avg Lengthening Velocities Across steps')
axes[0, 2].grid(True)

# Right max velocities
axes[1, 2].plot(range(len(right_bflh_r_avg_velocities)), right_bflh_r_avg_velocities, 'o-', color='red')
axes[1, 2].set_xlabel('step Number')
axes[1, 2].set_ylabel('Avg MTU LengtheningVelocity (Normalized Lengths/s)')
axes[1, 2].set_title('Right BFLH Avg LengtheningVelocities Across steps')
axes[1, 2].grid(True)


plt.tight_layout()
plt.savefig(r'G:\Shared drives\Stanford Football\February_23\subject10\CleanedKinematics\Outputs\bflh_mtu_all_steps_summary_ID10_S6_fly_LSTM_filtered.png')
plt.show()

print("\nPlot saved successfully!")

# ========== MODIFIED SECTION: Plot only last 3 steps ==========

# Create overlay plots for LAST 3 stepS ONLY with peak markers
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Generate colors for each step
from matplotlib import cm

# Get indices for last 3 steps
n_left_steps = len(left_bflh_l_max_lengths)
n_right_steps = len(right_bflh_r_max_lengths)

# Determine how many steps to plot (up to 3)
n_left_to_plot = min(3, n_left_steps) #changed from 6 to 3 for focus on closest 3 steps
n_right_to_plot = min(3, n_right_steps) #changed from 6 to 3 for focus on closest 3 steps

# Get indices of last 3 steps
left_step_indices = list(range(n_left_steps - n_left_to_plot, n_left_steps))
right_step_indices = list(range(n_right_steps - n_right_to_plot, n_right_steps))

# Generate colors for the steps we're plotting
left_colors = cm.rainbow(np.linspace(0, 1, n_left_to_plot))
right_colors = cm.rainbow(np.linspace(0, 1, n_right_to_plot))

# Define normalized x-axis (0 to 100%)
normalized_x = np.linspace(0, 100, 101)

# Plot LEFT BFLH LENGTHS (last 3 steps only)
for plot_idx, step_idx in enumerate(left_step_indices):
    start_time = left_step_start_times[step_idx]
    end_time = left_step_end_times[step_idx]
    
    step_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(step_mtu_df) > 0:
        # Create interpolation function
        step_percent = np.linspace(0, 100, len(step_mtu_df))
        interp_func = interp1d(step_percent, step_mtu_df['bflh_l'], 
                              kind='linear', fill_value='extrapolate')
        
        # Interpolate to normalized grid
        normalized_length = interp_func(normalized_x)
        
        # Plot the step
        step_number = n_left_steps - step_idx
        axes[0, 0].plot(normalized_x, normalized_length, 
                       color=left_colors[plot_idx], label=f'step {step_number}', linewidth=2)
        
        # Mark the peak
        max_idx = np.argmax(normalized_length)
        axes[0, 0].plot(normalized_x[max_idx], normalized_length[max_idx], 
                       'o', color=left_colors[plot_idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[0, 0].set_xlabel('step Cycle (%)', fontsize=18)
axes[0, 0].set_ylabel('MTU Length (Normalized Lengths)', fontsize=18)
axes[0, 0].set_title('Left BFLH Lengths - Last 2 steps Overlaid', fontsize=18, fontweight='bold')
axes[0, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=18)
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].set_xlim([0, 100])

# Plot RIGHT BFLH LENGTHS (last 3 steps only)
for plot_idx, step_idx in enumerate(right_step_indices):
    start_time = right_step_start_times[step_idx]
    end_time = right_step_end_times[step_idx]
    
    step_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(step_mtu_df) > 0:
        # Create interpolation function
        step_percent = np.linspace(0, 100, len(step_mtu_df))
        interp_func = interp1d(step_percent, step_mtu_df['bflh_r'], 
                              kind='linear', fill_value='extrapolate')
        
        # Interpolate to normalized grid
        normalized_length = interp_func(normalized_x)
        
        # Plot the step
        step_number = n_right_steps - step_idx
        axes[0, 1].plot(normalized_x, normalized_length, 
                       color=right_colors[plot_idx], label=f'step {step_number}', linewidth=2)
        
        # Mark the peak
        max_idx = np.argmax(normalized_length)
        axes[0, 1].plot(normalized_x[max_idx], normalized_length[max_idx], 
                       'o', color=right_colors[plot_idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[0, 1].set_xlabel('step Cycle (%)', fontsize=18)
axes[0, 1].set_ylabel('MTU Length (Normalized Lengths)', fontsize=18)
axes[0, 1].set_title('Right BFLH Lengths - Last 2 steps Overlaid', fontsize=18, fontweight='bold')
axes[0, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=18)
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].set_xlim([0, 100])

# Plot LEFT BFLH VELOCITIES (last 3 steps only)
for plot_idx, step_idx in enumerate(left_step_indices):
    start_time = left_step_start_times[step_idx]
    end_time = left_step_end_times[step_idx]
    
    step_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(step_mtu_df) > 0:
        # Calculate velocity
        step_mtu_df['bflh_l_vel'] = np.gradient(step_mtu_df['bflh_l'], step_mtu_df['time'])
        
        # Create interpolation function
        step_percent = np.linspace(0, 100, len(step_mtu_df))
        interp_func = interp1d(step_percent, step_mtu_df['bflh_l_vel'], 
                              kind='linear', fill_value='extrapolate')
        
        # Interpolate to normalized grid
        normalized_velocity = interp_func(normalized_x)
        
        # Plot the step
        step_number = n_left_steps - step_idx
        axes[1, 0].plot(normalized_x, normalized_velocity, 
                       color=left_colors[plot_idx], label=f'step {step_number}', linewidth=2)
        
        # Mark the peak
        max_idx = np.argmax(normalized_velocity)
        axes[1, 0].plot(normalized_x[max_idx], normalized_velocity[max_idx], 
                       'o', color=left_colors[plot_idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[1, 0].set_xlabel('step Cycle (%)', fontsize=18)
axes[1, 0].set_ylabel('MTU Velocity (Norm Lengths/s)', fontsize=18)
axes[1, 0].set_title('Left BFLH Velocities - Last 2 steps Overlaid', fontsize=18, fontweight='bold')
axes[1, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=18)
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].set_xlim([0, 100])


# Plot RIGHT BFLH VELOCITIES (last 3 steps only)
for plot_idx, step_idx in enumerate(right_step_indices):
    start_time = right_step_start_times[step_idx]
    end_time = right_step_end_times[step_idx]
    
    step_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(step_mtu_df) > 0:
        # Calculate velocity
        step_mtu_df['bflh_r_vel'] = np.gradient(step_mtu_df['bflh_r'], step_mtu_df['time'])
        
        # Create interpolation function
        step_percent = np.linspace(0, 100, len(step_mtu_df))
        interp_func = interp1d(step_percent, step_mtu_df['bflh_r_vel'], 
                              kind='linear', fill_value='extrapolate')
        
        # Interpolate to normalized grid
        normalized_velocity = interp_func(normalized_x)
        
        # Plot the step
        step_number = n_right_steps - step_idx
        axes[1, 1].plot(normalized_x, normalized_velocity, 
                       color=right_colors[plot_idx], label=f'step {step_number}', linewidth=2)
        
        # Mark the peak
        max_idx = np.argmax(normalized_velocity)
        axes[1, 1].plot(normalized_x[max_idx], normalized_velocity[max_idx], 
                       'o', color=right_colors[plot_idx], markersize=8, markeredgecolor='black', markeredgewidth=1.5)

axes[1, 1].set_xlabel('step Cycle (%)', fontsize=18)
axes[1, 1].set_ylabel('MTU Velocity (Norm Lengths/s)', fontsize=18)
axes[1, 1].set_title('Right BFLH Velocities - Last 2 steps Overlaid', fontsize=18, fontweight='bold')
axes[1, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=18)
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].set_xlim([0, 100])

plt.tight_layout()
plt.savefig(rf'{base_path}\bflh_mtu_last6_steps_overlay_ID{subject}_{session}_fly_LSTM.png', 
            dpi=300, bbox_inches='tight')
plt.show()

print("\nOverlay plot saved successfully!")
print(f"Plotted last {n_left_to_plot} left steps and last {n_right_to_plot} right steps")