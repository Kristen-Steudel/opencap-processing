'''
    ---------------------------------------------------------------------------
    Step-based Quality Check Visualization Script
    ---------------------------------------------------------------------------
    
    Combines step detection (from SeparateSteps.py) with kinematic analysis 
    (from example_cleaned.py) to generate per-step quality check plots.
    
    For each detected step, plots:
    - Knee flexion angle
    - Hip flexion angle
    - Knee flexion velocity
    - Hip flexion velocity
    - Knee marker positions (x, y, z)
    - Hip marker positions (x, y, z)
    
    Outputs individual step plots and combined comparison plots.
'''

import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from utilsTRC import trc_2_dict
import utilsKinematics
from utils import download_kinematics, get_model_name_from_metadata
import opensim as osim

# ============================================================================
# CONFIGURATION - ADJUST FOR EACH RUN
# ============================================================================
subject_num = 2
date = 'March_2'
session = '7'
trial_type = 'sprint'
filter_freq = 15  # Hz was 10 Hz for normal trials for kinematics filter freq
coord_filter_freq = 10  # Hz
marker_filter_freq = 10  # Hz
angular_vel_filter_freq = 2  # Hz (for step detection)

# Knee/Hip marker pairs to track
KNEE_MARKERS = ['LKnee', 'RKnee', 'LAnkle', 'RAnkle'] # Added ankle markers for additional quality check info
HIP_MARKERS = ['LHip', 'RHip']
COORDINATES_TO_PLOT = ['knee_angle_l', 'knee_angle_r', 'hip_flexion_l', 'hip_flexion_r']

# ============================================================================
# SETUP AND DATA LOADING
# ============================================================================

# For normal testing
# session_id = os.path.normpath(
#     f'G:\\Shared drives\\Stanford Football\\{date}\\subject{subject_num}\\CleanedKinematics\\OpenPose_default\\3-cameras\\Kinematics'
# )

# specific_trial_names = [f'ID{subject_num}_S{session}_{trial_type}_LSTM_filtered_{filter_freq}Hz']

# For testing filtering markers post augmentation
session_id = os.path.normpath(
    f'G:\\Shared drives\\Stanford Football\\{date}\\subject{subject_num}\\CleanedKinematics\\filtered_post_augmentation\\'
)

specific_trial_names = [f'ID{subject_num}_S{session}_{trial_type}_LSTM_filtpostaug15Hz_filteredkinematics_{filter_freq}Hz'] #'ACCEL_LSTM', 'DECEL_LSTM']
print(specific_trial_names)


#specific_trial_names = [f'ID{subject_num}_S{session}_{tri al_type}_LSTM_filt{filter_freq}Hz']

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
            t0, t1 = time[i], time[i + 1]
            v0, v1 = signal_data[i], signal_data[i + 1]
            
            # Interpolated crossing time
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
    
    # Get coordinates and velocities
    coord_values = kinematics.get_coordinate_values(in_degrees=True)
    coord_speeds = kinematics.get_coordinate_speeds(in_degrees=True, lowpass_cutoff_frequency=coord_filter_freq)
    
    # Get shank angular velocity for step detection
    angular_velocity = kinematics.get_body_angular_velocity(
        body_names=['tibia_l', 'tibia_r'],
        lowpass_cutoff_frequency=angular_vel_filter_freq,
        expressed_in='ground'
    )
    
    # Get marker data from TRC file
    try:
        # TRYING OUT ADDING IN THE FILTER ON THE POST AUGMENTATION FILES HERE
        trc_file_name = f'ID{subject_num}_S{session}_{trial_type}_LSTM_filt15Hz.trc'
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
        
        # Load TRC file using trc_2_dict function
        marker_data_raw = trc_2_dict(trc_file_path)
        print("Marker data loaded successfully from TRC file for trc file:", trc_file_name)
        
        # Interpolate marker data to kinematics time grid
        time_data_kin = coord_values['time'].values
        marker_time = marker_data_raw['time']
        marker_data = {'markers': {}, 'marker_names': marker_data_raw['marker_names']}
        
        for marker_name, marker_positions in marker_data_raw['markers'].items():
            # marker_positions is Nx3 array
            interp_x = np.interp(time_data_kin, marker_time, marker_positions[:, 0])
            interp_y = np.interp(time_data_kin, marker_time, marker_positions[:, 1])
            interp_z = np.interp(time_data_kin, marker_time, marker_positions[:, 2])
            marker_data['markers'][marker_name] = np.column_stack([interp_x, interp_y, interp_z])
        
        markers_available = True
    except Exception as e:
        print(f"Warning: Could not load marker data: {e}")
        markers_available = False
        marker_data = None
    
    time_data = coord_values['time'].values
    
    # ========================================================================
    # DETECT STEPS FROM ANGULAR VELOCITY
    # ========================================================================
    
    print("Detecting steps...")
    
    # Find negative-going zero crossings for both shanks (sagittal plane = z-axis)
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
    
    trial_output_dir = os.path.join(output_base_dir, trial_name)
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
    
    print("\nGenerating per-step plots...")
    
    # Store data for combined plots
    all_step_plots_data = {coord: [] for coord in COORDINATES_TO_PLOT}
    all_step_plots_data['knee_markers'] = []
    all_step_plots_data['hip_markers'] = []
    
    # Calculate total number of steps for reverse numbering
    total_steps = len(all_step_times) - 1
    
    for step_idx in range(total_steps):
        # Reverse step numbering: first step = total_steps, last step = 1
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
        
        # Extract coordinate data (both positions and velocities from respective dataframes)
        step_coords_values = {}
        step_coords_speeds = {}
        for coord in COORDINATES_TO_PLOT:
            if coord in coord_values.columns:
                step_coords_values[coord] = coord_values[step_mask][coord].values
            if coord in coord_speeds.columns:
                # Coordinate speeds dataframe has same column names as values
                step_coords_speeds[coord] = coord_speeds[step_mask][coord].values
        
        # Extract marker data
        step_markers = {}
        if markers_available and marker_data:
            try:
                for marker in KNEE_MARKERS + HIP_MARKERS:
                    if marker in marker_data['markers']:
                        marker_positions = marker_data['markers'][marker]
                        step_markers[marker] = marker_positions[step_mask]
            except Exception as e:
                print(f"  Warning: Could not extract marker data for step {step_number}: {e}")
        
        # ====================================================================
        # CREATE PER-STEP PLOT (3x4 grid - Knee, Hip, and Ankle markers)
        # ====================================================================
        
        fig, axes = plt.subplots(3, 4, figsize=(18, 12))
        fig.suptitle(f'Step {step_number:03d} ({step_side}): {step_start_time:.3f}s - {step_end_time:.3f}s', 
                     fontsize=14, fontweight='bold')
        
        # ROW 1: KNEE DATA
        # Panel (0,0): Knee flexion angle
        ax = axes[0, 0]
        knee_angle_col = 'knee_angle_l' if 'left' in step_side else 'knee_angle_r'
        if knee_angle_col in step_coords_values:
            ax.plot(step_time_norm, step_coords_values[knee_angle_col], 'b-', linewidth=2)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Angle (deg)', fontsize=10)
            ax.set_title('Knee Flexion Angle', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Data not available', ha='center', va='center')
        
        # Panel (0,1): Knee marker X position
        ax = axes[0, 1]
        knee_marker = 'LKnee' if 'left' in step_side else 'RKnee'
        if knee_marker in step_markers and len(step_markers[knee_marker]) > 0:
            knee_pos = step_markers[knee_marker]
            ax.plot(step_time_norm, knee_pos[:, 0], 'b-', linewidth=2.5)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Position (m)', fontsize=10)
            ax.set_title('Knee Marker X Position', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Marker data not available', ha='center', va='center')
        
        # Panel (0,2): Knee marker Y position
        ax = axes[0, 2]
        knee_marker = 'LKnee' if 'left' in step_side else 'RKnee'
        if knee_marker in step_markers and len(step_markers[knee_marker]) > 0:
            knee_pos = step_markers[knee_marker]
            ax.plot(step_time_norm, knee_pos[:, 1], 'g-', linewidth=2.5)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Position (m)', fontsize=10)
            ax.set_title('Knee Marker Y Position', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Marker data not available', ha='center', va='center')
        
        # Panel (0,3): Knee flexion velocity
        ax = axes[0, 3]
        knee_vel_col = 'knee_angle_l' if 'left' in step_side else 'knee_angle_r'
        if knee_vel_col in step_coords_speeds:
            ax.plot(step_time_norm, step_coords_speeds[knee_vel_col], 'b-', linewidth=2)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Velocity (deg/s)', fontsize=10)
            ax.set_title('Knee Flexion Velocity', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Data not available', ha='center', va='center')
        
        # ROW 2: HIP DATA
        # Panel (1,0): Hip flexion angle
        ax = axes[1, 0]
        hip_angle_col = 'hip_flexion_l' if 'left' in step_side else 'hip_flexion_r'
        if hip_angle_col in step_coords_values:
            ax.plot(step_time_norm, step_coords_values[hip_angle_col], 'r-', linewidth=2)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Angle (deg)', fontsize=10)
            ax.set_title('Hip Flexion Angle', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Data not available', ha='center', va='center')
        
        # Panel (1,1): Hip marker X position
        ax = axes[1, 1]
        hip_marker = 'LHip' if 'left' in step_side else 'RHip'
        if hip_marker in step_markers and len(step_markers[hip_marker]) > 0:
            hip_pos = step_markers[hip_marker]
            ax.plot(step_time_norm, hip_pos[:, 0], 'b-', linewidth=2.5)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Position (m)', fontsize=10)
            ax.set_title('Hip Marker X Position', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Marker data not available', ha='center', va='center')
        
        # Panel (1,2): Hip marker Y position
        ax = axes[1, 2]
        hip_marker = 'LHip' if 'left' in step_side else 'RHip'
        if hip_marker in step_markers and len(step_markers[hip_marker]) > 0:
            hip_pos = step_markers[hip_marker]
            ax.plot(step_time_norm, hip_pos[:, 1], 'g-', linewidth=2.5)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Position (m)', fontsize=10)
            ax.set_title('Hip Marker Y Position', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Marker data not available', ha='center', va='center')
        
        # Panel (1,3): Hip flexion velocity
        ax = axes[1, 3]
        hip_vel_col = 'hip_flexion_l' if 'left' in step_side else 'hip_flexion_r'
        if hip_vel_col in step_coords_speeds:
            ax.plot(step_time_norm, step_coords_speeds[hip_vel_col], 'r-', linewidth=2)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Velocity (deg/s)', fontsize=10)
            ax.set_title('Hip Flexion Velocity', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Data not available', ha='center', va='center')
        
        # ROW 3: ANKLE DATA
        # Panel (2,0): Ankle marker X position
        ax = axes[2, 0]
        ankle_marker = 'LAnkle' if 'left' in step_side else 'RAnkle'
        if ankle_marker in step_markers and len(step_markers[ankle_marker]) > 0:
            ankle_pos = step_markers[ankle_marker]
            ax.plot(step_time_norm, ankle_pos[:, 0], 'b-', linewidth=2.5)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Position (m)', fontsize=10)
            ax.set_title('Ankle Marker X Position', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Marker data not available', ha='center', va='center')
        
        # Panel (2,1): Ankle marker Y position
        ax = axes[2, 1]
        ankle_marker = 'LAnkle' if 'left' in step_side else 'RAnkle'
        if ankle_marker in step_markers and len(step_markers[ankle_marker]) > 0:
            ankle_pos = step_markers[ankle_marker]
            ax.plot(step_time_norm, ankle_pos[:, 1], 'g-', linewidth=2.5)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Position (m)', fontsize=10)
            ax.set_title('Ankle Marker Y Position', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Marker data not available', ha='center', va='center')
        
        # Panel (2,2): Ankle marker Z position
        ax = axes[2, 2]
        ankle_marker = 'LAnkle' if 'left' in step_side else 'RAnkle'
        if ankle_marker in step_markers and len(step_markers[ankle_marker]) > 0:
            ankle_pos = step_markers[ankle_marker]
            ax.plot(step_time_norm, ankle_pos[:, 2], 'r-', linewidth=2.5)
            ax.set_xlabel('Time (s)', fontsize=10)
            ax.set_ylabel('Position (m)', fontsize=10)
            ax.set_title('Ankle Marker Z Position', fontsize=11, fontweight='bold')
            ax.grid(alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Marker data not available', ha='center', va='center')
        
        # Panel (2,3): Empty or placeholder
        ax = axes[2, 3]
        ax.axis('off')
        
        plt.tight_layout()
        
        # Save plot
        plot_filename = f'step_{step_number:03d}_{step_side}.png'
        plot_path = os.path.join(plots_dir, plot_filename)
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"  Saved step {step_number:03d} plot")
    
    # ========================================================================
    # CREATE COMBINED COMPARISON PLOT
    # ========================================================================
    
    print("\nGenerating combined comparison plot...")
    
    # Determine which step indices correspond to steps 1-4 in reverse numbering
    # In reverse numbering: step 1 = last step (idx=total_steps-1), step 4 = idx=(total_steps-4)
    start_idx = max(0, total_steps - 4)
    end_idx = total_steps
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Step Comparison - Steps 1-4 (Reverse Numbering)\nTrial: {trial_name}', 
                 fontsize=14, fontweight='bold')
    
    # Panel 1: Knee flexion angle - steps 1-4 reverse
    ax = axes[0, 0]
    for step_idx in range(start_idx, end_idx):
        step_number = total_steps - step_idx
        step_start_time = all_step_times[step_idx]
        step_end_time = all_step_times[step_idx + 1]
        step_side = all_step_sides[step_idx]
        step_mask = (time_data >= step_start_time) & (time_data < step_end_time)
        step_time = time_data[step_mask]
        step_time_norm = (step_time - step_start_time) / (step_end_time - step_start_time)
        
        knee_angle_col = 'knee_angle_l' if 'left' in step_side else 'knee_angle_r'
        if knee_angle_col in coord_values.columns:
            values = coord_values[step_mask][knee_angle_col].values
            color = 'blue' if 'left' in step_side else 'red'
            ax.plot(step_time_norm, values, color=color, alpha=0.5, linewidth=1.5, label=f'Step {step_number}')
    
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('Angle (deg)', fontsize=10)
    ax.set_title('Knee Flexion Angle - Steps 1-4', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    
    # Panel 2: Hip flexion angle - steps 1-4 reverse
    ax = axes[0, 1]
    for step_idx in range(start_idx, end_idx):
        step_number = total_steps - step_idx
        step_start_time = all_step_times[step_idx]
        step_end_time = all_step_times[step_idx + 1]
        step_side = all_step_sides[step_idx]
        step_mask = (time_data >= step_start_time) & (time_data < step_end_time)
        step_time = time_data[step_mask]
        step_time_norm = (step_time - step_start_time) / (step_end_time - step_start_time)
        
        hip_angle_col = 'hip_flexion_l' if 'left' in step_side else 'hip_flexion_r'
        if hip_angle_col in coord_values.columns:
            values = coord_values[step_mask][hip_angle_col].values
            color = 'blue' if 'left' in step_side else 'red'
            ax.plot(step_time_norm, values, color=color, alpha=0.5, linewidth=1.5, label=f'Step {step_number}')
    
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('Angle (deg)', fontsize=10)
    ax.set_title('Hip Flexion Angle - Steps 1-4', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    
    # Panel 3: Knee flexion velocity - steps 1-4 reverse
    ax = axes[1, 0]
    for step_idx in range(start_idx, end_idx):
        step_number = total_steps - step_idx
        step_start_time = all_step_times[step_idx]
        step_end_time = all_step_times[step_idx + 1]
        step_side = all_step_sides[step_idx]
        step_mask = (time_data >= step_start_time) & (time_data < step_end_time)
        step_time = time_data[step_mask]
        step_time_norm = (step_time - step_start_time) / (step_end_time - step_start_time)
        
        knee_angle_col = 'knee_angle_l' if 'left' in step_side else 'knee_angle_r'
        if knee_angle_col in coord_speeds.columns:
            values = coord_speeds[step_mask][knee_angle_col].values
            color = 'blue' if 'left' in step_side else 'red'
            ax.plot(step_time_norm, values, color=color, alpha=0.5, linewidth=1.5, label=f'Step {step_number}')
    
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('Velocity (deg/s)', fontsize=10)
    ax.set_title('Knee Flexion Velocity - Steps 1-4', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    
    # Panel 4: Hip flexion velocity - steps 1-4 reverse
    ax = axes[1, 1]
    for step_idx in range(start_idx, end_idx):
        step_number = total_steps - step_idx
        step_start_time = all_step_times[step_idx]
        step_end_time = all_step_times[step_idx + 1]
        step_side = all_step_sides[step_idx]
        step_mask = (time_data >= step_start_time) & (time_data < step_end_time)
        step_time = time_data[step_mask]
        step_time_norm = (step_time - step_start_time) / (step_end_time - step_start_time)
        
        hip_angle_col = 'hip_flexion_l' if 'left' in step_side else 'hip_flexion_r'
        if hip_angle_col in coord_speeds.columns:
            values = coord_speeds[step_mask][hip_angle_col].values
            color = 'blue' if 'left' in step_side else 'red'
            ax.plot(step_time_norm, values, color=color, alpha=0.5, linewidth=1.5, label=f'Step {step_number}')
    
    ax.set_xlabel('Normalized Time (0-1)', fontsize=10)
    ax.set_ylabel('Velocity (deg/s)', fontsize=10)
    ax.set_title('Hip Flexion Velocity - Steps 1-4', fontsize=11, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    
    plt.tight_layout()
    
    # Save combined comparison plot
    comparison_plot_path = os.path.join(trial_output_dir, 'step_comparison_steps_1_to_4.png')
    plt.savefig(comparison_plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Saved comparison plot for steps 1-4: {comparison_plot_path}")
    
    # ========================================================================
    # CREATE MEAN TRAJECTORY PLOT FOR STEPS 1-4
    # ========================================================================
    
    print("\nGenerating mean trajectory plot...")
    
    # Collect data for all 4 steps and normalize time
    knee_angle_trajectories = []
    hip_angle_trajectories = []
    normalized_time_common = np.linspace(0, 1, 100)  # Common normalized time grid
    
    for step_idx in range(start_idx, end_idx):
        step_start_time = all_step_times[step_idx]
        step_end_time = all_step_times[step_idx + 1]
        step_side = all_step_sides[step_idx]
        step_mask = (time_data >= step_start_time) & (time_data < step_end_time)
        step_time = time_data[step_mask]
        
        if len(step_time) < 2:
            continue
            
        step_time_norm = (step_time - step_start_time) / (step_end_time - step_start_time)
        
        # Get knee angle for this step
        knee_angle_col = 'knee_angle_l' if 'left' in step_side else 'knee_angle_r'
        if knee_angle_col in coord_values.columns:
            knee_values = coord_values[step_mask][knee_angle_col].values
            # Interpolate to common time grid
            if len(knee_values) > 1:
                interp_knee = np.interp(normalized_time_common, step_time_norm, knee_values)
                knee_angle_trajectories.append(interp_knee)
        
        # Get hip angle for this step
        hip_angle_col = 'hip_flexion_l' if 'left' in step_side else 'hip_flexion_r'
        if hip_angle_col in coord_values.columns:
            hip_values = coord_values[step_mask][hip_angle_col].values
            # Interpolate to common time grid
            if len(hip_values) > 1:
                interp_hip = np.interp(normalized_time_common, step_time_norm, hip_values)
                hip_angle_trajectories.append(interp_hip)
    
    # Calculate mean trajectories
    if knee_angle_trajectories:
        mean_knee = np.mean(knee_angle_trajectories, axis=0)
        std_knee = np.std(knee_angle_trajectories, axis=0)
    else:
        mean_knee = None
        std_knee = None
        
    if hip_angle_trajectories:
        mean_hip = np.mean(hip_angle_trajectories, axis=0)
        std_hip = np.std(hip_angle_trajectories, axis=0)
    else:
        mean_hip = None
        std_hip = None
    
    # Create mean trajectory plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'Mean Trajectories - Steps 1-4\nTrial: {trial_name}', 
                 fontsize=14, fontweight='bold')
    
    # Panel 1: Mean knee flexion angle
    ax = axes[0]
    if mean_knee is not None:
        ax.plot(normalized_time_common, mean_knee, 'b-', linewidth=2.5, label='Mean')
        ax.fill_between(normalized_time_common, mean_knee - std_knee, mean_knee + std_knee, 
                         alpha=0.2, color='blue', label='±1 Std Dev')
    ax.set_xlabel('Normalized Time (0-1)', fontsize=11)
    ax.set_ylabel('Angle (deg)', fontsize=11)
    ax.set_title('Mean Knee Flexion Angle', fontsize=12, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=10)
    
    # Panel 2: Mean hip flexion angle
    ax = axes[1]
    if mean_hip is not None:
        ax.plot(normalized_time_common, mean_hip, 'r-', linewidth=2.5, label='Mean')
        ax.fill_between(normalized_time_common, mean_hip - std_hip, mean_hip + std_hip, 
                         alpha=0.2, color='red', label='±1 Std Dev')
    ax.set_xlabel('Normalized Time (0-1)', fontsize=11)
    ax.set_ylabel('Angle (deg)', fontsize=11)
    ax.set_title('Mean Hip Flexion Angle', fontsize=12, fontweight='bold')
    ax.grid(alpha=0.3)
    ax.legend(fontsize=10)
    
    plt.tight_layout()
    
    # Save mean trajectory plot
    mean_trajectory_path = os.path.join(trial_output_dir, 'step_mean_trajectories_1_to_4.png')
    plt.savefig(mean_trajectory_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Saved mean trajectory plot: {mean_trajectory_path}")
    
    # ========================================================================
    # SAVE SUMMARY STATISTICS
    # ========================================================================
    
    print("\nSaving summary statistics...")
    
    step_durations = np.diff(all_step_times)
    summary_stats = {
        'Total Steps': len(all_step_times),
        'Left Steps': len(left_crossing_times),
        'Right Steps': len(right_crossing_times),
        'Mean Step Duration (s)': np.mean(step_durations),
        'Std Step Duration (s)': np.std(step_durations),
        'Min Step Duration (s)': np.min(step_durations),
        'Max Step Duration (s)': np.max(step_durations),
        'Trial Duration (s)': time_data[-1] - time_data[0],
    }
    
    summary_df = pd.DataFrame(list(summary_stats.items()), columns=['Metric', 'Value'])
    summary_csv_path = os.path.join(trial_output_dir, 'summary_statistics.csv')
    summary_df.to_csv(summary_csv_path, index=False)
    print(f"Summary statistics saved to: {summary_csv_path}")
    
    print("\n" + "="*70)
    print(f"Completed processing trial: {trial_name}")
    print(f"Output directory: {trial_output_dir}")
    print("="*70)

print("\n" + "="*70)
print("ALL TRIALS COMPLETED")
print("="*70)
