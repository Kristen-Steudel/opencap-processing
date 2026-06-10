"""
process_opencap_sprinting/run_pipeline.py

Runs the stride-analysis pipeline for bilevel optimization results.
Reuses step scripts from the parent BatchProcessing/ folder but loads
generated configs from this folder's batch_configs/ only.

Usage:
    cd BatchProcessing/process_opencap_sprinting

    python run_pipeline.py --config pipeline_config_sprinting_ID2_S7_sprint
    python run_pipeline.py --config pipeline_config_sprinting_ID2_S7_sprint --steps 1 2 3
"""

import argparse
import importlib
import os
import runpy
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(PARENT_DIR)
CONFIG_DIR = os.path.join(SCRIPT_DIR, 'batch_configs')

PIPELINE = [
    ('1', 'FilterKinematics.py',                'Filter raw kinematics'),
    ('2', 'example_cleaned.py',                 'Compute lengths, velocities, angles'),
    ('3', 'SeparateSteps.py',                   'Detect foot contacts / stride times'),
    ('4', 'compare_literature_bflh.py',         'Compare BFLH to Bing Yu literature'),
    ('5', 'compare_literature_bflh_nordsprint.py', 'Compare angles to NordSprint / Hamner'),
    ('6', 'CalcStepVelReedMethodWithFlags.py',  'Calculate stride velocities (Reed)'),
    ('7', 'PlotStrideKinematics.py',            'Plot all joint angles per stride'),
    ('8', 'PeakBFLHAngles.py',                 'Extract angles at peak BFLH length per stride'),
    ('9', 'ComputeMarkerErrors.py',            'Marker error: IK marker STO vs post-augmentation TRC'),
]


def _resolve_script(script_file):
    if script_file == 'example_cleaned.py':
        return os.path.join(SCRIPT_DIR, script_file)
    return os.path.join(PARENT_DIR, script_file)


def _preload_config(config_name):
    """Load config from this folder before parent scripts adjust sys.path."""
    if config_name in sys.modules:
        del sys.modules[config_name]
    for path in (CONFIG_DIR, REPO_ROOT, PARENT_DIR):
        if path not in sys.path:
            sys.path.insert(0, path)
    return importlib.import_module(config_name)


def run_step(step_id, script_file, description, config_name):
    script_path = _resolve_script(script_file)
    if not os.path.exists(script_path):
        print(f'  SKIP  {script_file} not found')
        return 1

    print(f"\n{'=' * 60}")
    print(f'  Step {step_id}: {description}')
    print(f'  Script: {script_path}')
    if config_name:
        print(f'  Config: {config_name}')
    print(f"{'=' * 60}\n")

    os.environ['PIPELINE_CONFIG'] = config_name
    _preload_config(config_name)

    cwd = SCRIPT_DIR if script_file == 'example_cleaned.py' else PARENT_DIR
    try:
        runpy.run_path(script_path, run_name='__main__')
        print(f'\n  Step {step_id} completed successfully.')
        return 0
    except SystemExit as exc:
        code = exc.code if exc.code is not None else 0
        if code == 0:
            print(f'\n  Step {step_id} completed successfully.')
        else:
            print(f'\n  Step {step_id} FAILED (exit code {code}).')
        return code
    except Exception:
        print(f'\n  Step {step_id} FAILED.')
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Run the process-opencap-sprinting stride-analysis pipeline.')
    parser.add_argument('--steps', nargs='+', metavar='N',
                        help='Step numbers to run (default: all).')
    parser.add_argument('--list', action='store_true',
                        help='List available steps and exit')
    parser.add_argument(
        '--config', required=True, metavar='MODULE',
        help='Config module name from process_opencap_sprinting/batch_configs/.')
    args = parser.parse_args()

    if args.list:
        print('Available pipeline steps:')
        for step_id, script, desc in PIPELINE:
            print(f'  {step_id}  {script:45s}  {desc}')
        return 0

    config_name = args.config.removesuffix('.py')
    cfg = _preload_config(config_name)
    cfg.print_summary()

    steps = [(sid, sf, sd) for sid, sf, sd in PIPELINE
             if (args.steps is None or sid in args.steps)]
    if not steps:
        print(f'No matching steps for: {args.steps}')
        return 1

    print(f"\nSteps to run: {', '.join(s[0] for s in steps)}")

    results = {}
    for step_id, script_file, description in steps:
        results[step_id] = run_step(
            step_id, script_file, description, config_name)

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
