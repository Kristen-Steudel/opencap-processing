"""
HRNet / mmpose_0.8 pipeline configuration.

Kinematics are read from Google Drive (February_23).
All outputs are written locally under AccelStepVelocities/ so Drive is never modified.

SUBJECT_NUM is overwritten by run_pipeline_hrnet.py for each subject.
"""

import os

# =====================================================================
# SUBJECT PARAMETERS  --  run_pipeline_hrnet.py sets SUBJECT_NUM per trial
# =====================================================================
SUBJECT_NUM = 13
DATE = 'February_23'
SESSION = '6'
TRIAL_TYPE = 'fly'
POSE_VARIANT = 'mmpose_0.8'
KIN_SUFFIX = '_LSTM_hip_flexion_adjusted'
FILT_FREQ = 10
COORD_FILTER_FREQ = 10
MTU_LENGTH_FILTER_FREQ = -1
DIST_THRESHOLD = -12.0
LIT_SPEEDS = ['7p0']

# =====================================================================
# BASE DIRECTORIES
# =====================================================================
DATA_DIR = (
    '/Users/steudelk/Library/CloudStorage/GoogleDrive-steudelk@stanford.edu'
    '/Shared drives/Stanford Football'
)
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_ROOT = os.path.join(LOCAL_DIR, 'AccelStepVelocities')


def build_paths():
    """Return paths for HRNet fly kinematics + local AccelStepVelocities outputs."""
    subject_id = f'subject{SUBJECT_NUM}'
    subject_dir = os.path.join(DATA_DIR, DATE, subject_id)
    trial_stem = f'ID{SUBJECT_NUM}_S{SESSION}_{TRIAL_TYPE}'
    file_tag = f'{trial_stem}{KIN_SUFFIX}'
    trial_name = file_tag  # matches .mot basename without extension

    kinematics_input = os.path.join(
        subject_dir, 'OpenSimData', POSE_VARIANT, 'Kinematics',
        f'{file_tag}.mot')

    # Already-adjusted kinematics — no filter rewrite to Drive
    kinematics_filtered = kinematics_input

    model_path = os.path.join(
        subject_dir, 'OpenSimData', POSE_VARIANT, 'Model',
        'LaiUhlrich2022_scaled.osim')

    # All writes go under the local AccelStepVelocities folder
    outputs_dir = os.path.join(OUTPUT_ROOT, subject_id, trial_stem)
    session_id = outputs_dir

    shank_angular_velocity_csv = os.path.join(
        outputs_dir, f'shank_ang_vel_{file_tag}.csv')
    step_times_left = os.path.join(outputs_dir, 'step_times_left.csv')
    step_times_right = os.path.join(outputs_dir, 'step_times_right.csv')
    step_times_csv = os.path.join(outputs_dir, 'step_times.csv')

    stride_vel_output_dir = os.path.join(outputs_dir, 'stride_velocities')

    return {
        'subject_dir': subject_dir,
        'trial_stem': trial_stem,
        'trial_name': trial_name,
        'file_tag': file_tag,
        'openpose_variant': POSE_VARIANT,
        'model_path': model_path,
        'kinematics_input': kinematics_input,
        'kinematics_filtered': kinematics_filtered,
        'session_id': session_id,
        'outputs_dir': outputs_dir,
        'shank_angular_velocity_csv': shank_angular_velocity_csv,
        'step_times_left': step_times_left,
        'step_times_right': step_times_right,
        'step_times_csv': step_times_csv,
        'kinematics_file_reed': kinematics_filtered,
        'stride_vel_output_dir': stride_vel_output_dir,
        'mot_file': kinematics_filtered,
    }


PATHS = build_paths()


def print_summary():
    print('=' * 60)
    print('Pipeline Configuration  [HRNet / mmpose_0.8]')
    print('=' * 60)
    print(f'  Subject:        {SUBJECT_NUM}')
    print(f'  Date:           {DATE}')
    print(f'  Session:        {SESSION}')
    print(f'  Trial type:     {TRIAL_TYPE}')
    print(f'  Pose variant:   {POSE_VARIANT}')
    print(f'  Dist threshold: {DIST_THRESHOLD} m')
    print(f'  Kin input:      {PATHS["kinematics_input"]}')
    print(f'  Model:          {PATHS["model_path"]}')
    print(f'  Outputs dir:    {PATHS["outputs_dir"]}')
    print('=' * 60)
