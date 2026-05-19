"""
pipeline_config_OpenCap.py

Configuration for the OpenCap-sourced trial from the Sony Camera Testing
dataset.  The folder structure differs from the OpenPose trials:

  subject1/
    OpenCapData/
      OpenSimData/
        Model/    LaiUhlrich2022_scaled.osim
        Kinematics/  sprint_1.mot  sprint_2.mot  ...

Edit SUBJECT_NUM / TRIAL_TYPE at the top; all paths are derived automatically.
"""

import os

# =====================================================================
# SUBJECT PARAMETERS  --  edit these per trial
# =====================================================================
SUBJECT_NUM = 1
DATE        = ''          # no date subfolder in this dataset
SESSION     = ''          # no session number in this dataset
TRIAL_TYPE  = 'sprint'  # must match the .mot filename (sprint_1.mot)

FILT_FREQ             = 10    # kinematics lowpass filter (Hz)
COORD_FILTER_FREQ     = 10    # coordinate-value filter (Hz)
MTU_LENGTH_FILTER_FREQ = -1   # muscle-tendon length filter (Hz, -1 = off)

DIST_THRESHOLD = -12.0        # CalcStepVelReedMethodWithFlags threshold

LIT_SPEEDS = ['7p0']          # NordSprint speed bins to overlay

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

    trial_stem = TRIAL_TYPE                          # e.g. 'sprint_1'
    file_tag   = f'sub{SUBJECT_NUM}_{TRIAL_TYPE}_oc' # e.g. 'sub1_sprint_1_oc'

    # -- FilterKinematics --------------------------------------------------
    # Raw IK result from OpenCap (no OpenPose variant / camera subfolder)
    kinematics_input = os.path.join(
        opencap_dir, 'OpenSimData', 'Kinematics', f'{trial_stem}.mot')

    # Filtered output
    kinematics_filtered = os.path.join(
        opencap_dir, 'Cleaned_Kinematics',
        f'{trial_stem}_filtered_{FILT_FREQ}Hz.mot')

    # -- example_cleaned ---------------------------------------------------
    # session_id points to the folder containing the filtered .mot so
    # example_cleaned.find_session_root() can walk up and find OpenSimData.
    session_id = os.path.join(opencap_dir, 'Cleaned_Kinematics')
    trial_name = f'{trial_stem}_filtered_{FILT_FREQ}Hz'
    outputs_dir = os.path.join(opencap_dir, 'Outputs')

    # Explicit model path — bypasses the OpenPose variant glob in example_cleaned.py
    model_path = os.path.join(
        opencap_dir, 'OpenSimData', 'Model', 'LaiUhlrich2022_scaled.osim')

    # -- SeparateSteps -----------------------------------------------------
    shank_angular_velocity_csv = os.path.join(
        outputs_dir, f'shank_ang_vel_{file_tag}.csv')
    step_times_left  = os.path.join(outputs_dir, 'step_times_left.csv')
    step_times_right = os.path.join(outputs_dir, 'step_times_right.csv')

    # -- compare_literature_bflh -------------------------------------------
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

    # -- compare_literature_bflh_nordsprint / PlotStrideKinematics ---------
    mot_file              = kinematics_filtered
    lit_file_nordsprint   = os.path.join(
        LIT_DIR, 'NordSprintKinematics', 'All_Kinematics_Combined.csv')
    lit_file_nordsprint_all = os.path.join(
        LIT_DIR, 'NordSprintAllKinematics', 'All_Kinematics_Combined.csv')
    hamner_dir = os.path.join(LIT_DIR, 'SamHamnerKinematics')

    # -- CalcStepVelReedMethodWithFlags ------------------------------------
    step_times_csv       = os.path.join(outputs_dir, 'step_times.csv')
    kinematics_file_reed = kinematics_filtered
    stride_vel_output_dir = os.path.join(opencap_dir, 'Outputs', 'stride_velocities')

    return {
        # identifiers
        'subject_dir':      subject_dir,
        'trial_stem':       trial_stem,
        'trial_name':       trial_name,
        'file_tag':         file_tag,
        'openpose_variant': 'OpenCapData',  # unused; model_path overrides lookup

        # FilterKinematics
        'kinematics_input':    kinematics_input,
        'kinematics_filtered': kinematics_filtered,

        # example_cleaned
        'session_id':   session_id,
        'outputs_dir':  outputs_dir,
        'model_path':   model_path,   # explicit — skips OpenPose glob

        # SeparateSteps
        'shank_angular_velocity_csv': shank_angular_velocity_csv,
        'step_times_left':  step_times_left,
        'step_times_right': step_times_right,

        # compare_literature_bflh
        'normalized_bflh_csv':  normalized_bflh_csv,
        'lit_lengths_file':     lit_lengths_file,
        'lit_velocities_file':  lit_velocities_file,
        'lit_bflh_nordsprint':  lit_bflh_nordsprint,
        'lit_hamstrings_combined': lit_hamstrings_combined,

        # compare_literature_bflh_nordsprint / PlotStrideKinematics
        'mot_file':               mot_file,
        'lit_file_nordsprint':    lit_file_nordsprint,
        'lit_file_nordsprint_all': lit_file_nordsprint_all,
        'hamner_dir':             hamner_dir,

        # CalcStepVelReedMethodWithFlags
        'step_times_csv':        step_times_csv,
        'kinematics_file_reed':  kinematics_file_reed,
        'stride_vel_output_dir': stride_vel_output_dir,

        # PeakBFLHAngles
        'peak_bflh_angles_csv': os.path.join(
            outputs_dir, f'peak_bflh_angles_{file_tag}.csv'),
    }


PATHS = build_paths()


def print_summary():
    print('=' * 60)
    print('Pipeline Configuration  [OpenCap]')
    print('=' * 60)
    print(f'  Subject:        {SUBJECT_NUM}')
    print(f'  Trial type:     {TRIAL_TYPE}')
    print(f'  Filter freq:    {FILT_FREQ} Hz')
    print(f'  Coord filter:   {COORD_FILTER_FREQ} Hz')
    print(f'  MTU filter:     {MTU_LENGTH_FILTER_FREQ} Hz')
    print(f'  Kin input:      {PATHS["kinematics_input"]}')
    print(f'  Model path:     {PATHS["model_path"]}')
    print(f'  Outputs dir:    {PATHS["outputs_dir"]}')
    print('=' * 60)


if __name__ == '__main__':
    print_summary()
    print('\nAll paths:')
    for k, v in PATHS.items():
        print(f'  {k:30s}  {v}')
