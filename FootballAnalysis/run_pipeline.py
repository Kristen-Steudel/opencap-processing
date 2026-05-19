"""
FootballAnalysis/run_pipeline.py

Runs the full 8-step processing pipeline for Stanford Football subjects.
Configuration comes from pipeline_config.py in this folder.

Usage:
    python run_pipeline.py                  # run all steps
    python run_pipeline.py --steps 1 3 4    # run only steps 1, 3, 4
    python run_pipeline.py --list           # list available steps
"""

import argparse
import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

PIPELINE = [
    ('1', 'FilterKinematics.py',                'Filter raw kinematics'),
    ('2', 'example_cleaned.py',                 'Compute lengths, velocities, angles'),
    ('3', 'SeparateSteps.py',                   'Detect foot contacts / stride times'),
    ('4', 'compare_literature_bflh.py',         'Compare BFLH to Bing Yu literature'),
    ('5', 'compare_literature_bflh_nordsprint.py', 'Compare angles to NordSprint / Hamner'),
    ('6', 'CalcStepVelReedMethodWithFlags.py',  'Calculate stride velocities (Reed)'),
    ('7', 'PlotStrideKinematics.py',            'Plot all joint angles per stride'),
    ('8', 'PeakBFLHAngles.py',                 'Extract angles at peak BFLH length per stride'),
]


def run_step(step_id, script_file, description):
    script_path = os.path.join(SCRIPT_DIR, script_file)
    if not os.path.exists(script_path):
        print(f'  SKIP  {script_file} not found')
        return 1

    print(f"\n{'=' * 60}")
    print(f'  Step {step_id}: {description}')
    print(f'  Script: {script_file}')
    print(f"{'=' * 60}\n")

    result = subprocess.run([sys.executable, script_path], cwd=SCRIPT_DIR)
    if result.returncode == 0:
        print(f'\n  Step {step_id} completed successfully.')
    else:
        print(f'\n  Step {step_id} FAILED (exit code {result.returncode}).')
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description='Run the Football processing pipeline.')
    parser.add_argument('--steps', nargs='+', metavar='N',
                        help='Step numbers to run (default: all).')
    parser.add_argument('--list', action='store_true',
                        help='List available steps and exit')
    args = parser.parse_args()

    if args.list:
        print('Available pipeline steps:')
        for step_id, script, desc in PIPELINE:
            print(f'  {step_id}  {script:45s}  {desc}')
        return 0

    sys.path.insert(0, SCRIPT_DIR)
    import pipeline_config as cfg
    cfg.print_summary()

    steps = [(sid, sf, sd) for sid, sf, sd in PIPELINE
             if (args.steps is None or sid in args.steps)]
    if not steps:
        print(f'No matching steps for: {args.steps}')
        return 1

    print(f"\nSteps to run: {', '.join(s[0] for s in steps)}")

    results = {}
    for step_id, script_file, description in steps:
        results[step_id] = run_step(step_id, script_file, description)

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
    print(f'\nAll {len(steps)} step(s) completed successfully.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
