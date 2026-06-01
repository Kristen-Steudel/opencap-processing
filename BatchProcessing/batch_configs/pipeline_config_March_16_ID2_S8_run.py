"""
Auto-generated batch config
  Date:    March_16
  Subject: 2
  Session: 8
  Trial:   run
"""

import os

SUBJECT_NUM = 2
DATE = 'March_16'
SESSION = '8'
TRIAL_TYPE = 'run'
OPENPOSE_VARIANT = 'OpenPose_1x736_2scales'
FILT_FREQ = 10
COORD_FILTER_FREQ = 10
MTU_LENGTH_FILTER_FREQ = -1
DIST_THRESHOLD = -12.0
LIT_SPEEDS = ['7p0']

DATA_DIR = r'G:\Shared drives\Stanford Football'
LIT_DIR = os.path.join(DATA_DIR, 'LiteratureData')
LOCAL_DIR = r'C:\Users\steudelkri\Documents\opencap-processing'


def build_paths():
    subject_id = f'subject{SUBJECT_NUM}'
    subject_dir = os.path.join(DATA_DIR, DATE, subject_id)
    trial_stem = f'ID{SUBJECT_NUM}_S{SESSION}_{TRIAL_TYPE}'
    file_tag = trial_stem

    KIN_SUBFOLDER = 'Kinematics'
    KIN_SUFFIX = '_LSTM'
    kinematics_input = os.path.join(
        subject_dir, 'OpenSimData', OPENPOSE_VARIANT, '3-cameras',
        KIN_SUBFOLDER, f'{trial_stem}{KIN_SUFFIX}.mot')

    kinematics_filtered = os.path.join(
        subject_dir, 'Cleaned_Kinematics',
        f'{trial_stem}_filtered_{FILT_FREQ}Hz.mot')

    session_id = os.path.join(subject_dir, 'Cleaned_Kinematics')
    trial_name = f'{trial_stem}_filtered_{FILT_FREQ}Hz'
    outputs_dir = os.path.join(subject_dir, 'CleanedKinematics', 'Outputs')

    shank_angular_velocity_csv = os.path.join(
        outputs_dir, f'shank_ang_vel_{file_tag}.csv')
    step_times_left = os.path.join(outputs_dir, 'step_times_left.csv')
    step_times_right = os.path.join(outputs_dir, 'step_times_right.csv')

    normalized_bflh_csv = os.path.join(
        outputs_dir, f'norm_bflh_length_{file_tag}.csv')
    lit_lengths_file = os.path.join(
        LOCAL_DIR, 'experiments', 'LiteratureData', 'BingYuBFLHLengths.csv')
    lit_velocities_file = os.path.join(
        LOCAL_DIR, 'experiments', 'LiteratureData', 'BingYuBFLHVelocities.csv')
    lit_bflh_nordsprint = os.path.join(
        LIT_DIR, 'NordSprintAllKinematics', 'BicepsFemoris_All_Combined.csv')
    lit_hamstrings_combined = os.path.join(
        LIT_DIR, 'NordSprintAllKinematics', 'AllHamstrings_Combined.csv')

    mot_file = kinematics_filtered
    lit_file_nordsprint = os.path.join(
        LIT_DIR, 'NordSprintKinematics', 'All_Kinematics_Combined.csv')
    lit_file_nordsprint_all = os.path.join(
        LIT_DIR, 'NordSprintAllKinematics', 'All_Kinematics_Combined.csv')
    hamner_dir = os.path.join(LIT_DIR, 'SamHamnerKinematics')

    step_times_csv = os.path.join(outputs_dir, 'step_times.csv')
    kinematics_file_reed = kinematics_filtered
    stride_vel_output_dir = os.path.join(
        subject_dir, 'Kinematics', 'Outputs', 'stride_velocities')

    return {
        'subject_dir': subject_dir,
        'trial_stem': trial_stem,
        'trial_name': trial_name,
        'file_tag': file_tag,
        'openpose_variant': OPENPOSE_VARIANT,
        'kinematics_input': kinematics_input,
        'kinematics_filtered': kinematics_filtered,
        'session_id': session_id,
        'outputs_dir': outputs_dir,
        'shank_angular_velocity_csv': shank_angular_velocity_csv,
        'step_times_left': step_times_left,
        'step_times_right': step_times_right,
        'normalized_bflh_csv': normalized_bflh_csv,
        'lit_lengths_file': lit_lengths_file,
        'lit_velocities_file': lit_velocities_file,
        'lit_bflh_nordsprint': lit_bflh_nordsprint,
        'lit_hamstrings_combined': lit_hamstrings_combined,
        'mot_file': mot_file,
        'lit_file_nordsprint': lit_file_nordsprint,
        'lit_file_nordsprint_all': lit_file_nordsprint_all,
        'hamner_dir': hamner_dir,
        'step_times_csv': step_times_csv,
        'kinematics_file_reed': kinematics_file_reed,
        'stride_vel_output_dir': stride_vel_output_dir,
        'peak_bflh_angles_csv': os.path.join(
            outputs_dir, f'peak_bflh_angles_{file_tag}.csv'),
    }


PATHS = build_paths()


def print_summary():
    print('=' * 60)
    print('Pipeline Configuration  [batch]')
    print('=' * 60)
    print(f'  Subject:        {SUBJECT_NUM}')
    print(f'  Date:           {DATE}')
    print(f'  Session:        {SESSION}')
    print(f'  Trial type:     {TRIAL_TYPE}')
    print(f'  OpenPose:       {OPENPOSE_VARIANT}')
    print(f'  Filter freq:    {FILT_FREQ} Hz')
    print(f'  Kin input:      {PATHS["kinematics_input"]}')
    print(f'  Outputs dir:    {PATHS["outputs_dir"]}')
    print('=' * 60)
