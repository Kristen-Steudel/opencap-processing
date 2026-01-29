import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import spectrogram

subject_num = 9
# %% Load data
data_folder = rf'G:\Shared drives\Stanford Football\January_26\subject{subject_num}\Kinematics\Outputs\shank_angular_velocity_ID{subject_num}_S3_fly_LSTM.csv'

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

# %% Combine and sort all stride times
all_stride_times = np.concatenate([left_crossing_times, right_crossing_times])
all_stride_sides = ['left'] * len(left_crossing_times) + ['right'] * len(right_crossing_times)

# Sort by time
sort_indices = np.argsort(all_stride_times)
all_stride_times_sorted = all_stride_times[sort_indices]
all_stride_sides_sorted = [all_stride_sides[i] for i in sort_indices]

# Create dataframe
stride_times_df = pd.DataFrame({
    'time': all_stride_times_sorted,
    'side': all_stride_sides_sorted
})

# Also create separate dataframes for left and right
left_stride_times_df = pd.DataFrame({
    'time': left_crossing_times,
    'side': 'left'
})

right_stride_times_df = pd.DataFrame({
    'time': right_crossing_times,
    'side': 'right'
})

# %% Save to CSV
output_dir = os.path.dirname(data_folder)
output_path = os.path.join(output_dir, 'stride_times.csv')
output_path_left = os.path.join(output_dir, 'stride_times_left.csv')
output_path_right = os.path.join(output_dir, 'stride_times_right.csv')

stride_times_df.to_csv(output_path, index=False)
left_stride_times_df.to_csv(output_path_left, index=False)
right_stride_times_df.to_csv(output_path_right, index=False)

print(f"\nStride times saved to:")
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
plot_path = os.path.join(output_dir, 'stride_times_visualization.png')
plt.savefig(plot_path, dpi=300)
print(f"\nPlot saved to: {plot_path}")
plt.show()

# %% Print summary statistics
print("\n" + "="*60)
print("STRIDE DETECTION SUMMARY")
print("="*60)
print(f"Left shank strides:  {len(left_crossing_times)}")
print(f"Right shank strides: {len(right_crossing_times)}")
print(f"Total strides:       {len(all_stride_times_sorted)}")
print("\nFirst 5 stride times (combined):")
print(stride_times_df.head())
if len(stride_times_df) > 1:
    stride_intervals = np.diff(all_stride_times_sorted)
    print(f"\nMean stride interval: {np.mean(stride_intervals):.3f} s")
    print(f"Std stride interval:  {np.std(stride_intervals):.3f} s")
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