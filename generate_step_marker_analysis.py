'''
    ---------------------------------------------------------------------------
    Step-based Marker Trajectory Analysis Script
    ---------------------------------------------------------------------------
    
    Analyzes knee and hip marker positions throughout each step.
    Generates per-step marker trajectory plots and comparison plots.
    
    For each detected step, plots:
    - Knee marker positions (x, y, z)
    - Hip marker positions (x, y, z)
    
    Outputs individual step plots and combined comparison/mean plots.
'''

import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import utilsKinematics
from utilsTRC import trc_2_dict
from utils import download_kinematics, get_model_name_from_metadata
import opensim as osim

# ============================================================================
# CONFIGURATION - ADJUST FOR EACH RUN
# ============================================================================
subject_num = 10
date = 'February_23'
session = '6'
trial_type = 'fly'
filter_freq = 15  # Hz was 10 for normal data filter on the kinematics
coord_filter_freq = 10  # Hz
marker_filter_freq = 10  # Hz
angular_vel_filter_freq = 2  # Hz (for step detection)

# Knee/Hip marker pairs to track
KNEE_MARKERS = ['LKnee', 'RKnee']
HIP_MARKERS = ['LHip', 'RHip']

# ============================================================================
# SETUP AND DATA LOADING
# ============================================================================

# For normal data
# session_id = os.path.normpath(
#     f'G:\\Shared drives\\Stanford Football\\{date}\\subject{subject_num}\\CleanedKinematics\\OpenPose_default\\3-cameras\\Kinematics'
# )

# specific_trial_names = [f'ID{subject_num}_S{session}_{trial_type}_LSTM_filtered_{filter_freq}Hz']


# For testing filtering markers post augmentation
session_id = os.path.normpath(
    f'G:\\Shared drives\\Stanford Football\\{date}\\subject{subject_num}\\CleanedKinematics\\filtered_post_augmentation\\'
)

specific_trial_names = [f'ID{subject_num}_S{session}_{trial_type}_LSTM_filt{filter_freq}Hz']


# Determine data folder and find model
if os.path.exists(session_id):
    def find_session_root(path):
        path = os.path.abspath(path)
        while True:
            if os.path.exists(os.path.join(path, 'sessionMetadata.yaml')):
                return path
            opensimdata = os.path.join(path, 'OpenSimData')
            markerdata = os.path.join(path, 'MarkerData')
            if os.path.exists(opensimdata) or os.path.exists(markerdata):
                return path
            parent = os.path.dirname(path)
            if parent == path:
                return None
            path = parent

    norm_path = os.path.normpath(session_id)
    parts = norm_path.split(os.path.sep)
    lower_parts = [p.lower() for p in parts]
    
    if 'opensimdata' in lower_parts:
        idx = lower_parts.index('opensimdata')
        if idx > 0:
            data_folder = os.path.sep.join(parts[:idx])
        else:
            data_folder = os.path.sep.join(parts[:1])
        data_folder = data_folder.rstrip(os.path.sep)
    else:
        data_folder = find_session_root(session_id)
        if data_folder is None:
            raise FileNotFoundError(f"Could not find session root for path: {session_id}")

    # Find trial files
    mot_files = sorted(glob.glob(os.path.join(data_folder, 'OpenSimData', 'Kinematics', '*.mot')))
    if not mot_files:
        mot_files = sorted(glob.glob(os.path.join(data_folder, '**', '*.mot'), recursive=True))

    if len(mot_files) == 0:
        raise FileNotFoundError(f"No .mot files found")

    trial_names = [os.path.splitext(os.path.basename(m))[0] for m in mot_files]
    if specific_trial_names is not None:
        trial_names = [t for t in trial_names if t in specific_trial_names]

    # Find model
    model_files = sorted(glob.glob(os.path.join(data_folder, 'OpenSimData', 'OpenPose_default', '3-cameras', 'Model', '*scaled.osim')))
    if not model_files:
        raise FileNotFoundError("No scaled .osim model found")
    
    modelName = os.path.splitext(os.path.basename(model_files[0]))[0]
    model_path = model_files[0]
else:
    trial_names, modelName = download_kinematics(session_id, folder=data_folder, trialNames=specific_trial_names)
    model_path = os.path.join(data_folder, 'OpenSimData', 'Model', modelName + '.osim')

print(f"Session root: {data_folder}")
print(f"Model: {modelName}")
print(f"Trials: {trial_names}")


# ============================================================================
# STEP DETECTION FUNCTION
# ============================================================================

def find_negative_zero_crossings(time, signal_data):
    """
    Find the times where the signal crosses zero from positive to negative.
    """
    crossing_times = []
    crossing_indices = []
    
    for i in range(len(signal_data) - 1):
        if signal_data[i] > 0 and signal_data[i + 1] <= 0:
            t0, t1 = time[i], time[i + 1]
            v0, v1 = signal_data[i], signal_data[i + 1]
            
            if v1 != v0:
                crossing_time = t0 - v0 * (t1 - t0) / (v1 - v0)
            else:
                crossing_time = t0
            
            crossing_times.append(crossing_time)
            crossing_indices.append(i)
    
    return np.array(crossing_times), np.array(crossing_indices)


# ============================================================================
# PROCESS EACH TRIAL
# ============================================================================

for trial_name in trial_names:
    print(f"\n{'='*70}")
    print(f"Processing trial: {trial_name}")
    print(f"{'='*70}")
    
    # ========================================================================
    # LOAD KINEMATICS DATA
    # ========================================================================
    
    print("Loading kinematics data...")
    kinematics = utilsKinematics.kinematics(
        data_folder,
        trial_name,
        modelName=modelName,
        lowpass_cutoff_frequency_for_coordinate_values=coord_filter_freq
    )
    
    # Get shank angular velocity for step detection
    angular_velocity = kinematics.get_body_angular_velocity(
        body_names=['tibia_l', 'tibia_r'],
        lowpass_cutoff_frequency=angular_vel_filter_freq,
        expressed_in='ground'
    )
    
    # Load marker data from .trc file
    trc_file_name = f'ID{subject_num}_S{session}_{trial_type}_LSTM.trc'
    trc_file_path = os.path.join(
        'G:\\Shared drives\\Stanford Football',
        date,
        f'subject{subject_num}',
        'CleanedMarkerData',
        'OpenPose_default',
        '3-cameras',
        'PostAugmentation_v0.2',
        trc_file_name
    )
    
    try:
        # Load TRC file using trc_2_dict function
        marker_data_raw = trc_2_dict(trc_file_path)
        print(f"Marker data loaded from: {trc_file_path}")
        print(f"Loaded {len(marker_data_raw['markers'])} markers: {marker_data_raw['marker_names']}")
        markers_available = True
    except Exception as e:
        print(f"Error: Could not load marker data: {e}")
        print(f"Tried to load: {trc_file_path}")
        print("This script requires marker data. Skipping this trial.")
        continue
    
    time_data = angular_velocity['time'].values
    
    # Interpolate marker data to kinematics time grid
    marker_time = marker_data_raw['time']
    marker_data = {'markers': {}, 'marker_names': marker_data_raw['marker_names']}
    
    for marker_name, marker_positions in marker_data_raw['markers'].items():
        # marker_positions is Nx3 array
        interp_x = np.interp(time_data, marker_time, marker_positions[:, 0])
        interp_y = np.interp(time_data, marker_time, marker_positions[:, 1])
        interp_z = np.interp(time_data, marker_time, marker_positions[:, 2])
        marker_data['markers'][marker_name] = np.column_stack([interp_x, interp_y, interp_z])
    
    # ========================================================================
    # DETECT STEPS FROM ANGULAR VELOCITY
    # ========================================================================
    
    print("Detecting steps...")
    
    left_crossing_times, _ = find_negative_zero_crossings(
        angular_velocity['time'].values, 
        angular_velocity['tibia_l_z'].values
    )
    right_crossing_times, _ = find_negative_zero_crossings(
        angular_velocity['time'].values, 
        angular_velocity['tibia_r_z'].values
    )
    
    # Combine and sort
    all_step_times = np.concatenate([left_crossing_times, right_crossing_times])
    all_step_sides = ['left'] * len(left_crossing_times) + ['right'] * len(right_crossing_times)
    
    sort_indices = np.argsort(all_step_times)
    all_step_times = all_step_times[sort_indices]
    all_step_sides = [all_step_sides[i] for i in sort_indices]
    
    # Create step DataFrame
    steps_df = pd.DataFrame({
        'time': all_step_times,
        'side': all_step_sides
    })
    
    print(f"Detected {len(all_step_times)} steps total")
    print(f"  Left steps: {len(left_crossing_times)}")
    print(f"  Right steps: {len(right_crossing_times)}")
    
    # ========================================================================
    # CREATE OUTPUT FOLDER
    # ========================================================================
    
    output_base_dir = os.path.join(data_folder, 'quality_check')
    os.makedirs(output_base_dir, exist_ok=True)
    
    trial_output_dir = os.path.join(output_base_dir, trial_name + '_markers')
    os.makedirs(trial_output_dir, exist_ok=True)
    
    plots_dir = os.path.join(trial_output_dir, 'individual_steps')
    os.makedirs(plots_dir, exist_ok=True)
    
    # Save step times
    steps_csv_path = os.path.join(trial_output_dir, 'step_times.csv')
    steps_df.to_csv(steps_csv_path, index=False)
    print(f"Step times saved to: {steps_csv_path}")
    
    # ========================================================================
    # GENERATE PER-STEP PLOTS
    # ========================================================================
    
    print("\nGenerating per-step marker plots...")
    
    # Calculate total number of steps for reverse numbering
    total_steps = len(all_step_times) - 1
    
    for step_idx in range(total_steps):
        # Reverse step numbering
        step_number = total_steps - step_idx
        
        step_start_time = all_step_times[step_idx]
        step_end_time = all_step_times[step_idx + 1]
        step_side = all_step_sides[step_idx]
        
        # Extract data for this step
        step_mask = (time_data >= step_start_time) & (time_data < step_end_time)
        step_time = time_data[step_mask]
        
        if len(step_time) < 2:
            print(f"  Skipping step {step_number} (too few samples)")
            continue
        
        # Normalize time to start at 0
        step_time_norm = step_time - step_start_time
        
        # Extract marker data
        step_markers = {}
        try:
            for marker in KNEE_MARKERS + HIP_MARKERS:
                if marker in marker_data['markers']:
                    marker_positions = marker_data['markers'][marker]
                    step_markers[marker] = marker_positions[step_mask]
        except Exception as e:
            print(f"  Warning: Could not extract marker data for step {step_number}: {e}")
            continue
        
        # ====================================================================
        # CREATE PER-STEP PLOT (2x3 grid - Knee and Hip, X/Y/Z components)
        # ====================================================================
        
        fig, axes = plt.subplots(2, 3, figsize=(16, 10))
        fig.suptitle(f'Step {step_number:03d} ({step_side}) - Marker Trajectories: {step_start_time:.3f}s - {step_end_time:.3f}s', 
                     fontsize=14, fontweight='bold')
        
        knee_marker = 'LKnee' if 'left' in step_side else 'RKnee'
        hip_marker = 'LHip' if 'left' in step_side else 'RHip'
        
        # Row 1: Knee marker X, Y, Z
        if knee_marker in step_markers and len(step_markers[knee_marker]) > 0:
            knee_pos = step_markers[knee_marker]
            
            # Knee X
            ax = axes[0, 0]
            ax.plot(step_time_norm, knee_pos[:, 0], 'b-', linewidth=2.5)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Position (m)', fontsize=10)
            ax.set_title(f'Knee X Position - {knee_marker}', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
            
            # Knee Y
            ax = axes[0, 1]
            ax.plot(step_time_norm, knee_pos[:, 1], 'g-', linewidth=2.5)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Position (m)', fontsize=10)
            ax.set_title(f'Knee Y Position - {knee_marker}', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
            
            # Knee Z
            ax = axes[0, 2]
            ax.plot(step_time_norm, knee_pos[:, 2], 'r-', linewidth=2.5)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Position (m)', fontsize=10)
            ax.set_title(f'Knee Z Position - {knee_marker}', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
        else:
            for col in range(3):
                ax = axes[0, col]
                ax.text(0.5, 0.5, 'Knee marker data not available', ha='center', va='center', transform=ax.transAxes)
        
        # Row 2: Hip marker X, Y, Z
        if hip_marker in step_markers and len(step_markers[hip_marker]) > 0:
            hip_pos = step_markers[hip_marker]
            
            # Hip X
            ax = axes[1, 0]
            ax.plot(step_time_norm, hip_pos[:, 0], 'b-', linewidth=2.5)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Position (m)', fontsize=10)
            ax.set_title(f'Hip X Position - {hip_marker}', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
            
            # Hip Y
            ax = axes[1, 1]
            ax.plot(step_time_norm, hip_pos[:, 1], 'g-', linewidth=2.5)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Position (m)', fontsize=10)
            ax.set_title(f'Hip Y Position - {hip_marker}', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
            
            # Hip Z
            ax = axes[1, 2]
            ax.plot(step_time_norm, hip_pos[:, 2], 'r-', linewidth=2.5)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Position (m)', fontsize=10)
            ax.set_title(f'Hip Z Position - {hip_marker}', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
        else:
            for col in range(3):
                ax = axes[1, col]
                ax.text(0.5, 0.5, 'Hip marker data not available', ha='center', va='center', transform=ax.transAxes)
        
        plt.tight_layout()
        
        # Save plot
        plot_filename = f'step_{step_number:03d}_{step_side}.png'
        plot_path = os.path.join(plots_dir, plot_filename)
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"  Saved step {step_number:03d} marker plot")
    
    # ========================================================================
    # CREATE COMPARISON PLOT FOR STEPS 1-6
    # ========================================================================
    
    print("\nGenerating marker comparison plot for steps 1-6...")
    
    start_idx = max(0, total_steps - 6)
    end_idx = total_steps
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Marker Trajectory Comparison - Steps 1-6 (Reverse Numbering)\nTrial: {trial_name}', 
                 fontsize=14, fontweight='bold')
    
    # Panel 1: Knee marker X position - steps 1-6
    ax = axes[0, 0]
    for step_idx in range(start_idx, end_idx):
        step_number = total_steps - step_idx
        step_start_time = all_step_times[step_idx]
        step_end_time = all_step_times[step_idx + 1]
        step_side = all_step_sides[step_idx]
        step_mask = (time_data >= step_start_time) & (time_data < step_end_time)
        step_time = time_data[step_mask]
        step_time_norm = (step_time - step_start_time) / (step_end_time - step_start_time)
        
        knee_marker = 'LKnee' if 'left' in step_side else 'RKnee'
        if knee_marker in marker_data['markers']:
            try:
                knee_pos = marker_data['markers'][knee_marker][step_mask]
                color = 'blue' if 'left' in step_side else 'red'
                ax.plot(step_time_norm, knee_pos[:, 0], color=color, alpha=0.5, linewidth=1.5, label=f'Step {step_number}')
            except:
                pass
    
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('X Position (m)', fontsize=10)
    ax.set_title('Knee Marker X Position - Steps 1-6', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    
    # Panel 2: Knee marker Y position - steps 1-6
    ax = axes[0, 1]
    for step_idx in range(start_idx, end_idx):
        step_number = total_steps - step_idx
        step_start_time = all_step_times[step_idx]
        step_end_time = all_step_times[step_idx + 1]
        step_side = all_step_sides[step_idx]
        step_mask = (time_data >= step_start_time) & (time_data < step_end_time)
        step_time = time_data[step_mask]
        step_time_norm = (step_time - step_start_time) / (step_end_time - step_start_time)
        
        knee_marker = 'LKnee' if 'left' in step_side else 'RKnee'
        if knee_marker in marker_data['markers']:
            try:
                knee_pos = marker_data['markers'][knee_marker][step_mask]
                color = 'blue' if 'left' in step_side else 'red'
                ax.plot(step_time_norm, knee_pos[:, 1], color=color, alpha=0.5, linewidth=1.5, label=f'Step {step_number}')
            except:
                pass
    
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('Y Position (m)', fontsize=10)
    ax.set_title('Knee Marker Y Position - Steps 1-6', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    
    # Panel 3: Hip marker X position - steps 1-6
    ax = axes[1, 0]
    for step_idx in range(start_idx, end_idx):
        step_number = total_steps - step_idx
        step_start_time = all_step_times[step_idx]
        step_end_time = all_step_times[step_idx + 1]
        step_side = all_step_sides[step_idx]
        step_mask = (time_data >= step_start_time) & (time_data < step_end_time)
        step_time = time_data[step_mask]
        step_time_norm = (step_time - step_start_time) / (step_end_time - step_start_time)
        
        hip_marker = 'LHip' if 'left' in step_side else 'RHip'
        if hip_marker in marker_data['markers']:
            try:
                hip_pos = marker_data['markers'][hip_marker][step_mask]
                color = 'blue' if 'left' in step_side else 'red'
                ax.plot(step_time_norm, hip_pos[:, 0], color=color, alpha=0.5, linewidth=1.5, label=f'Step {step_number}')
            except:
                pass
    
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('X Position (m)', fontsize=10)
    ax.set_title('Hip Marker X Position - Steps 1-6', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    
    # Panel 4: Hip marker Y position - steps 1-6
    ax = axes[1, 1]
    for step_idx in range(start_idx, end_idx):
        step_number = total_steps - step_idx
        step_start_time = all_step_times[step_idx]
        step_end_time = all_step_times[step_idx + 1]
        step_side = all_step_sides[step_idx]
        step_mask = (time_data >= step_start_time) & (time_data < step_end_time)
        step_time = time_data[step_mask]
        step_time_norm = (step_time - step_start_time) / (step_end_time - step_start_time)
        
        hip_marker = 'LHip' if 'left' in step_side else 'RHip'
        if hip_marker in marker_data['markers']:
            try:
                hip_pos = marker_data['markers'][hip_marker][step_mask]
                color = 'blue' if 'left' in step_side else 'red'
                ax.plot(step_time_norm, hip_pos[:, 1], color=color, alpha=0.5, linewidth=1.5, label=f'Step {step_number}')
            except:
                pass
    
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('Y Position (m)', fontsize=10)
    ax.set_title('Hip Marker Y Position - Steps 1-6', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    
    plt.tight_layout()
    comparison_plot_path = os.path.join(trial_output_dir, 'marker_comparison_steps_1_to_6.png')
    plt.savefig(comparison_plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Saved marker comparison plot: {comparison_plot_path}")
    
    # ========================================================================
    # CREATE MEAN MARKER TRAJECTORY PLOT FOR STEPS 1-6
    # ========================================================================
    
    print("\nGenerating mean marker trajectory plot...")
    
    normalized_time_common = np.linspace(0, 1, 100)
    
    # Collect knee marker trajectories
    knee_x_trajectories = []
    knee_y_trajectories = []
    knee_z_trajectories = []
    
    # Collect hip marker trajectories
    hip_x_trajectories = []
    hip_y_trajectories = []
    hip_z_trajectories = []
    
    for step_idx in range(start_idx, end_idx):
        step_start_time = all_step_times[step_idx]
        step_end_time = all_step_times[step_idx + 1]
        step_side = all_step_sides[step_idx]
        step_mask = (time_data >= step_start_time) & (time_data < step_end_time)
        step_time = time_data[step_mask]
        
        if len(step_time) < 2:
            continue
            
        step_time_norm = (step_time - step_start_time) / (step_end_time - step_start_time)
        
        # Knee marker
        knee_marker = 'LKnee' if 'left' in step_side else 'RKnee'
        if knee_marker in marker_data['markers']:
            try:
                knee_pos = marker_data['markers'][knee_marker][step_mask]
                if len(knee_pos) > 1:
                    knee_x_trajectories.append(np.interp(normalized_time_common, step_time_norm, knee_pos[:, 0]))
                    knee_y_trajectories.append(np.interp(normalized_time_common, step_time_norm, knee_pos[:, 1]))
                    knee_z_trajectories.append(np.interp(normalized_time_common, step_time_norm, knee_pos[:, 2]))
            except:
                pass
        
        # Hip marker
        hip_marker = 'LHip' if 'left' in step_side else 'RHip'
        if hip_marker in marker_data['markers']:
            try:
                hip_pos = marker_data['markers'][hip_marker][step_mask]
                if len(hip_pos) > 1:
                    hip_x_trajectories.append(np.interp(normalized_time_common, step_time_norm, hip_pos[:, 0]))
                    hip_y_trajectories.append(np.interp(normalized_time_common, step_time_norm, hip_pos[:, 1]))
                    hip_z_trajectories.append(np.interp(normalized_time_common, step_time_norm, hip_pos[:, 2]))
            except:
                pass
    
    # Calculate means
    mean_knee_x = np.mean(knee_x_trajectories, axis=0) if knee_x_trajectories else None
    std_knee_x = np.std(knee_x_trajectories, axis=0) if knee_x_trajectories else None
    mean_knee_y = np.mean(knee_y_trajectories, axis=0) if knee_y_trajectories else None
    std_knee_y = np.std(knee_y_trajectories, axis=0) if knee_y_trajectories else None
    mean_knee_z = np.mean(knee_z_trajectories, axis=0) if knee_z_trajectories else None
    std_knee_z = np.std(knee_z_trajectories, axis=0) if knee_z_trajectories else None
    
    mean_hip_x = np.mean(hip_x_trajectories, axis=0) if hip_x_trajectories else None
    std_hip_x = np.std(hip_x_trajectories, axis=0) if hip_x_trajectories else None
    mean_hip_y = np.mean(hip_y_trajectories, axis=0) if hip_y_trajectories else None
    std_hip_y = np.std(hip_y_trajectories, axis=0) if hip_y_trajectories else None
    mean_hip_z = np.mean(hip_z_trajectories, axis=0) if hip_z_trajectories else None
    std_hip_z = np.std(hip_z_trajectories, axis=0) if hip_z_trajectories else None
    
    # Create mean trajectory plot
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle(f'Mean Marker Trajectories - Steps 1-6\nTrial: {trial_name}', 
                 fontsize=14, fontweight='bold')
    
    # Knee X
    ax = axes[0, 0]
    if mean_knee_x is not None:
        ax.plot(normalized_time_common, mean_knee_x, 'b-', linewidth=2.5, label='Mean')
        ax.fill_between(normalized_time_common, mean_knee_x - std_knee_x, mean_knee_x + std_knee_x, 
                         alpha=0.2, color='blue', label='±1 Std Dev')
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('X Position (m)', fontsize=10)
    ax.set_title('Knee Marker X Position', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    
    # Knee Y
    ax = axes[0, 1]
    if mean_knee_y is not None:
        ax.plot(normalized_time_common, mean_knee_y, 'g-', linewidth=2.5, label='Mean')
        ax.fill_between(normalized_time_common, mean_knee_y - std_knee_y, mean_knee_y + std_knee_y, 
                         alpha=0.2, color='green', label='±1 Std Dev')
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('Y Position (m)', fontsize=10)
    ax.set_title('Knee Marker Y Position', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    
    # Knee Z
    ax = axes[0, 2]
    if mean_knee_z is not None:
        ax.plot(normalized_time_common, mean_knee_z, 'r-', linewidth=2.5, label='Mean')
        ax.fill_between(normalized_time_common, mean_knee_z - std_knee_z, mean_knee_z + std_knee_z, 
                         alpha=0.2, color='red', label='±1 Std Dev')
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('Z Position (m)', fontsize=10)
    ax.set_title('Knee Marker Z Position', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    
    # Hip X
    ax = axes[1, 0]
    if mean_hip_x is not None:
        ax.plot(normalized_time_common, mean_hip_x, 'b-', linewidth=2.5, label='Mean')
        ax.fill_between(normalized_time_common, mean_hip_x - std_hip_x, mean_hip_x + std_hip_x, 
                         alpha=0.2, color='blue', label='±1 Std Dev')
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('X Position (m)', fontsize=10)
    ax.set_title('Hip Marker X Position', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    
    # Hip Y
    ax = axes[1, 1]
    if mean_hip_y is not None:
        ax.plot(normalized_time_common, mean_hip_y, 'g-', linewidth=2.5, label='Mean')
        ax.fill_between(normalized_time_common, mean_hip_y - std_hip_y, mean_hip_y + std_hip_y, 
                         alpha=0.2, color='green', label='±1 Std Dev')
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('Y Position (m)', fontsize=10)
    ax.set_title('Hip Marker Y Position', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    
    # Hip Z
    ax = axes[1, 2]
    if mean_hip_z is not None:
        ax.plot(normalized_time_common, mean_hip_z, 'r-', linewidth=2.5, label='Mean')
        ax.fill_between(normalized_time_common, mean_hip_z - std_hip_z, mean_hip_z + std_hip_z, 
                         alpha=0.2, color='red', label='±1 Std Dev')
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('Z Position (m)', fontsize=10)
    ax.set_title('Hip Marker Z Position', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    
    plt.tight_layout()
    mean_trajectory_path = os.path.join(trial_output_dir, 'marker_mean_trajectories_1_to_6.png')
    plt.savefig(mean_trajectory_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Saved mean marker trajectory plot: {mean_trajectory_path}")
    
    print("\n" + "="*70)
    print(f"Completed marker analysis for trial: {trial_name}")
    print(f"Output directory: {trial_output_dir}")
    print("="*70)

print("\n" + "="*70)
print("ALL MARKER ANALYSES COMPLETED")
print("="*70)
