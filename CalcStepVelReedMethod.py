# Determine the speed of running of each stride using the pelvis x direction velocity - assume this is in the direction of running. Then, determine the average speed of each stride and filter out strides that are above or below a certain threshold. This is to remove strides where the subject was not running at a consistent speed, which may indicate that they were not running at all (e.g., walking, standing still, etc.).
# This assumption may need to be adjusted/revisited later depending on how well it performs.

# Using Reed's methods: low-pass filter the pelvis translation signal with a 2-Hz cutoff frequency
# Divide the pelvis displacement during the step along the running direction by the step time. 


import numpy as np
import opensim as osim
import pandas as pd
from scipy.signal import butter, filtfilt
import matplotlib.pyplot as plt
from pathlib import Path

def butter_lowpass_filter(data, cutoff=2, fs=1000, order=4):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = filtfilt(b, a, data)
    return y

def calculate_stride_velocities(pelvis_x_filtered, time, stride_times_df):
    """
    Calculate velocity for each stride using Reed's method:
    velocity = displacement / time
    
    Parameters:
    -----------
    pelvis_x_filtered : array
        Filtered pelvis position data
    time : array
        Time vector from motion data
    stride_times_df : DataFrame
        DataFrame with 'start_time' and 'end_time' columns for each stride
    
    Returns:
    --------
    stride_data : list of dicts
        List containing velocity data for each stride
    """
    stride_data = []
    
    for idx, row in stride_times_df.iterrows():
        start_time = row['start_time']
        end_time = row['end_time']
        
        # Find indices corresponding to stride times
        start_idx = np.argmin(np.abs(time - start_time))
        end_idx = np.argmin(np.abs(time - end_time))
        
        # Extract stride duration and position data
        stride_time = end_time - start_time
        stride_displacement = pelvis_x_filtered[end_idx] - pelvis_x_filtered[start_idx]
        
        # Calculate average velocity for this stride (Reed's method)
        avg_velocity = stride_displacement / stride_time
        
        # Get time series data for this stride
        stride_time_vector = time[start_idx:end_idx+1]
        stride_position = pelvis_x_filtered[start_idx:end_idx+1]
        
        # Calculate instantaneous velocity using gradient
        stride_velocity = np.gradient(stride_position, stride_time_vector)
        
        stride_data.append({
            'stride_number': idx,
            'start_time': start_time,
            'end_time': end_time,
            'stride_duration': stride_time,
            'displacement': stride_displacement,
            'avg_velocity': avg_velocity,
            'time': stride_time_vector - start_time,  # Normalize to start at 0
            'position': stride_position,
            'velocity': stride_velocity
        })
    
    return stride_data

def save_stride_velocities(stride_data, output_dir):
    """
    Save velocity data for each stride to separate CSV files
    
    Parameters:
    -----------
    stride_data : list of dicts
        Output from calculate_stride_velocities
    output_dir : str or Path
        Directory to save CSV files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save summary data
    summary_data = []
    
    for stride in stride_data:
        # Save detailed time series for each stride
        stride_df = pd.DataFrame({
            'time': stride['time'],
            'position': stride['position'],
            'velocity': stride['velocity']
        })
        
        filename = output_path / f"stride_{stride['stride_number']:03d}_velocity.csv"
        stride_df.to_csv(filename, index=False)
        
        # Collect summary data
        summary_data.append({
            'stride_number': stride['stride_number'],
            'start_time': stride['start_time'],
            'end_time': stride['end_time'],
            'stride_duration': stride['stride_duration'],
            'displacement': stride['displacement'],
            'avg_velocity': stride['avg_velocity'],
            'max_velocity': np.max(stride['velocity']),
            'min_velocity': np.min(stride['velocity']),
            'std_velocity': np.std(stride['velocity'])
        })
    
    # Save summary file
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(output_path / 'stride_velocity_summary.csv', index=False)
    
    return summary_df

def filter_strides_by_speed(summary_df, min_speed=None, max_speed=None, std_threshold=None):
    """
    Filter out strides based on speed criteria
    
    Parameters:
    -----------
    summary_df : DataFrame
        Summary data from save_stride_velocities
    min_speed : float, optional
        Minimum average velocity threshold (m/s)
    max_speed : float, optional
        Maximum average velocity threshold (m/s)
    std_threshold : float, optional
        Maximum standard deviation of velocity (to detect inconsistent speeds)
    
    Returns:
    --------
    filtered_df : DataFrame
        Filtered stride data
    """
    mask = np.ones(len(summary_df), dtype=bool)
    
    if min_speed is not None:
        mask &= summary_df['avg_velocity'] >= min_speed
    
    if max_speed is not None:
        mask &= summary_df['avg_velocity'] <= max_speed
    
    if std_threshold is not None:
        mask &= summary_df['std_velocity'] <= std_threshold
    
    filtered_df = summary_df[mask].copy()
    
    print(f"Filtered {len(summary_df) - len(filtered_df)} strides out of {len(summary_df)}")
    print(f"Remaining strides: {len(filtered_df)}")
    
    return filtered_df

# Main execution
date = 'February_9'
subject_id = 'subject2'

data_dir = f'G:\\Shared drives\\Stanford Football'
date_dir = f'{data_dir}\\{date}'
subject_dir = f'{date_dir}\\{subject_id}'

stride_times = f'{subject_dir}\\Kinematics\\Outputs\\stride_times.csv'
kinematics_file = f'{subject_dir}\\OpenSimData\\OpenPose_default\\3-cameras\\Kinematics\\ID2_S5_decel_LSTM_filtered.mot'

# Load data
times_frame = pd.read_csv(stride_times)
mot_table = osim.TimeSeriesTable(kinematics_file)

# Get pelvis data
pelvis_x = mot_table.getDependentColumn('pelvis_tx').to_numpy()
time = mot_table.getIndependentColumn()

# Determine sampling frequency from data
dt = np.mean(np.diff(time))
fs = 1 / dt
print(f"Detected sampling frequency: {fs:.2f} Hz")

# Filter pelvis position
pelvis_x_filtered = butter_lowpass_filter(pelvis_x, cutoff=2, fs=fs, order=4)

# Calculate velocities for each stride
stride_data = calculate_stride_velocities(pelvis_x_filtered, time, times_frame)

# Save stride velocities
output_dir = f'{subject_dir}\\Kinematics\\Outputs\\stride_velocities'
summary_df = save_stride_velocities(stride_data, output_dir)

# Filter strides (adjust thresholds as needed)
# Example: keep strides with avg velocity between 3-8 m/s and std < 1 m/s
filtered_summary = filter_strides_by_speed(
    summary_df, 
    min_speed=3.0,  # Adjust based on your data
    max_speed=8.0,  # Adjust based on your data
    std_threshold=1.0  # Adjust based on your data
)

# Save filtered summary
filtered_summary.to_csv(f'{output_dir}/stride_velocity_summary_filtered.csv', index=False)

# Visualization
plt.figure(figsize=(12, 8))

# Plot 1: Position
plt.subplot(3, 1, 1)
plt.plot(time, pelvis_x, alpha=0.5, label='Original')
plt.plot(time, pelvis_x_filtered, label='Filtered', linewidth=2)
for _, row in times_frame.iterrows():
    plt.axvline(row['start_time'], color='g', alpha=0.3, linestyle='--')
    plt.axvline(row['end_time'], color='r', alpha=0.3, linestyle='--')
plt.xlabel('Time (s)')
plt.ylabel('Position (m)')
plt.title('Pelvis X Position')
plt.legend()
plt.grid(True)

# Plot 2: Velocity
plt.subplot(3, 1, 2)
pelvis_x_velocity = np.gradient(pelvis_x_filtered, time)
plt.plot(time, pelvis_x_velocity)
for _, row in times_frame.iterrows():
    plt.axvline(row['start_time'], color='g', alpha=0.3, linestyle='--')
    plt.axvline(row['end_time'], color='r', alpha=0.3, linestyle='--')
plt.xlabel('Time (s)')
plt.ylabel('Velocity (m/s)')
plt.title('Pelvis X Velocity')
plt.grid(True)

# Plot 3: Average velocity per stride
plt.subplot(3, 1, 3)
stride_numbers = summary_df['stride_number']
avg_velocities = summary_df['avg_velocity']
colors = ['green' if idx in filtered_summary['stride_number'].values else 'red' 
          for idx in stride_numbers]
plt.bar(stride_numbers, avg_velocities, color=colors, alpha=0.6)
plt.xlabel('Stride Number')
plt.ylabel('Average Velocity (m/s)')
plt.title('Average Velocity per Stride (Green=Kept, Red=Filtered)')
plt.grid(True, axis='y')

plt.tight_layout()
plt.savefig(f'{output_dir}/velocity_analysis.png', dpi=300)
plt.show()

print(f"\nVelocity data saved to: {output_dir}")
print(f"Summary statistics:\n{filtered_summary.describe()}")