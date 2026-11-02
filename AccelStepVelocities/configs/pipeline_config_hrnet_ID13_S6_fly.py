"""Auto-generated HRNet config for subject 13."""
import os

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
FIRST_STRIDE_TIME = 5.002

DATA_DIR = r'/Users/steudelk/Library/CloudStorage/GoogleDrive-steudelk@stanford.edu/Shared drives/Stanford Football'
LOCAL_DIR = r'/Users/steudelk/Documents/Github/opencap-processing'
OUTPUT_ROOT = r'/Users/steudelk/Documents/Github/opencap-processing/AccelStepVelocities'

PATHS = {
    'subject_dir': r'/Users/steudelk/Library/CloudStorage/GoogleDrive-steudelk@stanford.edu/Shared drives/Stanford Football/February_23/subject13',
    'trial_stem': 'ID13_S6_fly',
    'trial_name': 'ID13_S6_fly_LSTM_hip_flexion_adjusted',
    'file_tag': 'ID13_S6_fly_LSTM_hip_flexion_adjusted',
    'openpose_variant': 'mmpose_0.8',
    'model_path': r'/Users/steudelk/Library/CloudStorage/GoogleDrive-steudelk@stanford.edu/Shared drives/Stanford Football/February_23/subject13/OpenSimData/mmpose_0.8/Model/LaiUhlrich2022_scaled.osim',
    'kinematics_input': r'/Users/steudelk/Library/CloudStorage/GoogleDrive-steudelk@stanford.edu/Shared drives/Stanford Football/February_23/subject13/OpenSimData/mmpose_0.8/Kinematics/ID13_S6_fly_LSTM_hip_flexion_adjusted.mot',
    'kinematics_filtered': r'/Users/steudelk/Library/CloudStorage/GoogleDrive-steudelk@stanford.edu/Shared drives/Stanford Football/February_23/subject13/OpenSimData/mmpose_0.8/Kinematics/ID13_S6_fly_LSTM_hip_flexion_adjusted.mot',
    'session_id': r'/Users/steudelk/Documents/Github/opencap-processing/AccelStepVelocities/subject13/ID13_S6_fly',
    'outputs_dir': r'/Users/steudelk/Documents/Github/opencap-processing/AccelStepVelocities/subject13/ID13_S6_fly',
    'shank_angular_velocity_csv': r'/Users/steudelk/Documents/Github/opencap-processing/AccelStepVelocities/subject13/ID13_S6_fly/shank_ang_vel_ID13_S6_fly_LSTM_hip_flexion_adjusted.csv',
    'step_times_left': r'/Users/steudelk/Documents/Github/opencap-processing/AccelStepVelocities/subject13/ID13_S6_fly/step_times_left.csv',
    'step_times_right': r'/Users/steudelk/Documents/Github/opencap-processing/AccelStepVelocities/subject13/ID13_S6_fly/step_times_right.csv',
    'step_times_csv': r'/Users/steudelk/Documents/Github/opencap-processing/AccelStepVelocities/subject13/ID13_S6_fly/step_times.csv',
    'kinematics_file_reed': r'/Users/steudelk/Library/CloudStorage/GoogleDrive-steudelk@stanford.edu/Shared drives/Stanford Football/February_23/subject13/OpenSimData/mmpose_0.8/Kinematics/ID13_S6_fly_LSTM_hip_flexion_adjusted.mot',
    'stride_vel_output_dir': r'/Users/steudelk/Documents/Github/opencap-processing/AccelStepVelocities/subject13/ID13_S6_fly/stride_velocities',
    'mot_file': r'/Users/steudelk/Library/CloudStorage/GoogleDrive-steudelk@stanford.edu/Shared drives/Stanford Football/February_23/subject13/OpenSimData/mmpose_0.8/Kinematics/ID13_S6_fly_LSTM_hip_flexion_adjusted.mot',
    'first_stride_time': 5.002,
}


def print_summary():
    print('=' * 60)
    print('Pipeline Configuration  [HRNet / mmpose_0.8]')
    print('=' * 60)
    print(f'  Subject:        {SUBJECT_NUM}')
    print(f'  Date:           {DATE}')
    print(f'  Session:        {SESSION}')
    print(f'  Trial type:     {TRIAL_TYPE}')
    print(f'  First stride:   {FIRST_STRIDE_TIME} s')
    print(f'  Kin input:      {PATHS["kinematics_input"]}')
    print(f'  Model:          {PATHS["model_path"]}')
    print(f'  Outputs dir:    {PATHS["outputs_dir"]}')
    print('=' * 60)
