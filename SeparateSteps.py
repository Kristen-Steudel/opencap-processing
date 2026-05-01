import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import spectrogram

# Requirements to Change for each run
#########################################################################
subject_num = 5
date = 'March_2'
session_num = '7'
type = 'sprint'
filt_freq = 10  # Hz, was 15 Hz
##########################################################################

# %% Load data
# This folder is for non-cleaned data
# data_folder = rf'G:\Shared drives\Stanford Football\{date}\subject{subject_num}\Kinematics\Outputs\shank_angular_velocity_ID{subject_num}_S{session_num}_{type}_LSTM_filtered_{filt_freq}Hz.csv'
# This folder is for cleaned data shank_angular_velocity_ID10_S6_fly_LSTM_filtered_10Hz_filtered_10Hz
#data_folder = rf'G:\Shared drives\Stanford Football\{date}\subject{subject_num}\CleanedKinematics\filtered_post_augmentation\Outputs\shank_angular_velocity_ID{subject_num}_S{session_num}_{type}_LSTM_filtered_{filt_freq}Hz_filtered_{filt_freq}Hz.csv'

# Data folder for general trials
#data_folder = rf'G:\Shared drives\Stanford Football\{date}\subject{subject_num}\CleanedKinematics\filtered_post_augmentation\Outputs\shank_angular_velocity_ID{subject_num}_S{session_num}_{type}_LSTM_filtpostaug15Hz_filteredkinematics_15Hz_filtered_15Hz.csv'

# Data folder for analysis compare trials
data_folder = rf'G:\Shared drives\Stanford Football\AnalysisCompare\SplinedKinematics\SplinedKinematicsKnot80\Outputs\shank_angular_velocity_sprint_spline_ik_solution_knot80_filtered_10Hz.csv'

# Load csv file as dataframe
df = pd.read_csv(data_folder)

# %% Find negative-going zero crossings
def find_negative_zero_crossings(time, signal_data):
    """
    Find the times where the signal crosses zero from positive to negative.
    
    Parameters:
    -----------
    time : array
        Time vector
    signal_data : array
        Signal values
    
    Returns:
    --------
    crossing_times : array
        Times of negative-going zero crossings
    crossing_indices : array
        Indices of negative-going zero crossings
    """
    crossing_times = []
    crossing_indices = []
    
    for i in range(len(signal_data) - 1):
        # Check if crossing from positive to negative (negative-going)
        if signal_data[i] > 0 and signal_data[i + 1] <= 0:
            # Linear interpolation to find exact crossing time
            # y = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
            # Solve for x when y = 0
            t0, t1 = time[i], time[i + 1]
            v0, v1 = signal_data[i], signal_data[i + 1]
            
            # Interpolated crossing time
            if v1 != v0:  # Avoid division by zero
                crossing_time = t0 - v0 * (t1 - t0) / (v1 - v0)
            else:
                crossing_time = t0
            
            crossing_times.append(crossing_time)
            crossing_indices.append(i)
    
    return np.array(crossing_times), np.array(crossing_indices)

# Find negative-going zero crossings for both shanks (sagittal plane = y-axis)
left_crossing_times, left_crossing_indices = find_negative_zero_crossings(
    df['time'].values, df['tibia_l_z'].values
)
right_crossing_times, right_crossing_indices = find_negative_zero_crossings(
    df['time'].values, df['tibia_r_z'].values
)

print(f"Found {len(left_crossing_times)} negative-going zero crossings for left shank")
print(f"Found {len(right_crossing_times)} negative-going zero crossings for right shank")

# %% Combine and sort all step times
all_step_times = np.concatenate([left_crossing_times, right_crossing_times])
all_step_sides = ['left'] * len(left_crossing_times) + ['right'] * len(right_crossing_times)

# Sort by time
sort_indices = np.argsort(all_step_times)
all_step_times_sorted = all_step_times[sort_indices]
all_step_sides_sorted = [all_step_sides[i] for i in sort_indices]

# Create dataframe
step_times_df = pd.DataFrame({
    'time': all_step_times_sorted,
    'side': all_step_sides_sorted
})

# Also create separate dataframes for left and right
left_step_times_df = pd.DataFrame({
    'time': left_crossing_times,
    'side': 'left'
})

right_step_times_df = pd.DataFrame({
    'time': right_crossing_times,
    'side': 'right'
})

# %% Save to CSV
output_dir = os.path.dirname(data_folder)
output_path = os.path.join(output_dir, 'step_times.csv')
output_path_left = os.path.join(output_dir, 'step_times_left.csv')
output_path_right = os.path.join(output_dir, 'step_times_right.csv')

step_times_df.to_csv(output_path, index=False)
left_step_times_df.to_csv(output_path_left, index=False)
right_step_times_df.to_csv(output_path_right, index=False)

print(f"\nstep times saved to:")
print(f"  All: {output_path}")
print(f"  Left: {output_path_left}")
print(f"  Right: {output_path_right}")

# %% Plot the angular velocity with zero crossings marked
plt.figure(figsize=(14, 8))

# Plot signals
plt.plot(df['time'], df['tibia_l_z'], label='Left Shank Z', linewidth=2)
plt.plot(df['time'], df['tibia_r_z'], label='Right Shank Z', linewidth=2)

# Mark zero crossings
plt.scatter(left_crossing_times, np.zeros_like(left_crossing_times), 
            color='blue', s=100, marker='v', zorder=5, 
            label=f'Left zero crossings (n={len(left_crossing_times)})')
plt.scatter(right_crossing_times, np.zeros_like(right_crossing_times), 
            color='orange', s=100, marker='^', zorder=5, 
            label=f'Right zero crossings (n={len(right_crossing_times)})')

# Add zero line
plt.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.5)

plt.xlabel('Time (s)', fontsize=12)
plt.ylabel('Angular Velocity (rad/s)', fontsize=12)
plt.title('Shank Sagittal Plane Angular Velocity with Negative-Going Zero Crossings', fontsize=14)
plt.legend(fontsize=10)
plt.grid(alpha=0.3)
plt.tight_layout()

# Save plot
plot_path = os.path.join(output_dir, 'step_times_visualization.png')
plt.savefig(plot_path, dpi=300)
print(f"\nPlot saved to: {plot_path}")
plt.show()

# %% Print summary statistics
print("\n" + "="*60)
print("step DETECTION SUMMARY")
print("="*60)
print(f"Left shank steps:  {len(left_crossing_times)}")
print(f"Right shank steps: {len(right_crossing_times)}")
print(f"Total steps:       {len(all_step_times_sorted)}")
print("\nFirst 5 step times (combined):")
print(step_times_df.head())
if len(step_times_df) > 1:
    step_intervals = np.diff(all_step_times_sorted)
    print(f"\nMean step interval: {np.mean(step_intervals):.3f} s")
    print(f"Std step interval:  {np.std(step_intervals):.3f} s")
print("="*60)

fs = 120
x =  df['tibia_l_z']
t_x = df['time']

N = len(x)

f, t, Sxx = spectrogram(x, fs, nperseg = 90)
plt.pcolormesh(t, f, Sxx, shading='gouraud')
plt.ylabel('Frequency [Hz]')
plt.ylim([0, 10])
plt.xlabel('Time [sec]')
plt.show()