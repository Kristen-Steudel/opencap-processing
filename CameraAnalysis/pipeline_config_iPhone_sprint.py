"""
pipeline_config_iPhone_sprint.py

OpenCap iPhone cameras — trial: sprint
Kinematics: subject1/OpenCapData/OpenSimData/Kinematics/sprint.mot
Model:      subject1/OpenCapData/OpenSimData/Model/LaiUhlrich2022_scaled.osim
"""

import os

# =====================================================================
# SUBJECT PARAMETERS
# =====================================================================
SUBJECT_NUM = 1
DATE        = ''
SESSION     = ''
TRIAL_TYPE  = 'sprint'          # → sprint.mot

TRIAL_LABEL = 'iPhone / OpenCap'

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
    opencap_dir = os.path.join(subject_dir, 'OpenCapData')

    trial_stem = TRIAL_TYPE                              # 'sprint'
    file_tag   = f'sub{SUBJECT_NUM}_{TRIAL_TYPE}_iphone' # 'sub1_sprint_iphone'

    kinematics_input = os.path.join(
        opencap_dir, 'OpenSimData', 'Kinematics', f'{trial_stem}.mot')
    kinematics_filtered = os.path.join(
        opencap_dir, 'Cleaned_Kinematics',
        f'{trial_stem}_filtered_{FILT_FREQ}Hz.mot')

    session_id  = os.path.join(opencap_dir, 'Cleaned_Kinematics')
    trial_name  = f'{trial_stem}_filtered_{FILT_FREQ}Hz'
    outputs_dir = os.path.join(opencap_dir, 'Outputs_iPhone_sprint')

    model_path = os.path.join(
        opencap_dir, 'OpenSimData', 'Model', 'LaiUhlrich2022_scaled.osim')

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
        'openpose_variant': 'OpenCapData',
        'model_path':       model_path,
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
    print('Pipeline Configuration  [iPhone sprint]')
    print('=' * 60)
    print(f'  Trial:          {TRIAL_TYPE}')
    print(f'  Filter freq:    {FILT_FREQ} Hz')
    print(f'  Kin input:      {PATHS["kinematics_input"]}')
    print(f'  Model path:     {PATHS["model_path"]}')
    print(f'  Outputs dir:    {PATHS["outputs_dir"]}')
    print('=' * 60)


if __name__ == '__main__':
    print_summary()
    import os as _os
    for k, v in PATHS.items():
        print(f'  {k:30s}  {v}')
