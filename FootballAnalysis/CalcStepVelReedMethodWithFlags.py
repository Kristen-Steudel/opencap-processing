import numpy as np
import opensim as osim
import pandas as pd
from scipy.signal import butter, filtfilt
import matplotlib.pyplot as plt
from pathlib import Path

# Configuration imported from pipeline_config.py (edit once, used by all scripts)
# import pipeline_config as cfg
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pipeline_config as cfg
paths = cfg.PATHS
subject_dir = paths['subject_dir']
dist_threshold = cfg.DIST_THRESHOLD
step_times = paths['step_times_csv']
kinematics_file = paths['kinematics_file_reed']


def butter_lowpass_filter(data, cutoff=2, fs=1000, order=4):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = filtfilt(b, a, data)
    return y

def calculate_stride_velocities(pelvis_x_filtered, time, step_times_df):
    """
    Calculate velocity for each stride using Reed's method:
    velocity = displacement / time
    
    Parameters:
    -----------
    pelvis_x_filtered : array
        Filtered pelvis position data
    time : array
        Time vector from motion data
    step_times_df : DataFrame
        DataFrame with 'start_time' and 'end_time' columns for each stride
    
    Returns:
    --------
    stride_data : list of dicts
        List containing velocity data for each stride
    """
    stride_data = []
    total_strides = len(step_times_df) - 1
    
    for idx in range(total_strides):
        start_time = step_times_df.iloc[idx]['time']
        end_time = step_times_df.iloc[idx + 1]['time']
        start_side = step_times_df.iloc[idx]['side']
        end_side = step_times_df.iloc[idx + 1]['side']

        start_idx = np.argmin(np.abs(time - start_time))
        end_idx = np.argmin(np.abs(time - end_time))
        
        # Safety check: ensure we have at least 2 data points
        # This handles cases where consecutive stride markers are very close together
        if end_idx <= start_idx:
            end_idx = start_idx + 1
        
        # Extract stride duration and position data
        stride_time = end_time - start_time
        stride_displacement = pelvis_x_filtered[end_idx] - pelvis_x_filtered[start_idx]
        
        # Calculate average velocity for this stride (Reed's method)
        # Note: displacement will be negative since running from -15m to 0m
        # Velocity magnitude is what matters for speed
        avg_velocity = stride_displacement / stride_time
        
        # Get time series data for this stride
        stride_time_vector = time[start_idx:end_idx+1]
        stride_position = pelvis_x_filtered[start_idx:end_idx+1]
        
        # Calculate instantaneous velocity using gradient
        if len(stride_time_vector) > 1:
            stride_velocity = np.gradient(stride_position, stride_time_vector)
        else:
            # If only 1 point, set velocity to 0
            stride_velocity = np.array([0.0])
        
        # Calculate average position for this stride (for quality assessment)
        avg_position = np.mean(stride_position)

        # stride number counting up from the 0 mark
        stride_number = total_strides - idx 
        
        stride_data.append({
            'stride_number': stride_number, #idx, 
            'start_time': start_time,
            'end_time': end_time,
            'start_side': start_side,
            'end_side': end_side,
            'stride_duration': stride_time,
            'displacement': stride_displacement,
            'avg_velocity': avg_velocity,
            'avg_position': avg_position,
            'start_position': pelvis_x_filtered[start_idx],
            'end_position': pelvis_x_filtered[end_idx],
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
            'avg_position': stride['avg_position'],
            'start_position': stride['start_position'],
            'end_position': stride['end_position'],
            'max_velocity': np.max(stride['velocity']),
            'min_velocity': np.min(stride['velocity']),
            'std_velocity': np.std(stride['velocity'])
        })
    
    # Save summary file
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(output_path / 'stride_velocity_summary.csv', index=False)
    
    return summary_df

def filter_strides_by_quality(summary_df, stride_data, method='position', n_strides=None, 
                               min_speed=None, max_speed=None, position_threshold=dist_threshold):
    """
    Filter strides based on capture volume proximity and speed consistency
    
    For my data: subject runs from -15m to 0m, trust strides beyond -{dist_threshold}m (i.e., -{dist_threshold}m to 0m)
    
    Parameters:
    -----------
    summary_df : DataFrame
        Summary data from save_stride_velocities
    stride_data : list of dicts
        Full stride data including position information
    method : str
        'last_n': Keep only the last n strides (closest to capture volume)
        'position': Filter by position threshold (strides closer to 0m)
        'speed': Filter by speed range
        'combined': Use multiple criteria

        I want the position threshold for deceleration data because
        it's okay if the speed is slow

        I wmay want a speed threshold for acceleration or 100% max speed data

    n_strides : int, optional
        Number of last strides to keep (for 'last_n' method)
    min_speed : float, optional
        Minimum average velocity magnitude threshold (m/s)
    max_speed : float, optional
        Maximum average velocity magnitude threshold (m/s)
    position_threshold : float, optional
        Minimum pelvis_x position (default -{dist_threshold}m, keeps strides from -{dist_threshold}m to 0m)
    
    Returns:
    --------
    filtered_df : DataFrame
        Filtered stride data
    valid_stride_numbers : list
        List of valid stride numbers to use
    """
    mask = np.ones(len(summary_df), dtype=bool)
    
    # Method 1: Keep only last n strides (most reliable near capture volume)
    if method == 'last_n' and n_strides is not None:
        total_strides = len(summary_df)
        stride_numbers_to_keep = summary_df['stride_number'].iloc[-n_strides:].values
        mask = summary_df['stride_number'].isin(stride_numbers_to_keep)
        print(f"Keeping last {n_strides} strides (closest to capture volume, positions closer to 0m)")
    
    # Method 2: Filter by position (keep strides with avg_position > threshold, i.e., closer to 0)
    elif method == 'position' and position_threshold is not None:
        # Keep strides where average position is GREATER than threshold
        # (e.g., -5m is > -8m, so it's kept; -10m is < -8m, so it's filtered) if dist_threshold is -8m
        mask = summary_df['avg_position'] > position_threshold
        print(f"Filtering: keeping strides with avg_position > {position_threshold}m (closer to capture volume)")
    
    # Method 3: Combined approach (position + speed)
    elif method == 'combined':
        # Start with position-based filtering
        if position_threshold is not None:
            mask = summary_df['avg_position'] > position_threshold
        
        # Then apply speed filters to remaining strides
        # Use absolute value of velocity since running in negative x direction
        if min_speed is not None:
            mask &= np.abs(summary_df['avg_velocity']) >= min_speed
        
        if max_speed is not None:
            mask &= np.abs(summary_df['avg_velocity']) <= max_speed
        
        print(f"Combined filtering: position > {position_threshold}m, speed range applied")
    
    # Method 4: Speed-only filtering
    else:
        # Use absolute value of velocity since running in negative x direction
        if min_speed is not None:
            mask &= np.abs(summary_df['avg_velocity']) >= min_speed
        
        if max_speed is not None:
            mask &= np.abs(summary_df['avg_velocity']) <= max_speed
        
        print(f"Speed-only filtering applied")
    
    filtered_df = summary_df[mask].copy()
    valid_stride_numbers = filtered_df['stride_number'].tolist()
    
    print(f"Filtered out {len(summary_df) - len(filtered_df)} strides")
    print(f"Remaining strides: {len(filtered_df)}")
    print(f"Valid stride numbers: {valid_stride_numbers}")
    
    return filtered_df, valid_stride_numbers

def visualize_stride_quality(time, pelvis_x_filtered, times_frame, summary_df, 
                             valid_stride_numbers, output_dir, position_threshold=dist_threshold):
    """
    Visualize which strides are kept vs filtered based on capture volume proximity
    """
    plt.figure(figsize=(14, 12))
    
    # Plot 1: Position with stride markers
    plt.subplot(4, 1, 1)
    plt.plot(time, pelvis_x_filtered, label='Filtered Position', linewidth=2, color='blue')
    plt.axhline(y=position_threshold, color='orange', linestyle='--', linewidth=2, 
                label=f'Position Threshold ({position_threshold}m)')
    
    for idx in range(len(times_frame) - 1):
        start_time = times_frame.iloc[idx]['time']
        end_time = times_frame.iloc[idx + 1]['time']
        color = 'green' if idx in valid_stride_numbers else 'red'
        alpha = 0.3 if idx in valid_stride_numbers else 0.15
        plt.axvspan(start_time, end_time, color=color, alpha=alpha)
    
    plt.xlabel('Time (s)')
    plt.ylabel('Position (m)')
    plt.title('Pelvis X Position Over Time\n(Green=Valid Strides in Capture Volume, Red=Filtered Out)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot 2: Velocity over time
    plt.subplot(4, 1, 2)
    pelvis_x_velocity = np.gradient(pelvis_x_filtered, time)
    plt.plot(time, pelvis_x_velocity, color='blue')
    
    for idx in range(len(times_frame) - 1):
        start_time = times_frame.iloc[idx]['time']
        end_time = times_frame.iloc[idx + 1]['time']
        color = 'green' if idx in valid_stride_numbers else 'red'
        alpha = 0.3 if idx in valid_stride_numbers else 0.15
        plt.axvspan(start_time, end_time, color=color, alpha=alpha)
    
    plt.xlabel('Time (s)')
    plt.ylabel('Velocity (m/s)')
    plt.title('Pelvis X Velocity Over Time')
    plt.grid(True, alpha=0.3)
    
    # Plot 3: Average velocity per stride (absolute value for speed)
    plt.subplot(4, 1, 3)
    stride_numbers = summary_df['stride_number']
    avg_velocities = np.abs(summary_df['avg_velocity'])  # Absolute value for speed
    colors = ['green' if idx in valid_stride_numbers else 'red' for idx in stride_numbers]
    plt.bar(stride_numbers, avg_velocities, color=colors, alpha=0.6, edgecolor='black')
    plt.xlabel('Stride Number')
    plt.ylabel('Average Speed (m/s)')
    plt.title('Average Speed per Stride (Green=Valid, Red=Filtered)')
    plt.grid(True, axis='y', alpha=0.3)
    
    # Plot 4: Average position per stride (shows progression toward capture volume)
    plt.subplot(4, 1, 4)
    avg_positions = summary_df['avg_position']
    colors = ['green' if idx in valid_stride_numbers else 'red' for idx in stride_numbers]
    plt.bar(stride_numbers, avg_positions, color=colors, alpha=0.6, edgecolor='black')
    plt.axhline(y=position_threshold, color='orange', linestyle='--', linewidth=2, 
                label=f'Threshold ({position_threshold}m)')
    plt.xlabel('Stride Number')
    plt.ylabel('Average Position (m)')
    plt.title('Average Position per Stride\n(Lower stride values = closer to capture volume at 0m)')
    plt.legend()
    plt.grid(True, axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/stride_quality_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

# ===== MAIN EXECUTION =====

# Load data
print("Loading data...")
times_frame = pd.read_csv(step_times)
mot_table = osim.TimeSeriesTable(kinematics_file)

# Check metadata
print("\nOriginal file metadata:")
keys = mot_table.getTableMetaDataKeys()
for key in keys:
    print(f"  {key}: {mot_table.getTableMetaDataString(key)}")

column_labels = mot_table.getColumnLabels()
print("\nColumn Labels:", list(column_labels))

# Get pelvis data
pelvis_x = mot_table.getDependentColumn('pelvis_tx').to_numpy()
time = mot_table.getIndependentColumn()

# Determine sampling frequency from data
dt = np.mean(np.diff(time))
fs = 1 / dt
print(f"\nDetected sampling frequency: {fs:.2f} Hz")

# Filter pelvis position with 2 Hz cutoff (Reed's method)
print("Applying low-pass filter (2 Hz cutoff)...")
pelvis_x_filtered = butter_lowpass_filter(pelvis_x, cutoff=2, fs=fs, order=4)

# Calculate velocities for each stride
print("\nCalculating stride velocities...")
stride_data = calculate_stride_velocities(pelvis_x_filtered, time, times_frame)

# Save stride velocities
output_dir = paths['stride_vel_output_dir']
print(f"\nSaving stride velocity data to: {output_dir}")
summary_df = save_stride_velocities(stride_data, output_dir)

# Display position range for all strides
print(f"\nPosition range across all strides:")
print(f"  Minimum position: {summary_df['avg_position'].min():.2f} m")
print(f"  Maximum position: {summary_df['avg_position'].max():.2f} m")
print(f"  First stride avg position: {summary_df['avg_position'].iloc[0]:.2f} m")
print(f"  Last stride avg position: {summary_df['avg_position'].iloc[-1]:.2f} m")

# ===== FILTERING OPTIONS =====

# RECOMMENDED: Filter by position threshold (keep strides beyond -{dist_threshold}m, i.e., closer to 0m)
print("\n" + "="*60)
print("FILTERING STRIDES")
print("="*60)

filtered_summary, valid_stride_numbers = filter_strides_by_quality(
    summary_df, 
    stride_data,
    method='position',
    position_threshold=dist_threshold  # Keep strides with avg_position > {dist_threshold}m (closer to capture volume)
)

# Alternative Option 1: Keep only last N strides
# filtered_summary, valid_stride_numbers = filter_strides_by_quality(
#     summary_df, 
#     stride_data,
#     method='last_n',
#     n_strides=10  # Adjust based on how many good strides you have
# )

# Alternative Option 2: Combined approach (position + speed)
# filtered_summary, valid_stride_numbers = filter_strides_by_quality(
#     summary_df, 
#     stride_data,
#     method='combined',
#     position_threshold=dist_threshold,
#     min_speed=3.0,  # Minimum running speed
#     max_speed=8.0   # Maximum running speed
# )

# Save filtered summary
filtered_summary.to_csv(f'{output_dir}/stride_velocity_summary_filtered.csv', index=False)
print(f"\nFiltered summary saved to: {output_dir}/stride_velocity_summary_filtered.csv")

# Create detailed visualization
print("\nGenerating visualizations...")
visualize_stride_quality(time, pelvis_x_filtered, times_frame, summary_df, 
                         valid_stride_numbers, output_dir, position_threshold=dist_threshold)

# Print statistics for valid strides only
print(f"\n{'='*60}")
print(f"VALID STRIDES SUMMARY (n={len(filtered_summary)})")
print(f"{'='*60}")
print("\nDetailed stride information:")
print(filtered_summary[['stride_number', 'avg_position', 'avg_velocity', 'stride_duration']].to_string())

print(f"\nSpeed statistics (absolute values):")
speed_stats = np.abs(filtered_summary['avg_velocity']).describe()
print(speed_stats)

print(f"\nPosition statistics:")
position_stats = filtered_summary['avg_position'].describe()
print(position_stats)

# Optional: Create additional summary plots for valid strides only
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# Plot 1: Speed distribution
axes[0, 0].hist(np.abs(filtered_summary['avg_velocity']), bins=15, color='green', alpha=0.7, edgecolor='black')
axes[0, 0].set_xlabel('Speed (m/s)')
axes[0, 0].set_ylabel('Frequency')
axes[0, 0].set_title('Distribution of Valid Stride Speeds')
axes[0, 0].grid(True, alpha=0.3)

# Plot 2: Stride duration distribution
axes[0, 1].hist(filtered_summary['stride_duration'], bins=15, color='blue', alpha=0.7, edgecolor='black')
axes[0, 1].set_xlabel('Stride Duration (s)')
axes[0, 1].set_ylabel('Frequency')
axes[0, 1].set_title('Distribution of Valid Stride Durations')
axes[0, 1].grid(True, alpha=0.3)

# Plot 3: Speed vs stride number (check for consistency)
axes[1, 0].plot(filtered_summary['stride_number'], np.abs(filtered_summary['avg_velocity']), 
                'o-', color='green', markersize=8, linewidth=2)
axes[1, 0].set_xlabel('Stride Number')
axes[1, 0].set_ylabel('Speed (m/s)')
axes[1, 0].set_title('Speed Across Valid Strides')
axes[1, 0].grid(True, alpha=0.3)

# Plot 4: Position vs stride number (shows progression)
axes[1, 1].plot(filtered_summary['stride_number'], filtered_summary['avg_position'], 
                'o-', color='orange', markersize=8, linewidth=2)
axes[1, 1].axhline(y=dist_threshold, color='red', linestyle='--', linewidth=2, label=f'Threshold ({dist_threshold}m)')
axes[1, 1].set_xlabel('Stride Number')
axes[1, 1].set_ylabel('Average Position (m)')
axes[1, 1].set_title('Position Across Valid Strides')
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(f'{output_dir}/valid_strides_summary.png', dpi=300, bbox_inches='tight')
plt.show()

# Optional: Delete CSV files for filtered-out strides (uncomment if desired)
print("\nCleaning up filtered stride files...")
for stride_num in summary_df['stride_number']:
    if stride_num not in valid_stride_numbers:
        file_to_remove = Path(output_dir) / f"stride_{stride_num:03d}_velocity.csv"
        if file_to_remove.exists():
            file_to_remove.unlink()
            print(f"  Removed: stride_{stride_num:03d}_velocity.csv")

print(f"\n{'='*60}")
print("ANALYSIS COMPLETE")
print(f"{'='*60}")
print(f"Total strides analyzed: {len(summary_df)}")
print(f"Valid strides kept: {len(filtered_summary)}")
print(f"Strides filtered out: {len(summary_df) - len(filtered_summary)}")
print(f"\nValid stride numbers: {valid_stride_numbers}")
print(f"\nAll outputs saved to: {output_dir}")
print(f"  - Individual stride CSV files: stride_XXX_velocity.csv")
print(f"  - Summary of all strides: stride_velocity_summary.csv")
print(f"  - Summary of valid strides: stride_velocity_summary_filtered.csv")
print(f"  - Visualizations: stride_quality_analysis.png, valid_strides_summary.png")