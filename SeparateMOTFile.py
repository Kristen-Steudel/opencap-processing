# Separate the .mot kinematics file into individual steps based on zero crossings

import os
import pandas as pd
import numpy as np

# %% Configuration
stride_times_file = r'G:\Shared drives\Stanford Football\January_19\subject2\Kinematics\Outputs\stride_times.csv'
mot_file = r'G:\Shared drives\Stanford Football\January_19\subject2\OpenSimData\OpenPose_default\3-cameras\Kinematics\ID2_S2_fly_LSTM.mot'
output_dir = r'G:\Shared drives\Stanford Football\January_19\subject2\Kinematics\Outputs\Strides'

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# %% Load stride times
stride_times_df = pd.read_csv(stride_times_file)
print(f"Loaded {len(stride_times_df)} stride events")
print(stride_times_df.head())

# Separate by side
left_stride_times = stride_times_df[stride_times_df['side'] == 'left']['time'].values
right_stride_times = stride_times_df[stride_times_df['side'] == 'right']['time'].values

print(f"\nLeft strides: {len(left_stride_times)}")
print(f"Right strides: {len(right_stride_times)}")

# %% Load .mot file
def read_mot_file(mot_path):
    """
    Read an OpenSim .mot file and return header lines and data as DataFrame.
    """
    with open(mot_path, 'r') as f:
        lines = f.readlines()
    
    # Find where the header ends and data begins
    header_lines = []
    data_start_idx = 0
    
    for i, line in enumerate(lines):
        if line.strip().startswith('endheader'):
            data_start_idx = i + 1
            header_lines = lines[:i+1]
            break
        elif line.strip().startswith('time') or (i > 0 and 'time' in lines[i-1].lower()):
            # Some .mot files don't have 'endheader'
            data_start_idx = i
            header_lines = lines[:i]
            break
    
    if data_start_idx == 0:
        # Try to find column headers
        for i, line in enumerate(lines):
            if 'time' in line.lower():
                data_start_idx = i
                header_lines = lines[:i]
                break
    
    # Read the data portion
    data_lines = lines[data_start_idx:]
    
    # Parse column names
    column_line = data_lines[0].strip()
    columns = column_line.split()
    
    # Parse data
    data_rows = []
    for line in data_lines[1:]:
        if line.strip():  # Skip empty lines
            try:
                values = [float(x) for x in line.strip().split()]
                data_rows.append(values)
            except ValueError:
                continue
    
    # Create DataFrame
    df = pd.DataFrame(data_rows, columns=columns)
    
    return header_lines, df

# Load the .mot file
print(f"\nLoading .mot file: {mot_file}")
header_lines, mot_data = read_mot_file(mot_file)
print(f"Loaded {len(mot_data)} frames")
print(f"Time range: {mot_data['time'].min():.3f} to {mot_data['time'].max():.3f} seconds")
print(f"Columns: {list(mot_data.columns)}")

# %% Function to extract stride and save
def save_stride_segment(mot_data, header_lines, start_time, end_time, output_path, columns):
    """
    Extract a time segment from mot_data and save as a new .mot file.
    """
    # Extract data within time range
    mask = (mot_data['time'] >= start_time) & (mot_data['time'] <= end_time)
    stride_data = mot_data[mask].copy()
    
    if len(stride_data) == 0:
        print(f"  Warning: No data found between {start_time:.3f} and {end_time:.3f}")
        return False
    
    # Reset time to start at 0
    stride_data['time'] = stride_data['time'] - stride_data['time'].iloc[0]
    
    # Write to file
    with open(output_path, 'w') as f:
        # Write header
        for line in header_lines:
            # Update nRows if present
            if 'nRows' in line or 'nrows' in line.lower():
                f.write(f"nRows={len(stride_data)}\n")
            elif 'nColumns' in line or 'ncolumns' in line.lower():
                f.write(f"nColumns={len(columns)}\n")
            else:
                f.write(line)
        
        # Write column headers
        f.write('\t'.join(columns) + '\n')
        
        # Write data
        for idx, row in stride_data.iterrows():
            row_str = '\t'.join([f'{val:.8f}' for val in row.values])
            f.write(row_str + '\n')
    
    return True

# %% Separate into strides for LEFT foot
print("\n" + "="*60)
print("Extracting LEFT foot strides...")
print("="*60)

left_stride_dir = os.path.join(output_dir, 'left_strides')
os.makedirs(left_stride_dir, exist_ok=True)

for i in range(len(left_stride_times) - 1):
    start_time = left_stride_times[i]
    end_time = left_stride_times[i + 1]
    
    output_path = os.path.join(left_stride_dir, f'left_stride_{i+1:03d}.mot')
    
    success = save_stride_segment(mot_data, header_lines, start_time, end_time, 
                                   output_path, mot_data.columns)
    
    if success:
        duration = end_time - start_time
        print(f"Stride {i+1:3d}: {start_time:6.3f} to {end_time:6.3f} s (duration: {duration:.3f} s) → {os.path.basename(output_path)}")

print(f"\nSaved {len(left_stride_times)-1} left strides to: {left_stride_dir}")

# %% Separate into strides for RIGHT foot
print("\n" + "="*60)
print("Extracting RIGHT foot strides...")
print("="*60)

right_stride_dir = os.path.join(output_dir, 'right_strides')
os.makedirs(right_stride_dir, exist_ok=True)

for i in range(len(right_stride_times) - 1):
    start_time = right_stride_times[i]
    end_time = right_stride_times[i + 1]
    
    output_path = os.path.join(right_stride_dir, f'right_stride_{i+1:03d}.mot')
    
    success = save_stride_segment(mot_data, header_lines, start_time, end_time, 
                                   output_path, mot_data.columns)
    
    if success:
        duration = end_time - start_time
        print(f"Stride {i+1:3d}: {start_time:6.3f} to {end_time:6.3f} s (duration: {duration:.3f} s) → {os.path.basename(output_path)}")

print(f"\nSaved {len(right_stride_times)-1} right strides to: {right_stride_dir}")

# %% Summary statistics
print("\n" + "="*60)
print("STRIDE SEPARATION SUMMARY")
print("="*60)

if len(left_stride_times) > 1:
    left_durations = np.diff(left_stride_times)
    print(f"\nLeft Strides ({len(left_durations)} strides):")
    print(f"  Mean duration:   {np.mean(left_durations):.3f} s")
    print(f"  Std duration:    {np.std(left_durations):.3f} s")
    print(f"  Min duration:    {np.min(left_durations):.3f} s")
    print(f"  Max duration:    {np.max(left_durations):.3f} s")
    print(f"  Mean frequency:  {1/np.mean(left_durations):.3f} Hz ({60/np.mean(left_durations):.1f} strides/min)")

if len(right_stride_times) > 1:
    right_durations = np.diff(right_stride_times)
    print(f"\nRight Strides ({len(right_durations)} strides):")
    print(f"  Mean duration:   {np.mean(right_durations):.3f} s")
    print(f"  Std duration:    {np.std(right_durations):.3f} s")
    print(f"  Min duration:    {np.min(right_durations):.3f} s")
    print(f"  Max duration:    {np.max(right_durations):.3f} s")
    print(f"  Mean frequency:  {1/np.mean(right_durations):.3f} Hz ({60/np.mean(right_durations):.1f} strides/min)")

print("="*60)

# %% Create a summary CSV
summary_data = []

for i in range(len(left_stride_times) - 1):
    summary_data.append({
        'stride_number': i + 1,
        'side': 'left',
        'start_time': left_stride_times[i],
        'end_time': left_stride_times[i + 1],
        'duration': left_stride_times[i + 1] - left_stride_times[i],
        'filename': f'left_stride_{i+1:03d}.mot'
    })

for i in range(len(right_stride_times) - 1):
    summary_data.append({
        'stride_number': i + 1,
        'side': 'right',
        'start_time': right_stride_times[i],
        'end_time': right_stride_times[i + 1],
        'duration': right_stride_times[i + 1] - right_stride_times[i],
        'filename': f'right_stride_{i+1:03d}.mot'
    })

summary_df = pd.DataFrame(summary_data)
summary_df = summary_df.sort_values('start_time').reset_index(drop=True)

summary_path = os.path.join(output_dir, 'stride_segments_summary.csv')
summary_df.to_csv(summary_path, index=False)
print(f"\nStride summary saved to: {summary_path}")

# %% Visualize stride segmentation
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

# Plot a sample coordinate to visualize segmentation
if 'knee_angle_l' in mot_data.columns:
    sample_coord_l = 'knee_angle_l'
    sample_coord_r = 'knee_angle_r'
elif 'knee_flexion_l' in mot_data.columns:
    sample_coord_l = 'knee_flexion_l'
    sample_coord_r = 'knee_flexion_r'
else:
    # Use first non-time column
    sample_coord_l = mot_data.columns[1]
    sample_coord_r = mot_data.columns[1]

# Left strides
axes[0].plot(mot_data['time'], mot_data[sample_coord_l], linewidth=1.5, color='blue', alpha=0.7)
for stride_time in left_stride_times:
    axes[0].axvline(x=stride_time, color='red', linestyle='--', linewidth=1, alpha=0.6)
axes[0].set_ylabel(f'{sample_coord_l} (deg)', fontsize=11)
axes[0].set_title('Left Stride Segmentation', fontsize=13)
axes[0].grid(alpha=0.3)

# Right strides
axes[1].plot(mot_data['time'], mot_data[sample_coord_r], linewidth=1.5, color='orange', alpha=0.7)
for stride_time in right_stride_times:
    axes[1].axvline(x=stride_time, color='red', linestyle='--', linewidth=1, alpha=0.6)
axes[1].set_ylabel(f'{sample_coord_r} (deg)', fontsize=11)
axes[1].set_xlabel('Time (s)', fontsize=11)
axes[1].set_title('Right Stride Segmentation', fontsize=13)
axes[1].grid(alpha=0.3)

plt.tight_layout()
plot_path = os.path.join(output_dir, 'stride_segmentation_visualization.png')
plt.savefig(plot_path, dpi=300)
print(f"Visualization saved to: {plot_path}")
plt.show()