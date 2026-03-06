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
from utils import download_kinematics, get_model_name_from_metadata
from utilsPlotting import plot_dataframe
import opensim as osim

# Requirements to Change for each run
#########################################################################
subject_num = 2
date = 'March_2'
session_num = '7'
type = 'sprint'
##########################################################################




# %% User inputs.
# Specify session id; see end of url in app.opencap.ai/session/<session_id>.
#session_id = "4d5c3eb1-1a59-4ea1-9178-d3634610561c"
session_id = os.path.normpath(f'G:\\Shared drives\\Stanford Football\\{date}\\subject{subject_num}\\OpenSimData\\OpenPose_default\\3-cameras')


# Specify trial names in a list; use None to process all trials in a session.
specific_trial_names = [f'ID{subject_num}_S{session_num}_{type}_LSTM_filtered'] #'ACCEL_LSTM', 'DECEL_LSTM']

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

    # Find model (.osim) under OpenSimData/Model or anywhere under session
    model_files = sorted(glob.glob(os.path.join(session_root, 'OpenSimData', 'Model', '*.osim')))
    if not model_files:
        model_files = sorted(glob.glob(os.path.join(session_root, '**', '*.osim'), recursive=True))

    if model_files:
        # Prefer _scaled models over generic ones
        scaled_models = [m for m in model_files if '_scaled' in m]
        if scaled_models:
            modelName = os.path.splitext(os.path.basename(scaled_models[0]))[0]
            model_path = scaled_models[0]
        else:
            modelName = os.path.splitext(os.path.basename(model_files[0]))[0]
            model_path = model_files[0]
    else:
        # try to read from metadata
        try:
            modelName = get_model_name_from_metadata(session_root).replace('.osim', '')
            model_path = os.path.join(session_root, 'OpenSimData', 'Model', modelName + '.osim')
        except Exception:
            modelName = None
            model_path = None
else:   
    # Fallback: download from cloud as before
    trial_names, modelName = download_kinematics(session_id, folder=data_folder, trialNames=specific_trial_names)
    model_path = os.path.join(data_folder, 'OpenSimData', 'Model', modelName + '.osim')

# Get the neutral MTU lengths from the model for normalization
def get_neutral_mtu_lengths(model_path):
    """
    Get the neutral (resting) muscle-tendon unit lengths from an OpenSim model.
    This is calculated as optimal_fiber_length + tendon_slack_length.
    
    Parameters
    ----------
    model_path : str
        Path to the OpenSim model file (.osim)
    
    Returns
    -------
    dict
        Dictionary with muscle names as keys and neutral MTU lengths as values
    """
    model = osim.Model(model_path)
    state = model.initSystem()
    neutral_mtu_lengths = {}
    muscles = model.getMuscles()
    for i in range(muscles.getSize()):
        muscle = muscles.get(i)
        neutral_mtu_lengths[muscle.getName()] = muscle.getOptimalFiberLength() + muscle.getTendonSlackLength()
    return neutral_mtu_lengths

neutral_mtu_lengths = get_neutral_mtu_lengths(model_path)

# %% Process data.
kinematics, coordinates, muscle_tendon_lengths, moment_arms, center_of_mass = {}, {}, {}, {}, {}
coordinates['values'], coordinates['speeds'], coordinates['accelerations'] = {}, {}, {}
center_of_mass['values'], center_of_mass['speeds'], center_of_mass['accelerations'] = {}, {}, {}
angular_velocity = {}

for trial_name in trial_names:
    # Create object from class kinematics.
    kinematics[trial_name] = utilsKinematics.kinematics(data_folder, trial_name, modelName=modelName, lowpass_cutoff_frequency_for_coordinate_values=10)

    # Get coordinate values, speeds, and accelerations.
    coordinates['values'][trial_name] = kinematics[trial_name].get_coordinate_values(in_degrees=True) # already filtered
    coordinates['speeds'][trial_name] = kinematics[trial_name].get_coordinate_speeds(in_degrees=True, lowpass_cutoff_frequency=10)
    coordinates['accelerations'][trial_name] = kinematics[trial_name].get_coordinate_accelerations(in_degrees=True, lowpass_cutoff_frequency=10)
    
    # Get muscle-tendon lengths and moment arms.
    muscle_tendon_lengths[trial_name] = kinematics[trial_name].get_muscle_tendon_lengths()
    # moment_arms[trial_name] = kinematics[trial_name].get_moment_arms()
    muscle_tendon_velocities = kinematics[trial_name].get_muscle_tendon_velocities(lowpass_cutoff_frequency=5)

    # Get center of mass values, speeds, and accelerations.
    center_of_mass['values'][trial_name] = kinematics[trial_name].get_center_of_mass_values(lowpass_cutoff_frequency=10)
    center_of_mass['speeds'][trial_name] = kinematics[trial_name].get_center_of_mass_speeds(lowpass_cutoff_frequency=10)
    center_of_mass['accelerations'][trial_name] = kinematics[trial_name].get_center_of_mass_accelerations(lowpass_cutoff_frequency=10)
    
    # Get shank angular velocity (expressed in body frame, with 10 Hz lowpass filter)
    # Specify both left and right shanks
    angular_velocity[trial_name] = kinematics[trial_name].get_body_angular_velocity(
        body_names=['tibia_l', 'tibia_r'],  # Both shanks
        lowpass_cutoff_frequency=2, #  2 Hz cutoff frequency for angular velocity for detecting steps
        expressed_in='ground'  # Options: 'body' or 'ground'
    )

# %% Normalize muscle-tendon lengths
normalized_muscle_tendon_lengths = {}
for trial_name in trial_names:
    # Create a normalized dataframe
    normalized_df = muscle_tendon_lengths[trial_name].copy()
    
    # Normalize each muscle column by its neutral length
    for muscle_name in normalized_df.columns:
        if muscle_name != 'time' and muscle_name in neutral_mtu_lengths:
            normalized_df[muscle_name] = normalized_df[muscle_name] / neutral_mtu_lengths[muscle_name]
    
    normalized_muscle_tendon_lengths[trial_name] = normalized_df



# %% Print neutral lengths for biceps femoris long head
print("\nNeutral MTU Lengths for Biceps Femoris Long Head:")
for muscle_name, length in neutral_mtu_lengths.items():
    if 'bflh' in muscle_name.lower():
        print(f"{muscle_name}: {length:.4f} m")

# %% Save outputs
output_csv_dir = os.path.join(data_folder, 'Kinematics', 'Outputs')
os.makedirs(output_csv_dir, exist_ok=True)

# Save coordinate speeds
output_csv_path = os.path.join(output_csv_dir, 'coordinate_speeds_{}.csv'.format(trial_names[0]))
coordinates['speeds'][trial_names[0]].to_csv(output_csv_path)

# Save center of mass speeds
output_csv_path = os.path.join(output_csv_dir, 'center_of_mass_speeds_{}.csv'.format(trial_names[0]))
center_of_mass['speeds'][trial_names[0]].to_csv(output_csv_path)

# Save shank angular velocity
output_csv_path = os.path.join(output_csv_dir, 'shank_angular_velocity_{}.csv'.format(trial_names[0]))
angular_velocity[trial_names[0]].to_csv(output_csv_path)

# Save muscle-tendon lengths (original)
output_csv_path = os.path.join(output_csv_dir, 'muscle_tendon_lengths_{}.csv'.format(trial_names[0]))
muscle_tendon_lengths[trial_names[0]].to_csv(output_csv_path)

# Save muscle-tendon velocities
output_csv_path = os.path.join(output_csv_dir, 'muscle_tendon_velocities_{}.csv'.format(trial_names[0]))
muscle_tendon_velocities.to_csv(output_csv_path) 

# Save normalized muscle-tendon lengths (all muscles)
output_csv_path = os.path.join(output_csv_dir, 'normalized_muscle_tendon_lengths_{}.csv'.format(trial_names[0]))
normalized_muscle_tendon_lengths[trial_names[0]].to_csv(output_csv_path)

# Save normalized biceps femoris long head length only
output_csv_path_bflh = os.path.join(output_csv_dir, 'normalized_bflh_length_{}.csv'.format(trial_names[0]))
bflh_columns = [col for col in normalized_muscle_tendon_lengths[trial_names[0]].columns if 'bflh' in col.lower()]
columns_to_save = ['time'] + bflh_columns
normalized_muscle_tendon_lengths[trial_names[0]][columns_to_save].to_csv(output_csv_path_bflh)


# %% Plot: examples.
# Plot all coordinate values against time.
plot_dataframe(dataframes = [coordinates['values'][trial_names[0]]],
               xlabel = 'Time (s)',
               ylabel = 'Pos (m or deg)',
               title = 'Coordinate values',
               labels = [trial_names[0]],
               save_path = os.path.join(output_csv_dir, 'coordinate_values_{}.png'.format(trial_names[0])))

# Plot selected coordinate speeds against time.
plot_dataframe(dataframes = [coordinates['speeds'][trial_names[0]]],
               y = ['hip_flexion_l', 'knee_angle_l'],
               xlabel = 'Time (s)',
               ylabel = 'Vel (deg/s)',
               title = 'Coordinate speeds',
               labels = [trial_names[0]],
               save_path = os.path.join(output_csv_dir, 'coordinate_speeds_{}.png'.format(trial_names[0])))

# Plot knee flexion accelerations against hip flexion accelerations.
plot_dataframe(dataframes = [coordinates['accelerations'][trial_names[0]]],
               x = 'knee_angle_l',
               y = ['hip_flexion_l'],
               xlabel = 'Knee angle acceleration (deg/s^2)',
               ylabel = 'Hip flexion acceleration (deg/s^2)',
               labels = [trial_names[0]],
               save_path = os.path.join(output_csv_dir, 'coordinate_accelerations_{}.png'.format(trial_names[0])))

# Plot center of mass accelerations.
plot_dataframe(dataframes = [center_of_mass['accelerations'][trial_names[0]]],
               xlabel = 'Time (s)',
               title = 'Center of mass accelerations',
               labels = [trial_names[0]],
               save_path = os.path.join(output_csv_dir, 'center_of_mass_accelerations_{}.png'.format(trial_names[0])))

# Plot muscle-tendon lengths against time (original).
plot_dataframe(dataframes = [muscle_tendon_lengths[trial_names[0]]],
               y = ['bflh_r', 'gasmed_r', 'recfem_r'],
               xlabel = 'Time (s)',
               ylabel = 'Length (m)',
               title = 'Muscle-tendon lengths',
               labels = [trial_names[0]],
               save_path = os.path.join(output_csv_dir, 'muscle_tendon_lengths_{}.png'.format(trial_names[0])))

# Plot normalized muscle-tendon lengths
plot_dataframe(dataframes = [normalized_muscle_tendon_lengths[trial_names[0]]],
               y = ['bflh_r', 'gasmed_r', 'recfem_r'],
               xlabel = 'Time (s)',
               ylabel = 'Normalized Length',
               title = 'Normalized Muscle-tendon lengths',
               labels = [trial_names[0]],
               save_path = os.path.join(output_csv_dir, 'normalized_muscle_tendon_lengths_{}.png'.format(trial_names[0])))