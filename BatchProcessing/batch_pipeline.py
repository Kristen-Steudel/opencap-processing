"""
BatchProcessing/batch_pipeline.py

Discover subjects across collection days, generate per-trial pipeline config
files, and run the 8-step pipeline in batch using scripts in this folder.

Prerequisites for each subject/trial:
  - Kinematics .mot in OpenSimData/{OPENPOSE_VARIANT}/3-cameras/Kinematics/
  - Scaled model in OpenSimData/{OPENPOSE_VARIANT}/3-cameras/Model/*scaled.osim

Usage:
    cd BatchProcessing

    # Preview what is ready on one collection day
    python batch_pipeline.py --dry-run --date March_2

    # Generate config files for all ready trials on that day
    python batch_pipeline.py --generate-configs --date March_2

    # Run the pipeline for generated configs on that day
    python batch_pipeline.py --run --date March_2

    # Generate + run in one command
    python batch_pipeline.py --generate-configs --run --date March_2

    # All collection days, only sprint trials
    python batch_pipeline.py --generate-configs --run --trial-type sprint

    # Re-run steps 1-3 for one subject
    python batch_pipeline.py --run --date March_2 --subject 5 --steps 1 2 3
"""

import argparse
import glob
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BATCH_CONFIG_DIR = os.path.join(SCRIPT_DIR, 'batch_configs')
RUN_PIPELINE = os.path.join(SCRIPT_DIR, 'run_pipeline.py')

# Defaults match BatchProcessing/pipeline_config.py
DEFAULTS = {
    'DATA_DIR': r'G:\Shared drives\Stanford Football',
    'LOCAL_DIR': r'C:\Users\steudelkri\Documents\opencap-processing',
    'OPENPOSE_VARIANT': 'OpenPose_1x736_2scales',
    'KIN_SUBFOLDER': 'Kinematics',
    'KIN_SUFFIX': '_LSTM',
    'TRIAL_TYPE_FILTER': None,   # None = all trial types found
    'FILT_FREQ': 10,
    'COORD_FILTER_FREQ': 10,
    'MTU_LENGTH_FILTER_FREQ': -1,
    'DIST_THRESHOLD': -12.0,
    'LIT_SPEEDS': ['7p0'],
}

SKIP_TOP_LEVEL_DIRS = {
    'LiteratureData', 'batch_configs', '__pycache__',
}

MOT_RE = re.compile(
    r'^ID(?P<subj>\d+)_S(?P<session>\d+)_(?P<trial>.+?)(?P<suffix>_LSTM|_trimmed_LSTM|_trimmed_long_LSTM|)\.mot$',
    re.IGNORECASE,
)

SUBJECT_RE = re.compile(r'^subject(\d+)$', re.IGNORECASE)


def config_module_name(date, subject_num, session, trial_type):
    return f'pipeline_config_{date}_ID{subject_num}_S{session}_{trial_type}'


def config_file_path(date, subject_num, session, trial_type):
    return os.path.join(
        BATCH_CONFIG_DIR,
        f'{config_module_name(date, subject_num, session, trial_type)}.py')


def list_date_folders(data_dir, dates=None):
    if dates:
        return [d for d in dates if os.path.isdir(os.path.join(data_dir, d))]

    found = []
    for name in sorted(os.listdir(data_dir)):
        path = os.path.join(data_dir, name)
        if not os.path.isdir(path):
            continue
        if name in SKIP_TOP_LEVEL_DIRS:
            continue
        # Expect at least one subject folder inside
        if any(SUBJECT_RE.match(entry) for entry in os.listdir(path)):
            found.append(name)
    return found


def list_subject_dirs(date_dir):
    subjects = []
    if not os.path.isdir(date_dir):
        return subjects
    for name in sorted(os.listdir(date_dir), key=lambda s: (
            int(SUBJECT_RE.match(s).group(1)) if SUBJECT_RE.match(s) else 999)):
        m = SUBJECT_RE.match(name)
        if m:
            subjects.append(int(m.group(1)))
    return subjects


def find_scaled_model(subject_dir, openpose_variant):
    pattern = os.path.join(
        subject_dir, 'OpenSimData', openpose_variant, '3-cameras', 'Model', '*scaled.osim')
    models = sorted(glob.glob(pattern))
    return models[0] if models else None


def discover_trials(subject_dir, subject_num, openpose_variant, kin_subfolder, trial_type_filter):
    kin_dir = os.path.join(
        subject_dir, 'OpenSimData', openpose_variant, '3-cameras', kin_subfolder)
    if not os.path.isdir(kin_dir):
        return []

    trials = []
    for mot_path in sorted(glob.glob(os.path.join(kin_dir, '*.mot'))):
        fname = os.path.basename(mot_path)
        m = MOT_RE.match(fname)
        if not m:
            continue
        subj = int(m.group('subj'))
        if subj != subject_num:
            continue
        session = m.group('session')
        trial_type = m.group('trial')
        suffix = m.group('suffix') or ''
        if trial_type_filter and trial_type.lower() != trial_type_filter.lower():
            continue
        model_path = find_scaled_model(subject_dir, openpose_variant)
        ready = os.path.isfile(mot_path) and model_path is not None
        trials.append({
            'subject_num': subj,
            'session': session,
            'trial_type': trial_type,
            'kin_suffix': suffix,
            'kin_subfolder': kin_subfolder,
            'mot_path': mot_path,
            'model_path': model_path,
            'ready': ready,
        })
    return trials


def render_config_file(date, trial_info, settings):
    subj = trial_info['subject_num']
    session = trial_info['session']
    trial_type = trial_info['trial_type']
    kin_suffix = trial_info['kin_suffix']
    kin_subfolder = trial_info['kin_subfolder']
    openpose_variant = settings['OPENPOSE_VARIANT']
    filt_freq = settings['FILT_FREQ']
    lit_speeds = settings['LIT_SPEEDS']

    return f'''"""
Auto-generated batch config
  Date:    {date}
  Subject: {subj}
  Session: {session}
  Trial:   {trial_type}
"""

import os

SUBJECT_NUM = {subj}
DATE = '{date}'
SESSION = '{session}'
TRIAL_TYPE = '{trial_type}'
OPENPOSE_VARIANT = '{openpose_variant}'
FILT_FREQ = {filt_freq}
COORD_FILTER_FREQ = {settings['COORD_FILTER_FREQ']}
MTU_LENGTH_FILTER_FREQ = {settings['MTU_LENGTH_FILTER_FREQ']}
DIST_THRESHOLD = {settings['DIST_THRESHOLD']}
LIT_SPEEDS = {lit_speeds!r}

DATA_DIR = r'{settings['DATA_DIR']}'
LIT_DIR = os.path.join(DATA_DIR, 'LiteratureData')
LOCAL_DIR = r'{settings['LOCAL_DIR']}'


def build_paths():
    subject_id = f'subject{{SUBJECT_NUM}}'
    subject_dir = os.path.join(DATA_DIR, DATE, subject_id)
    trial_stem = f'ID{{SUBJECT_NUM}}_S{{SESSION}}_{{TRIAL_TYPE}}'
    file_tag = trial_stem

    KIN_SUBFOLDER = '{kin_subfolder}'
    KIN_SUFFIX = '{kin_suffix}'
    kinematics_input = os.path.join(
        subject_dir, 'OpenSimData', OPENPOSE_VARIANT, '3-cameras',
        KIN_SUBFOLDER, f'{{trial_stem}}{{KIN_SUFFIX}}.mot')

    kinematics_filtered = os.path.join(
        subject_dir, 'Cleaned_Kinematics',
        f'{{trial_stem}}_filtered_{{FILT_FREQ}}Hz.mot')

    session_id = os.path.join(subject_dir, 'Cleaned_Kinematics')
    trial_name = f'{{trial_stem}}_filtered_{{FILT_FREQ}}Hz'
    outputs_dir = os.path.join(subject_dir, 'CleanedKinematics', 'Outputs')

    shank_angular_velocity_csv = os.path.join(
        outputs_dir, f'shank_ang_vel_{{file_tag}}.csv')
    step_times_left = os.path.join(outputs_dir, 'step_times_left.csv')
    step_times_right = os.path.join(outputs_dir, 'step_times_right.csv')

    normalized_bflh_csv = os.path.join(
        outputs_dir, f'norm_bflh_length_{{file_tag}}.csv')
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

    return {{
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
            outputs_dir, f'peak_bflh_angles_{{file_tag}}.csv'),
    }}


PATHS = build_paths()


def print_summary():
    print('=' * 60)
    print('Pipeline Configuration  [batch]')
    print('=' * 60)
    print(f'  Subject:        {{SUBJECT_NUM}}')
    print(f'  Date:           {{DATE}}')
    print(f'  Session:        {{SESSION}}')
    print(f'  Trial type:     {{TRIAL_TYPE}}')
    print(f'  OpenPose:       {{OPENPOSE_VARIANT}}')
    print(f'  Filter freq:    {{FILT_FREQ}} Hz')
    print(f'  Kin input:      {{PATHS["kinematics_input"]}}')
    print(f'  Outputs dir:    {{PATHS["outputs_dir"]}}')
    print('=' * 60)
'''


def collect_jobs(settings, dates=None, subjects=None):
    jobs = []
    data_dir = settings['DATA_DIR']
    for date in list_date_folders(data_dir, dates):
        date_dir = os.path.join(data_dir, date)
        subject_nums = list_subject_dirs(date_dir)
        if subjects:
            subject_nums = [s for s in subject_nums if s in subjects]

        for subject_num in subject_nums:
            subject_dir = os.path.join(date_dir, f'subject{subject_num}')
            trials = discover_trials(
                subject_dir, subject_num,
                settings['OPENPOSE_VARIANT'],
                settings['KIN_SUBFOLDER'],
                settings['TRIAL_TYPE_FILTER'],
            )
            for trial in trials:
                module = config_module_name(
                    date, trial['subject_num'], trial['session'], trial['trial_type'])
                jobs.append({
                    'date': date,
                    'module': module,
                    'config_path': config_file_path(
                        date, trial['subject_num'], trial['session'], trial['trial_type']),
                    **trial,
                })
    return jobs


def generate_configs(jobs, settings, overwrite=False):
    os.makedirs(BATCH_CONFIG_DIR, exist_ok=True)
    written = []
    skipped = []
    for job in jobs:
        if not job['ready']:
            skipped.append(job)
            continue
        path = job['config_path']
        if os.path.exists(path) and not overwrite:
            skipped.append(job)
            continue
        content = render_config_file(job['date'], job, settings)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        written.append(job)
    return written, skipped


def run_pipeline_for_job(job, steps=None, stop_on_error=True):
    cmd = [sys.executable, RUN_PIPELINE, '--config', job['module']]
    if steps:
        cmd.extend(['--steps', *steps])

    print(f"\n{'#' * 70}")
    print(f"  Running: {job['date']}  subject{job['subject_num']}  "
          f"S{job['session']}  {job['trial_type']}")
    print(f"  Config:  {job['module']}")
    print(f"{'#' * 70}")

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if result.returncode != 0 and stop_on_error:
        return result.returncode
    return result.returncode


def print_job_table(jobs, title):
    print(f"\n{title} ({len(jobs)})")
    print('-' * 90)
    if not jobs:
        print('  (none)')
        return
    for job in jobs:
        status = 'READY' if job['ready'] else 'MISSING INPUTS'
        print(f"  [{status:15s}]  {job['date']:12s}  subject{job['subject_num']:2d}  "
              f"S{job['session']}  {job['trial_type']:10s}  {os.path.basename(job['mot_path'])}")
        if not job['ready']:
            missing = []
            if not os.path.isfile(job['mot_path']):
                missing.append('kinematics .mot')
            if not job['model_path']:
                missing.append('scaled .osim model')
            print(f"                    missing: {', '.join(missing)}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate batch pipeline configs and run FootballAnalysis pipeline.')
    parser.add_argument('--date', action='append', metavar='FOLDER',
                        help='Collection day folder name (repeatable). Default: all days found.')
    parser.add_argument('--subject', type=int, action='append', metavar='N',
                        help='Limit to subject number(s) (repeatable).')
    parser.add_argument('--trial-type', metavar='NAME',
                        help='Only include this trial type (e.g. sprint, fly).')
    parser.add_argument('--openpose-variant', default=DEFAULTS['OPENPOSE_VARIANT'],
                        help=f"OpenPose folder name (default: {DEFAULTS['OPENPOSE_VARIANT']})")
    parser.add_argument('--kin-suffix', default=DEFAULTS['KIN_SUFFIX'],
                        help=f"Kinematics filename suffix (default: {DEFAULTS['KIN_SUFFIX']})")
    parser.add_argument('--generate-configs', action='store_true',
                        help='Write config files to BatchProcessing/batch_configs/')
    parser.add_argument('--run', action='store_true',
                        help='Run run_pipeline.py for ready configs')
    parser.add_argument('--dry-run', action='store_true',
                        help='List discovered trials without writing or running')
    parser.add_argument('--overwrite', action='store_true',
                        help='Overwrite existing generated config files')
    parser.add_argument('--steps', nargs='+', metavar='N',
                        help='Pipeline steps to run (passed to run_pipeline.py)')
    parser.add_argument('--continue-on-error', action='store_true',
                        help='Keep processing later subjects if one fails')
    args = parser.parse_args()

    if not any([args.generate_configs, args.run, args.dry_run]):
        parser.error('Specify at least one of: --generate-configs, --run, --dry-run')

    settings = dict(DEFAULTS)
    settings['OPENPOSE_VARIANT'] = args.openpose_variant
    settings['KIN_SUFFIX'] = args.kin_suffix
    settings['TRIAL_TYPE_FILTER'] = args.trial_type

    jobs = collect_jobs(settings, dates=args.date, subjects=args.subject)
    ready_jobs = [j for j in jobs if j['ready']]
    not_ready = [j for j in jobs if not j['ready']]

    print_job_table(ready_jobs, 'Ready trials')
    print_job_table(not_ready, 'Trials missing kinematics or model')

    if args.dry_run and not args.generate_configs and not args.run:
        print(f"\nDry run complete. {len(ready_jobs)} trial(s) ready for batch processing.")
        return 0

    exit_code = 0

    if args.generate_configs:
        written, skipped = generate_configs(ready_jobs, settings, overwrite=args.overwrite)
        print(f"\nGenerated {len(written)} config file(s) in:\n  {BATCH_CONFIG_DIR}")
        if skipped:
            print(f"Skipped {len(skipped)} (not ready or already exists; use --overwrite to replace).")

    if args.run:
        # Run from generated config files on disk
        run_jobs = []
        for job in ready_jobs:
            if os.path.isfile(job['config_path']):
                run_jobs.append(job)
            else:
                print(f"\nWARNING: config not found, skipping run for "
                      f"{job['date']} subject{job['subject_num']} S{job['session']} "
                      f"{job['trial_type']}\n  {job['config_path']}\n"
                      f"  Run with --generate-configs first.")

        print(f"\nRunning pipeline for {len(run_jobs)} config(s)...")
        failures = []
        for job in run_jobs:
            rc = run_pipeline_for_job(
                job, steps=args.steps,
                stop_on_error=not args.continue_on_error)
            if rc != 0:
                failures.append(job)
                if not args.continue_on_error:
                    return rc

        print(f"\n{'=' * 70}")
        print('Batch Run Summary')
        print(f"{'=' * 70}")
        print(f"  Completed: {len(run_jobs) - len(failures)}")
        print(f"  Failed:    {len(failures)}")
        if failures:
            for job in failures:
                print(f"    - {job['date']} subject{job['subject_num']} "
                      f"S{job['session']} {job['trial_type']}")
            exit_code = 1

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
