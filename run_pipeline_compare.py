"""
run_pipeline_compare.py

Runs the full 8-step pipeline on the OpenCap trial (pipeline_config_OpenCap),
then runs Step 9 (CompareTrials.py) to compare that trial against the OpenPose
trial defined in pipeline_config_CameraTest.

The individual pipeline scripts (steps 1–8) pick up their config via the
PIPELINE_CONFIG environment variable, so no script edits are needed.

Usage:
    python run_pipeline_compare.py                  # run all steps (1–9)
    python run_pipeline_compare.py --steps 2 3 4    # run specific steps
    python run_pipeline_compare.py --steps 9        # comparison only
    python run_pipeline_compare.py --list           # list steps
"""

import argparse
import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Config name passed to the individual pipeline scripts via env var
OPENCAP_CONFIG = 'pipeline_config_OpenCap'

# Steps 1–8 run the standard scripts under the OpenCap config.
# Step 9 runs CompareTrials.py which imports both configs internally.
PIPELINE = [
    ('1', 'FilterKinematics.py',                'Filter raw kinematics  [OpenCap]'),
    ('2', 'example_cleaned.py',                 'Compute MTU lengths/velocities  [OpenCap]'),
    ('3', 'SeparateSteps.py',                   'Detect foot contacts / stride times  [OpenCap]'),
    ('4', 'compare_literature_bflh.py',         'Compare BFLH to literature  [OpenCap]'),
    ('5', 'compare_literature_bflh_nordsprint.py', 'Compare angles to NordSprint  [OpenCap]'),
    ('6', 'CalcStepVelReedMethodWithFlags.py',  'Calculate stride velocities  [OpenCap]'),
    ('7', 'PlotStrideKinematics.py',            'Plot all joint angles per stride  [OpenCap]'),
    ('8', 'PeakBFLHAngles.py',                 'Extract angles at peak BFLH length  [OpenCap]'),
    ('9', 'CompareTrials.py',                   'Compare OpenCap vs OpenPose kinematics & BFLH'),
]


def run_step(step_id, script_file, description, config_name=None):
    """Run one pipeline step as a subprocess, optionally injecting config."""
    script_path = os.path.join(SCRIPT_DIR, script_file)
    if not os.path.exists(script_path):
        print(f'  SKIP  {script_file} not found')
        return 1

    print(f"\n{'=' * 60}")
    print(f'  Step {step_id}: {description}')
    print(f'  Script: {script_file}')
    if config_name:
        print(f'  Config: {config_name}')
    print(f"{'=' * 60}\n")

    env = dict(os.environ)
    if config_name:
        env['PIPELINE_CONFIG'] = config_name

    result = subprocess.run([sys.executable, script_path], cwd=SCRIPT_DIR, env=env)
    if result.returncode == 0:
        print(f'\n  Step {step_id} completed successfully.')
    else:
        print(f'\n  Step {step_id} FAILED (exit code {result.returncode}).')
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description='Run the OpenCap pipeline and compare to OpenPose trial.')
    parser.add_argument(
        '--steps', nargs='+', metavar='N',
        help='Step numbers to run (default: all). E.g. --steps 1 3 9')
    parser.add_argument(
        '--list', action='store_true',
        help='List available steps and exit')
    args = parser.parse_args()

    if args.list:
        print('Available pipeline steps:')
        for step_id, script, desc in PIPELINE:
            print(f'  {step_id}  {script:50s}  {desc}')
        return 0

    # Print config summaries
    sys.path.insert(0, SCRIPT_DIR)
    import pipeline_config_OpenCap    as cfg_oc
    import pipeline_config_CameraTest as cfg_op
    print('\n--- Trial being processed through steps 1–8 ---')
    cfg_oc.print_summary()
    print('\n--- Trial used as comparison in step 9 ---')
    cfg_op.print_summary()

    # Select steps
    if args.steps:
        steps = [(sid, sf, sd) for sid, sf, sd in PIPELINE if sid in args.steps]
        if not steps:
            print(f'No matching steps for: {args.steps}')
            print('Use --list to see available step numbers.')
            return 1
    else:
        steps = PIPELINE

    print(f"\nSteps to run: {', '.join(s[0] for s in steps)}")

    results = {}
    for step_id, script_file, description in steps:
        # Step 9 imports both configs directly — no env var injection needed.
        config = OPENCAP_CONFIG if step_id != '9' else None
        results[step_id] = run_step(step_id, script_file, description, config)

    # Summary
    print(f"\n{'=' * 60}")
    print('Pipeline Summary')
    print(f"{'=' * 60}")
    for step_id, script_file, description in steps:
        status = 'OK' if results[step_id] == 0 else 'FAILED'
        print(f'  Step {step_id}: {status:6s}  {description}')

    failed = [sid for sid, rc in results.items() if rc != 0]
    if failed:
        print(f'\n{len(failed)} step(s) failed: {", ".join(failed)}')
        return 1
    else:
        print(f'\nAll {len(steps)} step(s) completed successfully.')
        return 0


if __name__ == '__main__':
    sys.exit(main())
