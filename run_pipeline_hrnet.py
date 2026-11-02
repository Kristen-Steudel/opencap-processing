"""
HRNet / mmpose_0.8 pipeline for February_23 fly trials.

Subjects: 8, 13, 16, 25, 34, 36, 54

Steps (default):
  2  compute_shank_ang_vel_hrnet.py          shank angular velocity
  3  SeparateSteps_hrnet.py                  foot-contact / step times
  6  CalcStepVelReedMethodWithFlags_hrnet.py stride velocities (Reed)

Kinematics are read from Google Drive. All outputs go to local:
  AccelStepVelocities/subject{N}/ID{N}_S6_fly/

Usage:
    python run_pipeline_hrnet.py
    python run_pipeline_hrnet.py --dry-run
    python run_pipeline_hrnet.py --subject 13
    python run_pipeline_hrnet.py --steps 2 3
    python run_pipeline_hrnet.py --list
"""

import argparse
import os
import sys
import subprocess
import textwrap

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_ROOT = os.path.join(SCRIPT_DIR, 'AccelStepVelocities')
CONFIG_DIR = os.path.join(OUTPUT_ROOT, 'configs')

SUBJECTS = [8, 13, 16, 25, 34, 36, 54]

# Sam-says-Go times (full-length video clock). Plotted as black dashed
# vertical lines marking the start of the first stride on time-series plots.
SUBJECT_FIRST_STRIDE_TIME = {
    8: 4.893,
    13: 5.002,
    16: 5.265,
    19: 6.19,
    25: 4.05,
    34: 3.948,
    36: 4.209,
    54: 4.855,
}

DATA_DIR = (
    '/Users/steudelk/Library/CloudStorage/GoogleDrive-steudelk@stanford.edu'
    '/Shared drives/Stanford Football'
)
DATE = 'February_23'
SESSION = '6'
TRIAL_TYPE = 'fly'
POSE_VARIANT = 'mmpose_0.8'
KIN_SUFFIX = '_LSTM_hip_flexion_adjusted'
DIST_THRESHOLD = -12.0

PIPELINE = [
    ('2', 'compute_shank_ang_vel_hrnet.py',
     'Compute shank angular velocity'),
    ('3', 'SeparateSteps_hrnet.py',
     'Detect foot contacts / stride times'),
    ('6', 'CalcStepVelReedMethodWithFlags_hrnet.py',
     'Calculate stride velocities (Reed)'),
]


def trial_stem(subject_num):
    return f'ID{subject_num}_S{SESSION}_{TRIAL_TYPE}'


def file_tag(subject_num):
    return f'{trial_stem(subject_num)}{KIN_SUFFIX}'


def kinematics_path(subject_num):
    return os.path.join(
        DATA_DIR, DATE, f'subject{subject_num}',
        'OpenSimData', POSE_VARIANT, 'Kinematics',
        f'{file_tag(subject_num)}.mot')


def model_path(subject_num):
    return os.path.join(
        DATA_DIR, DATE, f'subject{subject_num}',
        'OpenSimData', POSE_VARIANT, 'Model',
        'LaiUhlrich2022_scaled.osim')


def outputs_dir(subject_num):
    return os.path.join(OUTPUT_ROOT, f'subject{subject_num}', trial_stem(subject_num))


def config_module_name(subject_num):
    return f'pipeline_config_hrnet_ID{subject_num}_S{SESSION}_{TRIAL_TYPE}'


def write_subject_config(subject_num):
    """Write a per-subject config module under AccelStepVelocities/configs/."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    module = config_module_name(subject_num)
    path = os.path.join(CONFIG_DIR, f'{module}.py')
    tag = file_tag(subject_num)
    stem = trial_stem(subject_num)
    kin = kinematics_path(subject_num)
    model = model_path(subject_num)
    out = outputs_dir(subject_num)
    stride_out = os.path.join(out, 'stride_velocities')
    first_stride_time = SUBJECT_FIRST_STRIDE_TIME.get(subject_num)

    content = textwrap.dedent(f'''\
    """Auto-generated HRNet config for subject {subject_num}."""
    import os

    SUBJECT_NUM = {subject_num}
    DATE = '{DATE}'
    SESSION = '{SESSION}'
    TRIAL_TYPE = '{TRIAL_TYPE}'
    POSE_VARIANT = '{POSE_VARIANT}'
    KIN_SUFFIX = '{KIN_SUFFIX}'
    FILT_FREQ = 10
    COORD_FILTER_FREQ = 10
    MTU_LENGTH_FILTER_FREQ = -1
    DIST_THRESHOLD = {DIST_THRESHOLD}
    LIT_SPEEDS = ['7p0']
    FIRST_STRIDE_TIME = {first_stride_time!r}

    DATA_DIR = r'{DATA_DIR}'
    LOCAL_DIR = r'{SCRIPT_DIR}'
    OUTPUT_ROOT = r'{OUTPUT_ROOT}'

    PATHS = {{
        'subject_dir': r'{os.path.join(DATA_DIR, DATE, f"subject{subject_num}")}',
        'trial_stem': '{stem}',
        'trial_name': '{tag}',
        'file_tag': '{tag}',
        'openpose_variant': '{POSE_VARIANT}',
        'model_path': r'{model}',
        'kinematics_input': r'{kin}',
        'kinematics_filtered': r'{kin}',
        'session_id': r'{out}',
        'outputs_dir': r'{out}',
        'shank_angular_velocity_csv': r'{os.path.join(out, f"shank_ang_vel_{tag}.csv")}',
        'step_times_left': r'{os.path.join(out, "step_times_left.csv")}',
        'step_times_right': r'{os.path.join(out, "step_times_right.csv")}',
        'step_times_csv': r'{os.path.join(out, "step_times.csv")}',
        'kinematics_file_reed': r'{kin}',
        'stride_vel_output_dir': r'{stride_out}',
        'mot_file': r'{kin}',
        'first_stride_time': {first_stride_time!r},
    }}


    def print_summary():
        print('=' * 60)
        print('Pipeline Configuration  [HRNet / mmpose_0.8]')
        print('=' * 60)
        print(f'  Subject:        {{SUBJECT_NUM}}')
        print(f'  Date:           {{DATE}}')
        print(f'  Session:        {{SESSION}}')
        print(f'  Trial type:     {{TRIAL_TYPE}}')
        print(f'  First stride:   {{FIRST_STRIDE_TIME}} s')
        print(f'  Kin input:      {{PATHS["kinematics_input"]}}')
        print(f'  Model:          {{PATHS["model_path"]}}')
        print(f'  Outputs dir:    {{PATHS["outputs_dir"]}}')
        print('=' * 60)
    ''')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return module, path


def subject_ready(subject_num):
    kin = kinematics_path(subject_num)
    model = model_path(subject_num)
    missing = []
    if not os.path.isfile(kin):
        missing.append(f'kinematics: {kin}')
    if not os.path.isfile(model):
        missing.append(f'model: {model}')
    return missing


def run_step(step_id, script_file, description, config_module):
    script_path = os.path.join(SCRIPT_DIR, script_file)
    if not os.path.exists(script_path):
        print(f'  SKIP  {script_file} not found')
        return 1

    print(f"\n{'=' * 60}")
    print(f'  Step {step_id}: {description}')
    print(f'  Script: {script_file}')
    print(f'  Config: {config_module}')
    print(f"{'=' * 60}\n")

    env = dict(os.environ)
    env['PIPELINE_CONFIG'] = config_module
    # Prefer AccelStepVelocities/configs over repo root for generated modules
    pythonpath = CONFIG_DIR
    if env.get('PYTHONPATH'):
        pythonpath = CONFIG_DIR + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath

    result = subprocess.run(
        [sys.executable, script_path], cwd=SCRIPT_DIR, env=env)
    if result.returncode == 0:
        print(f'\n  Step {step_id} completed successfully.')
    else:
        print(f'\n  Step {step_id} FAILED (exit code {result.returncode}).')
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description='HRNet mmpose fly pipeline → AccelStepVelocities/')
    parser.add_argument(
        '--subject', type=int, action='append', metavar='N',
        help='Limit to subject number(s) (repeatable). Default: all HRNet subjects.')
    parser.add_argument(
        '--steps', nargs='+', metavar='N',
        help='Step numbers to run (default: 2 3 6).')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='List subjects/paths without running.')
    parser.add_argument(
        '--list', action='store_true',
        help='List available steps and exit.')
    parser.add_argument(
        '--continue-on-error', action='store_true',
        help='Keep going if one subject/step fails.')
    args = parser.parse_args()

    if args.list:
        print('Available HRNet pipeline steps:')
        for step_id, script, desc in PIPELINE:
            print(f'  {step_id}  {script:50s}  {desc}')
        return 0

    subjects = args.subject if args.subject else SUBJECTS
    steps = (
        [(sid, sf, sd) for sid, sf, sd in PIPELINE if sid in args.steps]
        if args.steps else PIPELINE
    )
    if not steps:
        print(f'No matching steps for: {args.steps}')
        return 1

    print(f'Output root: {OUTPUT_ROOT}')
    print(f'Subjects:    {subjects}')
    print(f'Steps:       {", ".join(s[0] for s in steps)}')

    ready = []
    skipped = []
    for subj in subjects:
        missing = subject_ready(subj)
        if missing:
            skipped.append((subj, missing))
        else:
            ready.append(subj)

    print(f'\nReady subjects ({len(ready)}): {ready}')
    if skipped:
        print(f'Skipped ({len(skipped)}):')
        for subj, missing in skipped:
            print(f'  subject{subj}:')
            for m in missing:
                print(f'    - {m}')

    if args.dry_run:
        for subj in ready:
            print(f'\nsubject{subj}')
            print(f'  kin:  {kinematics_path(subj)}')
            print(f'  model:{model_path(subj)}')
            print(f'  out:  {outputs_dir(subj)}')
        print(f'\nDry run complete. {len(ready)} subject(s) ready.')
        return 0

    failures = []
    for subj in ready:
        print(f"\n{'#' * 70}")
        print(f'  subject{subj}  {trial_stem(subj)}')
        print(f"{'#' * 70}")

        os.makedirs(outputs_dir(subj), exist_ok=True)
        module, _ = write_subject_config(subj)

        # Import generated config for summary
        if CONFIG_DIR not in sys.path:
            sys.path.insert(0, CONFIG_DIR)
        import importlib
        if module in sys.modules:
            del sys.modules[module]
        cfg = importlib.import_module(module)
        cfg.print_summary()

        for step_id, script_file, description in steps:
            rc = run_step(step_id, script_file, description, module)
            if rc != 0:
                failures.append((subj, step_id))
                if not args.continue_on_error:
                    print(f'\nStopping after failure on subject{subj} step {step_id}.')
                    return rc

    print(f"\n{'=' * 70}")
    print('HRNet Batch Summary')
    print(f"{'=' * 70}")
    print(f'  Subjects run: {len(ready)}')
    print(f'  Failures:     {len(failures)}')
    if failures:
        for subj, step_id in failures:
            print(f'    - subject{subj} step {step_id}')
        return 1
    print(f'\nAll outputs written under:\n  {OUTPUT_ROOT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
