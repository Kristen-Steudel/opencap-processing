"""
pipeline_config_Sony_sprint_trimmed.py

Sony cameras (OpenPose 1x736_2scales) — trial: sprint_trimmed
Kinematics: subject1/OpenSimData/OpenPose_1x736_2scales/3-cameras/Kinematics/sprint_trimmed_LSTM.mot
Model:      subject1/OpenSimData/OpenPose_1x736_2scales/3-cameras/Model/LaiUhlrich2022_scaled.osim
"""

import os

# =====================================================================
# SUBJECT PARAMETERS
# =====================================================================
SUBJECT_NUM = 1
DATE        = ''
SESSION     = ''
TRIAL_TYPE  = 'sprint_trimmed'              # → sprint_trimmed_LSTM.mot
OPENPOSE_VARIANT = 'OpenPose_1x736_2scales'

TRIAL_LABEL = 'Sony / OpenPose 1x736'

FILT_FREQ              = 10
COORD_FILTER_FREQ      = 10
MTU_LENGTH_FILTER_FREQ = -1

DIST_THRESHOLD = -12.0
LIT_SPEEDS     = ['7p0']

# =====================================================================
# BASE DIRECTORIES
# =====================================================================
DATA_DIR  = r'G:\Shared drives\Sony Camera Testing'
LIT_DIR   = r'G:\Shared drives\Stanford Football\LiteratureData'
LOCAL_DIR = r'C:\Users\steudelkri\Documents\opencap-processing'

# =====================================================================
# DERIVED PATHS
# =====================================================================

def build_paths():
    subject_id  = f'subject{SUBJECT_NUM}'
    subject_dir = os.path.join(DATA_DIR, subject_id)

    trial_stem = TRIAL_TYPE                               # 'sprint_trimmed'
    file_tag   = f'sub{SUBJECT_NUM}_{TRIAL_TYPE}_sony'   # 'sub1_sprint_trimmed_sony'

    KIN_SUBFOLDER = 'Kinematics'
    KIN_SUFFIX    = '_LSTM'
    kinematics_input = os.path.join(
        subject_dir, 'OpenSimData', OPENPOSE_VARIANT, '3-cameras',
        KIN_SUBFOLDER, f'{trial_stem}{KIN_SUFFIX}.mot')

    kinematics_filtered = os.path.join(
        subject_dir, 'Cleaned_Kinematics',
        f'{trial_stem}_filtered_{FILT_FREQ}Hz.mot')

    session_id  = os.path.join(subject_dir, 'Cleaned_Kinematics')
    trial_name  = f'{trial_stem}_filtered_{FILT_FREQ}Hz'
    outputs_dir = os.path.join(subject_dir, 'Outputs_Sony_sprint_trimmed')

    shank_angular_velocity_csv = os.path.join(
        outputs_dir, f'shank_ang_vel_{file_tag}.csv')
    step_times_left  = os.path.join(outputs_dir, 'step_times_left.csv')
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

    mot_file             = kinematics_filtered
    lit_file_nordsprint  = os.path.join(
        LIT_DIR, 'NordSprintAllKinematics', 'All_Kinematics_Combined.csv')
    lit_file_nordsprint_all = os.path.join(
        LIT_DIR, 'NordSprintAllKinematics', 'All_Kinematics_Combined.csv')
    hamner_dir = os.path.join(LIT_DIR, 'SamHamnerKinematics')

    step_times_csv        = os.path.join(outputs_dir, 'step_times.csv')
    kinematics_file_reed  = kinematics_filtered
    stride_vel_output_dir = os.path.join(outputs_dir, 'stride_velocities')

    return {
        'subject_dir':      subject_dir,
        'trial_stem':       trial_stem,
        'trial_name':       trial_name,
        'file_tag':         file_tag,
        'openpose_variant': OPENPOSE_VARIANT,
        'kinematics_input':    kinematics_input,
        'kinematics_filtered': kinematics_filtered,
        'session_id':   session_id,
        'outputs_dir':  outputs_dir,
        'shank_angular_velocity_csv': shank_angular_velocity_csv,
        'step_times_left':  step_times_left,
        'step_times_right': step_times_right,
        'normalized_bflh_csv':     normalized_bflh_csv,
        'lit_lengths_file':        lit_lengths_file,
        'lit_velocities_file':     lit_velocities_file,
        'lit_bflh_nordsprint':     lit_bflh_nordsprint,
        'lit_hamstrings_combined': lit_hamstrings_combined,
        'mot_file':               mot_file,
        'lit_file_nordsprint':    lit_file_nordsprint,
        'lit_file_nordsprint_all': lit_file_nordsprint_all,
        'hamner_dir':             hamner_dir,
        'step_times_csv':        step_times_csv,
        'kinematics_file_reed':  kinematics_file_reed,
        'stride_vel_output_dir': stride_vel_output_dir,
        'peak_bflh_angles_csv':  os.path.join(
            outputs_dir, f'peak_bflh_angles_{file_tag}.csv'),
    }


PATHS = build_paths()


def print_summary():
    print('=' * 60)
    print('Pipeline Configuration  [Sony sprint_trimmed]')
    print('=' * 60)
    print(f'  Trial:          {TRIAL_TYPE}')
    print(f'  OpenPose:       {OPENPOSE_VARIANT}')
    print(f'  Filter freq:    {FILT_FREQ} Hz')
    print(f'  Kin input:      {PATHS["kinematics_input"]}')
    print(f'  Outputs dir:    {PATHS["outputs_dir"]}')
    print('=' * 60)


if __name__ == '__main__':
    print_summary()
    for k, v in PATHS.items():
        print(f'  {k:30s}  {v}')
