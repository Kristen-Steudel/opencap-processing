'''
    ---------------------------------------------------------------------------
    OpenCap processing: example.py
    ---------------------------------------------------------------------------

    Copyright 2022 Stanford University and the Authors
    
    Author(s): Antoine Falisse, Scott Uhlrich
    
    Licensed under the Apache License, Version 2.0 (the "License"); you may not
    use this file except in compliance with the License. You may obtain a copy
    of the License at http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''

import os
import glob
import utilsKinematics
from utilsPlotting import plot_dataframe
import opensim as osim
import pandas as pd
import numpy as np

# Configuration imported from pipeline_config.py (edit once, used by all scripts)
import pipeline_config as cfg
paths = cfg.PATHS
filter_freq = cfg.FILT_FREQ
coord_filter_freq = cfg.COORD_FILTER_FREQ
mtu_length_filter_freq = cfg.MTU_LENGTH_FILTER_FREQ
enable_mtu_filter_diagnostics = False

###########################################################
# %% User inputs.
session_id = os.path.normpath(paths['session_id'])
specific_trial_names = [paths['trial_name']]
print(specific_trial_names)

# Specify where to download the data.
data_folder = os.path.join(session_id)

# %% Prepare data (local or remote).
if os.path.exists(session_id):
    # Running locally — discover session root, trials and model from local folder structure.
    def find_session_root(path):
        path = os.path.abspath(path)
        while True:
            # Check for obvious session markers or OpenSimData folder
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

    # If the user supplied a path that already contains an 'OpenSimData'
    # segment (for example: ...\subject3\OpenSimData\OpenPose_default\3-cameras)
    # then set the session root to the parent directory that contains
    # `OpenSimData` so that later code doesn't append `OpenSimData` twice.
    norm_path = os.path.normpath(session_id)
    parts = norm_path.split(os.path.sep)
    lower_parts = [p.lower() for p in parts]
    if 'opensimdata' in lower_parts:
        idx = lower_parts.index('opensimdata')
        # join parts up to (but not including) the OpenSimData segment
        if idx > 0:
            session_root = os.path.sep.join(parts[:idx])
        else:
            session_root = os.path.sep.join(parts[:1])
        session_root = session_root.rstrip(os.path.sep)
    else:
        session_root = find_session_root(session_id)
        if session_root is None:
            raise FileNotFoundError(f"Could not find session root for path: {session_id}")

    # Use session_root as the session directory passed to utilsKinematics
    data_folder = session_root

    # Search for .mot files under likely kinematics folders
    mot_files = sorted(glob.glob(os.path.join(session_root, 'OpenSimData', 'Kinematics', '*.mot')))
    if not mot_files:
        # fallback: search recursively for any .mot under the session root
        mot_files = sorted(glob.glob(os.path.join(session_root, '**', '*.mot'), recursive=True))

    if len(mot_files) == 0:
        raise FileNotFoundError(f"No .mot files found under session root: {session_root}")

    trial_names = [os.path.splitext(os.path.basename(m))[0] for m in mot_files]
    if specific_trial_names is not None:
        trial_names = [t for t in trial_names if t in specific_trial_names]

    # Find model (.osim) under the correct OpenPose variant folder.
    model_files = sorted(glob.glob(os.path.join(
        session_root, 'OpenSimData', paths['openpose_variant'],
        '3-cameras', 'Model', '*scaled.osim')))
    if not model_files:
        raise FileNotFoundError(
            f"No scaled .osim model found under "
            f"OpenSimData/{paths['openpose_variant']}/3-cameras/Model/\n"
            f"Check OPENPOSE_VARIANT in pipeline_config.py.")
    # Pass the full absolute path so utilsKinematics uses it directly
    # instead of doing a recursive glob that could pick the wrong variant.
    model_path = model_files[0]
    modelName = model_path  # full path; utilsKinematics detects & uses directly
else:
    raise FileNotFoundError(
        f"Local session path does not exist: {session_id}\n"
        f"Check subject_num, date, and folder structure."
    )

# +++ ADD THIS LINE TO DEBUG +++
print(f"--- Using model: {modelName}.osim ---") 

# Get neutral MTU lengths for normalization.
def get_neutral_mtu_lengths(model_file_path):
    model = osim.Model(model_file_path)
    model.initSystem()
    neutral_mtu = {}
    muscles = model.getMuscles()
    for i in range(muscles.getSize()):
        muscle = muscles.get(i)
        neutral_mtu[muscle.getName()] = (
            muscle.getOptimalFiberLength() + muscle.getTendonSlackLength())
    return neutral_mtu

neutral_mtu_lengths = get_neutral_mtu_lengths(model_path)

# %% Process data.
kinematics, coordinates, muscle_tendon_lengths, moment_arms, center_of_mass = {}, {}, {}, {}, {}
coordinates['values'], coordinates['speeds'], coordinates['accelerations'] = {}, {}, {}
center_of_mass['values'], center_of_mass['speeds'], center_of_mass['accelerations'] = {}, {}, {}
angular_velocity = {}
muscle_tendon_velocities = {}
muscle_tendon_velocities_opensim = {}
muscle_tendon_velocity_comparison = {}
normalized_muscle_tendon_lengths = {}
muscle_tendon_lengths_raw = {}
muscle_tendon_lengths_filter_delta = {}


def compute_fft_band_power_ratio(time_vec, signal_vec, cutoff_hz):
    """Return fraction of spectral power above cutoff_hz."""
    dt = np.mean(np.diff(time_vec))
    fs = 1.0 / dt
    demeaned = signal_vec - np.mean(signal_vec)
    freqs = np.fft.rfftfreq(len(demeaned), d=dt)
    power = np.abs(np.fft.rfft(demeaned)) ** 2
    total_power = np.sum(power)
    if total_power <= 0:
        return 0.0
    high_power = np.sum(power[freqs > cutoff_hz])
    return high_power / total_power

for trial_name in trial_names:
    # Create object from class kinematics.
    kinematics[trial_name] = utilsKinematics.kinematics(
        data_folder,
        trial_name,
        modelName=modelName,
        lowpass_cutoff_frequency_for_coordinate_values=coord_filter_freq)
    print(f"Loaded motion file: {kinematics[trial_name].motionPath}")
    print(f"Loaded model file:  {kinematics[trial_name].modelPath}")
    print(f"Motion rows:        {kinematics[trial_name].table.getNumRows()}")
    
    # Get coordinate values, speeds, and accelerations.
    coordinates['values'][trial_name] = kinematics[trial_name].get_coordinate_values(in_degrees=True) # already filtered
    coordinates['speeds'][trial_name] = kinematics[trial_name].get_coordinate_speeds(
        in_degrees=True, lowpass_cutoff_frequency=coord_filter_freq)
    coordinates['accelerations'][trial_name] = kinematics[trial_name].get_coordinate_accelerations(
        in_degrees=True, lowpass_cutoff_frequency=coord_filter_freq)
    
    # Get muscle-tendon lengths and moment arms.
    muscle_tendon_lengths_raw[trial_name] = (
        kinematics[trial_name].get_muscle_tendon_lengths(
            lowpass_cutoff_frequency=-1))
    muscle_tendon_lengths[trial_name] = (
        kinematics[trial_name].get_muscle_tendon_lengths(
            lowpass_cutoff_frequency=mtu_length_filter_freq))
    
    # Optional filtering diagnostics for bflh_r.
    mtu_raw = muscle_tendon_lengths_raw[trial_name]
    mtu_filt = muscle_tendon_lengths[trial_name]
    if enable_mtu_filter_diagnostics:
        rms_diff_bflh_r = np.sqrt(
            np.mean((mtu_filt['bflh_r'] - mtu_raw['bflh_r']) ** 2))
        raw_high_power_ratio = compute_fft_band_power_ratio(
            mtu_raw['time'].to_numpy(), mtu_raw['bflh_r'].to_numpy(), mtu_length_filter_freq)
        filt_high_power_ratio = compute_fft_band_power_ratio(
            mtu_filt['time'].to_numpy(), mtu_filt['bflh_r'].to_numpy(), mtu_length_filter_freq)
        print(f"RMS diff bflh_r (filtered - raw): {rms_diff_bflh_r:.8f}")
        print(
            f"bflh_r power above {mtu_length_filter_freq} Hz (raw): {100 * raw_high_power_ratio:.3f}%")
        print(
            f"bflh_r power above {mtu_length_filter_freq} Hz (filtered): {100 * filt_high_power_ratio:.3f}%")

    delta_df_dict = {'time': mtu_raw['time']}
    for col in mtu_raw.columns:
        if col == 'time' or col not in mtu_filt.columns:
            continue
        delta_df_dict[f'{col}_raw'] = mtu_raw[col]
        delta_df_dict[f'{col}_filtered'] = mtu_filt[col]
        delta_df_dict[f'{col}_delta_filtered_minus_raw'] = mtu_filt[col] - mtu_raw[col]
    delta_df = pd.DataFrame(delta_df_dict)
    muscle_tendon_lengths_filter_delta[trial_name] = delta_df
    # moment_arms[trial_name] = kinematics[trial_name].get_moment_arms()
    muscle_tendon_velocities_opensim[trial_name] = (
        kinematics[trial_name].get_muscle_tendon_velocities(
            lowpass_cutoff_frequency=-1))
    muscle_tendon_velocities[trial_name] = (
        kinematics[trial_name].get_muscle_tendon_velocity_spline_approach(
            lowpass_cutoff_frequency_for_lengths=mtu_length_filter_freq,
            lowpass_cutoff_frequency_for_velocities=-1)) # Currently skipping the filtering with -1
    comparison_df_dict = {
        'time': muscle_tendon_velocities[trial_name]['time']
    }
    for col in muscle_tendon_velocities[trial_name].columns:
        if col == 'time' or col not in muscle_tendon_velocities_opensim[trial_name].columns:
            continue
        comparison_df_dict[f'{col}_spline'] = muscle_tendon_velocities[trial_name][col]
        comparison_df_dict[f'{col}_opensim'] = muscle_tendon_velocities_opensim[trial_name][col]
        comparison_df_dict[f'{col}_diff_spline_minus_opensim'] = (
            muscle_tendon_velocities[trial_name][col] -
            muscle_tendon_velocities_opensim[trial_name][col]
        )
    comparison_df = pd.DataFrame(comparison_df_dict)
    muscle_tendon_velocity_comparison[trial_name] = comparison_df
    
    # Get center of mass values, speeds, and accelerations.
    center_of_mass['values'][trial_name] = kinematics[trial_name].get_center_of_mass_values(
        lowpass_cutoff_frequency=coord_filter_freq)
    center_of_mass['speeds'][trial_name] = kinematics[trial_name].get_center_of_mass_speeds(
        lowpass_cutoff_frequency=coord_filter_freq)
    center_of_mass['accelerations'][trial_name] = kinematics[trial_name].get_center_of_mass_accelerations(
        lowpass_cutoff_frequency=coord_filter_freq)
    
        # Get shank angular velocity (expressed in body frame, with 10 Hz lowpass filter)
    # Specify both left and right shanks
    angular_velocity[trial_name] = kinematics[trial_name].get_body_angular_velocity(
        body_names=['tibia_l', 'tibia_r'],  # Both shanks
        lowpass_cutoff_frequency=3, #  2 Hz cutoff frequency for angular velocity for detecting steps
        expressed_in='ground'  # Options: 'body' or 'ground'
    )

    # Normalize muscle-tendon lengths by neutral MTU lengths.
    normalized_df = muscle_tendon_lengths[trial_name].copy()
    for muscle_name in normalized_df.columns:
        if muscle_name != 'time' and muscle_name in neutral_mtu_lengths:
            normalized_df[muscle_name] = (
                normalized_df[muscle_name] / neutral_mtu_lengths[muscle_name])
    normalized_muscle_tendon_lengths[trial_name] = normalized_df

# Print neutral lengths for biceps femoris long head.
print("\nNeutral MTU Lengths for Biceps Femoris Long Head:")
for muscle_name, length in neutral_mtu_lengths.items():
    if 'bflh' in muscle_name.lower():
        print(f"{muscle_name}: {length:.4f} m")
    
# %% Save CSVs and plots -- short filenames use file_tag from pipeline config
output_csv_dir = paths['outputs_dir']
os.makedirs(output_csv_dir, exist_ok=True)
tag = paths['file_tag']

output_csv_path = os.path.join(output_csv_dir, f'coord_speeds_{tag}.csv')
coordinates['speeds'][trial_names[0]].to_csv(output_csv_path)

output_csv_path = os.path.join(output_csv_dir, f'shank_ang_vel_{tag}.csv')
angular_velocity[trial_names[0]].to_csv(output_csv_path)

output_csv_path = os.path.join(output_csv_dir, f'mtu_lengths_{tag}.csv')
muscle_tendon_lengths[trial_names[0]].to_csv(output_csv_path)

output_csv_path = os.path.join(output_csv_dir, f'mtu_lengths_raw_{tag}.csv')
muscle_tendon_lengths_raw[trial_names[0]].to_csv(output_csv_path)

output_csv_path = os.path.join(output_csv_dir, f'mtu_lengths_delta_{tag}.csv')
muscle_tendon_lengths_filter_delta[trial_names[0]].to_csv(output_csv_path, index=False)

output_csv_path = os.path.join(output_csv_dir, f'mtu_vel_spline_{tag}.csv')
muscle_tendon_velocities[trial_names[0]].to_csv(output_csv_path)

output_csv_path = os.path.join(output_csv_dir, f'mtu_vel_opensim_{tag}.csv')
muscle_tendon_velocities_opensim[trial_names[0]].to_csv(output_csv_path)

output_csv_path = os.path.join(output_csv_dir, f'mtu_vel_comparison_{tag}.csv')
muscle_tendon_velocity_comparison[trial_names[0]].to_csv(output_csv_path, index=False)

output_csv_path = os.path.join(output_csv_dir, f'norm_mtu_lengths_{tag}.csv')
normalized_muscle_tendon_lengths[trial_names[0]].to_csv(output_csv_path)

output_csv_path = os.path.join(output_csv_dir, f'norm_bflh_length_{tag}.csv')
bflh_columns = [
    col for col in normalized_muscle_tendon_lengths[trial_names[0]].columns
    if 'bflh' in col.lower()]
columns_to_save = ['time'] + bflh_columns
normalized_muscle_tendon_lengths[trial_names[0]][columns_to_save].to_csv(output_csv_path)

# %% Plot: examples.
# Plot all coordinate values against time.
plot_dataframe(dataframes = [coordinates['values'][trial_names[0]]],
               xlabel = 'Time (s)',
               ylabel = 'Pos (m or deg)',
               title = 'Coordinate values',
               labels = [trial_names[0]],
               save_path = os.path.join(output_csv_dir, f'coord_values_{tag}.png'))

# Plot selected coordinate speeds against time.
plot_dataframe(dataframes = [coordinates['speeds'][trial_names[0]]],
               y = ['hip_flexion_l', 'knee_angle_l'],
               xlabel = 'Time (s)',
               ylabel = 'Vel (deg/s)',
               title = 'Coordinate speeds',
               labels = [trial_names[0]],
               save_path = os.path.join(output_csv_dir, f'coord_speeds_{tag}.png'))

# Plot knee flexion accelerations against hip flexion accelerations.
plot_dataframe(dataframes = [coordinates['accelerations'][trial_names[0]]],
               x = 'knee_angle_l',
               y = ['hip_flexion_l'],
               xlabel = 'Knee angle acceleration (deg/s^2)',
               ylabel = 'Hip flexion acceleration (deg/s^2)',
               labels = [trial_names[0]],
               save_path = os.path.join(output_csv_dir, f'coord_accel_{tag}.png'))

# Plot center of mass accelerations.
plot_dataframe(dataframes = [center_of_mass['accelerations'][trial_names[0]]],
               xlabel = 'Time (s)',
               title = 'Center of mass accelerations',
               labels = [trial_names[0]],
               save_path = os.path.join(output_csv_dir, f'com_accel_{tag}.png'))

# Plot muscle-tendon lengths against time.
plot_dataframe(dataframes = [muscle_tendon_lengths[trial_names[0]]],
               y = ['bflh_r', 'gasmed_r', 'recfem_r'],
               xlabel = 'Time (s)',
               title = 'Muscle-tendon lengths',
               labels = [trial_names[0]],
               save_path = os.path.join(output_csv_dir, f'mtu_lengths_{tag}.png'))

# Plot normalized muscle-tendon lengths against time.
plot_dataframe(dataframes = [normalized_muscle_tendon_lengths[trial_names[0]]],
               y = ['bflh_r', 'gasmed_r', 'recfem_r'],
               xlabel = 'Time (s)',
               ylabel = 'Normalized Length',
               title = 'Normalized Muscle-tendon lengths',
               labels = [trial_names[0]],
               save_path = os.path.join(output_csv_dir, f'norm_mtu_lengths_{tag}.png'))
