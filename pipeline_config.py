"""
Central configuration for the OpenCap processing pipeline.

Edit the SUBJECT PARAMETERS section below, then run any script or
run_pipeline.py -- all scripts import paths from here.
"""

import os

# =====================================================================
# SUBJECT PARAMETERS  --  edit these per subject/session
# =====================================================================
SUBJECT_NUM = 2
DATE = 'March_2'
SESSION = '7'
TRIAL_TYPE = 'sprint'
OPENPOSE_VARIANT = 'OpenPose_1x736_2scales'  # options: 'OpenPose_default', 'OpenPose_1x1008_4scales', 'OpenPose_1x736_2scales'
FILT_FREQ = 10                 # kinematics lowpass filter (Hz)
COORD_FILTER_FREQ = 10         # coordinate value filter (Hz)
MTU_LENGTH_FILTER_FREQ = -1    # muscle-tendon length filter (Hz)

# CalcStepVelReedMethodWithFlags threshold
DIST_THRESHOLD = -12.0

# NordSprint speed bins to plot (first is used for Pearson r)
#LIT_SPEEDS = ['7p0', '8p0', '4p0']
LIT_SPEEDS = ['7p0']


# =====================================================================
# BASE DIRECTORIES  --  change only if your drive/root moves
# =====================================================================
DATA_DIR = r'G:\Shared drives\Stanford Football'
LIT_DIR = os.path.join(DATA_DIR, 'LiteratureData')
LOCAL_DIR = r'C:\Users\steudelkri\Documents\opencap-processing'

# =====================================================================
# DERIVED PATHS  --  no need to edit unless folder structure changes
# =====================================================================

def build_paths():
    """Return a dict of every path used by the pipeline scripts."""

    subject_id = f'subject{SUBJECT_NUM}'
    subject_dir = os.path.join(DATA_DIR, DATE, subject_id)
    trial_stem = f'ID{SUBJECT_NUM}_S{SESSION}_{TRIAL_TYPE}'

    # Short tag used in output filenames (e.g. "ID11_S7_sprint")
    file_tag = trial_stem

    # -- FilterKinematics -------------------------------------------------
    # Input filename suffix -- edit KIN_SUFFIX to match your .mot filename
    # Examples:
    #   OpenPose_default + NoSync:  KIN_SUBFOLDER = 'Kinematics_NoSync', KIN_SUFFIX = ''
    #   OpenPose_default + LSTM:    KIN_SUBFOLDER = 'Kinematics',        KIN_SUFFIX = '_LSTM'
    #   1x1008_4scales trimmed:     KIN_SUBFOLDER = 'Kinematics',        KIN_SUFFIX = '_trimmed_LSTM'
    #   1x736_2scales trimmed long: KIN_SUBFOLDER = 'Kinematics',        KIN_SUFFIX = '_trimmed_long_LSTM'
    KIN_SUBFOLDER = 'Kinematics'
    KIN_SUFFIX = '_LSTM' # example: '_trimmed_LSTM' or '_trimmed_long_LSTM' or '_LSTM'
    kinematics_input = os.path.join(
        subject_dir, 'OpenSimData', OPENPOSE_VARIANT, '3-cameras',
        KIN_SUBFOLDER, f'{trial_stem}{KIN_SUFFIX}.mot')

    # Output: filtered .mot
    kinematics_filtered = os.path.join(
        subject_dir, 'Cleaned_Kinematics',
        f'{trial_stem}_filtered_{FILT_FREQ}Hz.mot')

    # -- example_cleaned ---------------------------------------------------
    session_id = os.path.join(subject_dir, 'Cleaned_Kinematics')
    trial_name = f'{trial_stem}_filtered_{FILT_FREQ}Hz'
    outputs_dir = os.path.join(subject_dir, 'CleanedKinematics', 'Outputs')

    # -- SeparateSteps -----------------------------------------------------
    shank_angular_velocity_csv = os.path.join(
        outputs_dir, f'shank_ang_vel_{file_tag}.csv')
    step_times_left = os.path.join(outputs_dir, 'step_times_left.csv')
    step_times_right = os.path.join(outputs_dir, 'step_times_right.csv')

    # -- compare_literature_bflh -------------------------------------------
    normalized_bflh_csv = os.path.join(
        outputs_dir, f'norm_bflh_length_{file_tag}.csv')
    lit_lengths_file = os.path.join(
        LOCAL_DIR, 'experiments', 'LiteratureData', 'BingYuBFLHLengths.csv')
    lit_velocities_file = os.path.join(
        LOCAL_DIR, 'experiments', 'LiteratureData', 'BingYuBFLHVelocities.csv')
    # NordSprint BFLH normalized lengths (same units as experimental data)
    lit_bflh_nordsprint = os.path.join(
        LIT_DIR, 'NordSprintAllKinematics', 'BicepsFemoris_All_Combined.csv')
    # Combined hamstring MTU lengths + velocities (MATLAB/OpenSim computed)
    lit_hamstrings_combined = os.path.join(
        LIT_DIR, 'NordSprintAllKinematics', 'AllHamstrings_Combined.csv')

    # -- compare_literature_bflh_nordsprint --------------------------------
    mot_file = kinematics_filtered
    lit_file_nordsprint = os.path.join(
        LIT_DIR, 'NordSprintKinematics', 'All_Kinematics_Combined.csv')
    # Full all-coordinate NordSprint literature file (used by PlotStrideKinematics)
    lit_file_nordsprint_all = os.path.join(
        LIT_DIR, 'NordSprintAllKinematics', 'All_Kinematics_Combined.csv')
    hamner_dir = os.path.join(LIT_DIR, 'SamHamnerKinematics')

    # -- CalcStepVelReedMethodWithFlags ------------------------------------
    step_times_csv = os.path.join(outputs_dir, 'step_times.csv')
    kinematics_file_reed = kinematics_filtered
    stride_vel_output_dir = os.path.join(
        subject_dir, 'Kinematics', 'Outputs', 'stride_velocities')

    return {
        # identifiers
        'subject_dir': subject_dir,
        'trial_stem': trial_stem,
        'trial_name': trial_name,
        'file_tag': file_tag,
        'openpose_variant': OPENPOSE_VARIANT,

        # FilterKinematics
        'kinematics_input': kinematics_input,
        'kinematics_filtered': kinematics_filtered,

        # example_cleaned
        'session_id': session_id,
        'outputs_dir': outputs_dir,

        # SeparateSteps
        'shank_angular_velocity_csv': shank_angular_velocity_csv,
        'step_times_left': step_times_left,
        'step_times_right': step_times_right,

        # compare_literature_bflh
        'normalized_bflh_csv': normalized_bflh_csv,
        'lit_lengths_file': lit_lengths_file,
        'lit_velocities_file': lit_velocities_file,
        'lit_bflh_nordsprint': lit_bflh_nordsprint,
        'lit_hamstrings_combined': lit_hamstrings_combined,

        # compare_literature_bflh_nordsprint
        'mot_file': mot_file,
        'lit_file_nordsprint': lit_file_nordsprint,
        'lit_file_nordsprint_all': lit_file_nordsprint_all,
        'hamner_dir': hamner_dir,

        # CalcStepVelReedMethodWithFlags
        'step_times_csv': step_times_csv,
        'kinematics_file_reed': kinematics_file_reed,
        'stride_vel_output_dir': stride_vel_output_dir,

        # PeakBFLHAngles
        'peak_bflh_angles_csv': os.path.join(
            outputs_dir, f'peak_bflh_angles_{file_tag}.csv'),
    }


# Build once at import time so scripts can do:
#   import pipeline_config as cfg
#   paths = cfg.PATHS
PATHS = build_paths()


def print_summary():
    """Print current configuration."""
    print('=' * 60)
    print('Pipeline Configuration')
    print('=' * 60)
    print(f'  Subject:        {SUBJECT_NUM}')
    print(f'  Date:           {DATE}')
    print(f'  Session:        {SESSION}')
    print(f'  Trial type:     {TRIAL_TYPE}')
    print(f'  Filter freq:    {FILT_FREQ} Hz')
    print(f'  Coord filter:   {COORD_FILTER_FREQ} Hz')
    print(f'  MTU filter:     {MTU_LENGTH_FILTER_FREQ} Hz')
    print(f'  Outputs dir:    {PATHS["outputs_dir"]}')
    print('=' * 60)


if __name__ == '__main__':
    print_summary()
    print('\nAll paths:')
    for k, v in PATHS.items():
        print(f'  {k:30s}  {v}')
