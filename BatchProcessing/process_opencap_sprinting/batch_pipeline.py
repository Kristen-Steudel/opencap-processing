"""
BatchProcessing/process_opencap_sprinting/batch_pipeline.py

Self-contained batch orchestration for process-opencap-sprinting bilevel results.
Does not use or modify the parent BatchProcessing/batch_pipeline.py workflow.

Prerequisites for each trial (under RESULTS_DIR):
  - Kinematics .sto:  {trial_stem}_bilevel_solution_filtered.sto
  - Scaled model:     {trial_stem}_bilevel_scaled.osim

Usage:
    cd BatchProcessing/process_opencap_sprinting

    python batch_pipeline.py --dry-run
    python batch_pipeline.py --generate-configs --date March_2
    python batch_pipeline.py --generate-configs --run --subject 2 --trial-type sprint
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

DEFAULTS = {
    'DATA_DIR': r'G:\Shared drives\Stanford Football',
    'LOCAL_DIR': r'/Users/steudelk/Documents/Github/opencap-processing',
    'RESULTS_DIR': r'/Users/steudelk/Documents/Github/process-opencap-sprinting/results',
    'DEFAULT_DATE': 'sprinting',
    'OPENPOSE_VARIANT': 'OpenPose_1x736_2scales',
    'POST_AUG_FOLDER': 'PostAugmentation_v0.3',
    'TRIAL_TYPE_FILTER': None,
    'FILT_FREQ': 10,
    'COORD_FILTER_FREQ': 10,
    'MTU_LENGTH_FILTER_FREQ': -1,
    'DIST_THRESHOLD': -12.0,
    'LIT_SPEEDS': ['7p0'],
}

SKIP_TOP_LEVEL_DIRS = {
    'LiteratureData', 'batch_configs', '__pycache__', 'process_opencap_sprinting',
}

STO_RE = re.compile(
    r'^ID(?P<subj>\d+)_S(?P<session>\d+)_(?P<trial>.+?)_bilevel_solution_filtered\.sto$',
    re.IGNORECASE,
)

OSIM_RE = re.compile(
    r'^ID(?P<subj>\d+)_S(?P<session>\d+)_(?P<trial>.+?)_bilevel_scaled\.osim$',
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
    if not os.path.isdir(data_dir):
        return []

    if dates:
        return [d for d in dates if os.path.isdir(os.path.join(data_dir, d))]

    found = []
    for name in sorted(os.listdir(data_dir)):
        path = os.path.join(data_dir, name)
        if not os.path.isdir(path):
            continue
        if name in SKIP_TOP_LEVEL_DIRS:
            continue
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


def find_scaled_model(results_dir, subject_num, session, trial_type):
    exact = os.path.join(
        results_dir,
        f'ID{subject_num}_S{session}_{trial_type}_bilevel_scaled.osim')
    if os.path.isfile(exact):
        return exact

    pattern = os.path.join(
        results_dir, f'ID{subject_num}_S{session}_*_bilevel_scaled.osim')
    models = sorted(glob.glob(pattern))
    return models[0] if models else None


def parse_trial_from_sto(sto_path, subject_num=None, trial_type_filter=None):
    fname = os.path.basename(sto_path)
    m = STO_RE.match(fname)
    if not m:
        return None

    subj = int(m.group('subj'))
    if subject_num is not None and subj != subject_num:
        return None

    session = m.group('session')
    trial_type = m.group('trial')
    if trial_type_filter and trial_type.lower() != trial_type_filter.lower():
        return None

    trial_stem = f'ID{subj}_S{session}_{trial_type}'
    return {
        'subject_num': subj,
        'session': session,
        'trial_type': trial_type,
        'trial_stem': trial_stem,
        'sto_path': sto_path,
    }


def _trial_record(results_dir, subj, session, trial_type, sto_path, model_path):
    trial_stem = f'ID{subj}_S{session}_{trial_type}'
    mot_path = os.path.join(results_dir, 'Kinematics', f'{trial_stem}.mot')
    has_sto = sto_path and os.path.isfile(sto_path)
    has_mot = os.path.isfile(mot_path)
    ready = model_path is not None and (has_sto or has_mot)
    return {
        'subject_num': subj,
        'session': session,
        'trial_type': trial_type,
        'trial_stem': trial_stem,
        'sto_path': sto_path or os.path.join(
            results_dir, f'{trial_stem}_bilevel_solution_filtered.sto'),
        'mot_path': mot_path,
        'model_path': model_path,
        'ready': ready,
    }


def discover_trials(results_dir, subject_num=None, trial_type_filter=None):
    if not os.path.isdir(results_dir):
        return []

    trials_by_key = {}

    for sto_path in sorted(glob.glob(
            os.path.join(results_dir, '*_bilevel_solution_filtered.sto'))):
        parsed = parse_trial_from_sto(sto_path, subject_num, trial_type_filter)
        if not parsed:
            continue
        subj = parsed['subject_num']
        session = parsed['session']
        trial_type = parsed['trial_type']
        model_path = find_scaled_model(results_dir, subj, session, trial_type)
        key = (subj, session, trial_type)
        trials_by_key[key] = _trial_record(
            results_dir, subj, session, trial_type, sto_path, model_path)

    for model_path in sorted(glob.glob(
            os.path.join(results_dir, '*_bilevel_scaled.osim'))):
        fname = os.path.basename(model_path)
        m = OSIM_RE.match(fname)
        if not m:
            continue
        subj = int(m.group('subj'))
        if subject_num is not None and subj != subject_num:
            continue
        session = m.group('session')
        trial_type = m.group('trial')
        if trial_type_filter and trial_type.lower() != trial_type_filter.lower():
            continue
        key = (subj, session, trial_type)
        if key in trials_by_key:
            continue
        mot_path = os.path.join(
            results_dir, 'Kinematics', f'ID{subj}_S{session}_{trial_type}.mot')
        if not os.path.isfile(mot_path):
            continue
        trials_by_key[key] = _trial_record(
            results_dir, subj, session, trial_type, None, model_path)

    return list(trials_by_key.values())


def render_config_file(date, trial_info, settings):
    subj = trial_info['subject_num']
    session = trial_info['session']
    trial_type = trial_info['trial_type']
    trial_stem = trial_info['trial_stem']
    model_path = trial_info['model_path']
    results_dir = settings['RESULTS_DIR']
    filt_freq = settings['FILT_FREQ']
    lit_speeds = settings['LIT_SPEEDS']

    return f'''"""
Auto-generated config  [process_opencap_sprinting]
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
OPENPOSE_VARIANT = '{settings['OPENPOSE_VARIANT']}'
POST_AUG_FOLDER = '{settings['POST_AUG_FOLDER']}'
TRC_TIME_OFFSET = 'auto'
FILT_FREQ = {filt_freq}
COORD_FILTER_FREQ = {settings['COORD_FILTER_FREQ']}
MTU_LENGTH_FILTER_FREQ = {settings['MTU_LENGTH_FILTER_FREQ']}
DIST_THRESHOLD = {settings['DIST_THRESHOLD']}
LIT_SPEEDS = {lit_speeds!r}

DATA_DIR = r'{settings['DATA_DIR']}'
LOCAL_DIR = r'{settings['LOCAL_DIR']}'
RESULTS_DIR = r'{results_dir}'
LIT_DIR = os.path.join(LOCAL_DIR, 'LiteratureData')


def build_paths():
    trial_stem = '{trial_stem}'
    file_tag = trial_stem

    kinematics_input = os.path.join(RESULTS_DIR, 'Kinematics', f'{{trial_stem}}.mot')
    kinematics_filtered = os.path.join(
        RESULTS_DIR, 'Cleaned_Kinematics',
        f'{{trial_stem}}_filtered_{{FILT_FREQ}}Hz.mot')

    session_id = os.path.join(RESULTS_DIR, 'Cleaned_Kinematics')
    trial_name = f'{{trial_stem}}_filtered_{{FILT_FREQ}}Hz'
    outputs_dir = os.path.join(RESULTS_DIR, 'analysis', trial_stem)
    subject_dir = outputs_dir

    shank_angular_velocity_csv = os.path.join(
        outputs_dir, f'shank_ang_vel_{{file_tag}}.csv')
    step_times_left = os.path.join(outputs_dir, 'step_times_left.csv')
    step_times_right = os.path.join(outputs_dir, 'step_times_right.csv')

    normalized_bflh_csv = os.path.join(
        outputs_dir, f'norm_bflh_length_{{file_tag}}.csv')
    lit_lengths_file = os.path.join(LIT_DIR, 'BingYuBFLHLengths.csv')
    lit_velocities_file = os.path.join(LIT_DIR, 'BingYuBFLHVelocities.csv')
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
    stride_vel_output_dir = os.path.join(outputs_dir, 'stride_velocities')

    return {{
        'subject_dir': subject_dir,
        'trial_stem': trial_stem,
        'trial_name': trial_name,
        'file_tag': file_tag,
        'openpose_variant': OPENPOSE_VARIANT,
        'model_path': r'{model_path}',
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
        'kinematics_marker_sto': None,
        'post_augmentation_trc': None,
        'marker_errors_csv': os.path.join(
            outputs_dir, f'marker_errors_{{file_tag}}.csv'),
        'marker_errors_sto': os.path.join(
            outputs_dir, f'marker_errors_{{file_tag}}.sto'),
    }}


PATHS = build_paths()


def print_summary():
    print('=' * 60)
    print('Pipeline Configuration  [process-opencap-sprinting]')
    print('=' * 60)
    print(f'  Subject:        {{SUBJECT_NUM}}')
    print(f'  Date:           {{DATE}}')
    print(f'  Session:        {{SESSION}}')
    print(f'  Trial type:     {{TRIAL_TYPE}}')
    print(f'  Filter freq:    {{FILT_FREQ}} Hz')
    print(f'  Kin input:      {{PATHS["kinematics_input"]}}')
    print(f'  Model:          {{PATHS["model_path"]}}')
    print(f'  Outputs dir:    {{PATHS["outputs_dir"]}}')
    print('=' * 60)
'''


def collect_jobs(settings, dates=None, subjects=None):
    results_dir = settings['RESULTS_DIR']
    data_dir = settings['DATA_DIR']
    date_folders = list_date_folders(data_dir, dates)
    jobs = []
    seen = set()

    def add_jobs_for_trials(trials, date):
        for trial in trials:
            key = (trial['subject_num'], trial['session'], trial['trial_type'])
            if key in seen:
                continue
            seen.add(key)
            module = config_module_name(
                date, trial['subject_num'], trial['session'], trial['trial_type'])
            jobs.append({
                'date': date,
                'module': module,
                'config_path': config_file_path(
                    date, trial['subject_num'], trial['session'],
                    trial['trial_type']),
                **trial,
            })

    if date_folders:
        for date in date_folders:
            date_dir = os.path.join(data_dir, date)
            subject_nums = list_subject_dirs(date_dir)
            if subjects:
                subject_nums = [s for s in subject_nums if s in subjects]
            for subject_num in subject_nums:
                trials = discover_trials(
                    results_dir, subject_num, settings['TRIAL_TYPE_FILTER'])
                add_jobs_for_trials(trials, date)
    else:
        default_date = dates[0] if dates else settings['DEFAULT_DATE']
        trials = discover_trials(
            results_dir, subject_num=None,
            trial_type_filter=settings['TRIAL_TYPE_FILTER'])
        if subjects:
            trials = [t for t in trials if t['subject_num'] in subjects]
        add_jobs_for_trials(trials, default_date)

    return jobs


def prepare_kinematics(jobs, results_dir):
    from bilevel_sto_to_mot import ensure_bilevel_mot

    converted = []
    for job in jobs:
        if not job['ready']:
            continue
        if os.path.isfile(job['mot_path']) and not os.path.isfile(job['sto_path']):
            converted.append(job)
            continue
        try:
            mot_path = ensure_bilevel_mot(
                results_dir, job['trial_stem'], job['sto_path'])
            job['mot_path'] = mot_path
            converted.append(job)
        except FileNotFoundError as exc:
            print(f"WARNING: {exc}")
    return converted


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
        kin_label = (
            os.path.basename(job['sto_path'])
            if os.path.isfile(job['sto_path'])
            else os.path.basename(job['mot_path']))
        print(f"  [{status:15s}]  {job['date']:12s}  subject{job['subject_num']:2d}  "
              f"S{job['session']}  {job['trial_type']:10s}  {kin_label}")
        if not job['ready']:
            missing = []
            if not os.path.isfile(job['sto_path']) and not os.path.isfile(job['mot_path']):
                missing.append('bilevel .sto or Kinematics .mot')
            if not job['model_path']:
                missing.append('bilevel_scaled .osim')
            print(f"                    missing: {', '.join(missing)}")


def main():
    parser = argparse.ArgumentParser(
        description='Batch pipeline for process-opencap-sprinting bilevel results.')
    parser.add_argument('--date', action='append', metavar='FOLDER',
                        help='Collection day label for config naming (repeatable).')
    parser.add_argument('--subject', type=int, action='append', metavar='N',
                        help='Limit to subject number(s) (repeatable).')
    parser.add_argument('--trial-type', metavar='NAME',
                        help='Only include this trial type (e.g. sprint, fly).')
    parser.add_argument('--results-dir', metavar='PATH',
                        help=f"Results directory (default: {DEFAULTS['RESULTS_DIR']})")
    parser.add_argument('--generate-configs', action='store_true',
                        help='Write configs to process_opencap_sprinting/batch_configs/')
    parser.add_argument('--run', action='store_true',
                        help='Run process_opencap_sprinting/run_pipeline.py')
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
    if args.results_dir:
        settings['RESULTS_DIR'] = args.results_dir
    settings['TRIAL_TYPE_FILTER'] = args.trial_type

    jobs = collect_jobs(settings, dates=args.date, subjects=args.subject)
    ready_jobs = [j for j in jobs if j['ready']]
    not_ready = [j for j in jobs if not j['ready']]

    print_job_table(ready_jobs, 'Ready trials')
    print_job_table(not_ready, 'Trials missing bilevel STO or scaled model')

    if args.dry_run and not args.generate_configs and not args.run:
        print(f"\nDry run complete. {len(ready_jobs)} trial(s) ready.")
        return 0

    exit_code = 0

    if ready_jobs and (args.generate_configs or args.run):
        print(f"\nEnsuring STO -> MOT conversion in {settings['RESULTS_DIR']} ...")
        prepare_kinematics(ready_jobs, settings['RESULTS_DIR'])

    if args.generate_configs:
        written, skipped = generate_configs(ready_jobs, settings, overwrite=args.overwrite)
        print(f"\nGenerated {len(written)} config file(s) in:\n  {BATCH_CONFIG_DIR}")
        if skipped:
            print(f"Skipped {len(skipped)} (not ready or already exists; use --overwrite).")

    if args.run:
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
