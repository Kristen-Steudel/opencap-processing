"""
Pipeline Runner: Execute data processing scripts with config file

This script orchestrates running the analysis pipeline with a specific configuration.
It ensures all downstream scripts use consistent parameters and output paths.

Usage:
    # Run with config file
    python run_pipeline.py --config experiments/freq10Hz.yaml --steps example_cleaned CalcStrideMaxLastThreeStrides
    
    # Run all steps defined in config
    python run_pipeline.py --config experiments/freq10Hz.yaml
    
    # Run single step
    python run_pipeline.py --config experiments/freq10Hz.yaml --steps example_cleaned
    
    # Quick test with inline parameters
    python run_pipeline.py --mtu-freq 10 --exp-name freq10Hz --steps example_cleaned
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from config_manager import ConfigManager


# Map friendly script names to actual script files
SCRIPT_MAP = {
    'example_cleaned': 'example_cleaned.py',
    'CalcStrideMaxLastThreeStrides': 'CalcStrideMaxLastThreeStrides.py',
    'generate_step_quality_checks': 'generate_step_quality_checks.py',
    'SeparateSteps': 'SeparateSteps.py',
    'CalcStepVelReedMethodWithFlags': 'CalcStepVelReedMethodWithFlags.py',
}


def run_script(script_name: str, config: ConfigManager, verbose: bool = True) -> int:
    """
    Run a single script with config.
    
    Args:
        script_name: Script to run (e.g., 'example_cleaned')
        config: ConfigManager instance
        verbose: Print output
    
    Returns:
        Exit code from script
    """
    script_file = SCRIPT_MAP.get(script_name)
    if not script_file:
        print(f"❌ Unknown script: {script_name}")
        print(f"   Available: {', '.join(SCRIPT_MAP.keys())}")
        return 1
    
    script_path = os.path.join(os.path.dirname(__file__), script_file)
    if not os.path.exists(script_path):
        print(f"❌ Script not found: {script_path}")
        return 1
    
    print(f"\n{'='*70}")
    print(f"Running: {script_name}")
    print(f"Experiment: {config.get_experiment_name()}")
    print(f"Output: {config.get_output_dir(exp_subfolder=True)}")
    print(f"{'='*70}\n")
    
    # Set environment variable so scripts can access config if needed
    os.environ['OPENCAP_CONFIG_FILE'] = config.config_file or 'inline'
    os.environ['OPENCAP_MTU_FILTER_FREQ'] = str(config.get_mtu_filter_freq())
    os.environ['OPENCAP_EXPERIMENT_NAME'] = config.get_experiment_name()
    os.environ['OPENCAP_OUTPUT_DIR'] = config.get_output_dir(exp_subfolder=True)
    
    # Run the script
    try:
        result = subprocess.run(
            ['python', script_path],
            capture_output=not verbose,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {script_name} completed successfully\n")
        else:
            print(f"❌ {script_name} failed with exit code {result.returncode}")
            if result.stderr:
                print(f"   Error: {result.stderr}")
        
        return result.returncode
    
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Run data processing pipeline with configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with config file
  python run_pipeline.py --config experiments/freq10Hz.yaml
  
  # Run specific steps
  python run_pipeline.py --config experiments/freq10Hz.yaml --steps example_cleaned CalcStrideMaxLastThreeStrides
  
  # Quick inline config (no file needed)
  python run_pipeline.py --mtu-freq 10 --exp-name mytest --steps example_cleaned
        """
    )
    
    # Config file options
    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument(
        '--config',
        help='Path to YAML config file (e.g., experiments/freq10Hz.yaml)'
    )
    config_group.add_argument(
        '--exp-name',
        help='Experiment name (for inline config, no file)'
    )
    config_group.add_argument(
        '--mtu-freq',
        type=int,
        help='MTU length filter frequency in Hz'
    )
    config_group.add_argument(
        '--filter-freq',
        type=int,
        help='Kinematics filter frequency in Hz'
    )
    
    # Execution options
    exec_group = parser.add_argument_group('Execution')
    exec_group.add_argument(
        '--steps',
        nargs='+',
        help=f'Scripts to run. Available: {", ".join(SCRIPT_MAP.keys())}'
    )
    exec_group.add_argument(
        '--list-scripts',
        action='store_true',
        help='List available scripts and exit'
    )
    exec_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would run without executing'
    )
    exec_group.add_argument(
        '--verbose',
        action='store_true',
        default=True,
        help='Print script output (default: True)'
    )
    
    args = parser.parse_args()
    
    # List scripts and exit
    if args.list_scripts:
        print("Available scripts:")
        for name, script_file in SCRIPT_MAP.items():
            print(f"  {name:40s} ({script_file})")
        return 0
    
    # Load or create config
    if args.config:
        if not os.path.exists(args.config):
            print(f"❌ Config file not found: {args.config}")
            return 1
        config = ConfigManager.from_yaml(args.config)
        print(f"✅ Loaded config: {args.config}")
    else:
        # Build config from inline arguments
        if not args.exp_name:
            print("❌ Either --config file or --exp-name required")
            return 1
        
        config_dict = {
            'experiment_name': args.exp_name,
            'mtu_length_filter_freq': args.mtu_freq or 10,
            'filter_freq': args.filter_freq or 15,
            'coord_filter_freq': 10,
            'subject_num': 2,
            'date': 'March_2',
            'session': '7',
            'type': 'sprint',
            'paths': {
                'base': 'G:/Shared drives/Stanford Football',
                'output_base': 'Outputs'
            }
        }
        config = ConfigManager.from_dict(config_dict)
        print(f"✅ Created inline config: {args.exp_name}")
    
    # Print config summary
    config.print_summary()
    
    # Determine which steps to run
    steps_to_run = args.steps or config.get('scripts', ['example_cleaned'])
    
    print(f"\nSteps to run: {', '.join(steps_to_run)}")
    
    if args.dry_run:
        print("\n[DRY RUN] Would execute:")
        for step in steps_to_run:
            print(f"  - {step}")
        return 0
    
    # Run each step
    failed_steps = []
    for step in steps_to_run:
        exit_code = run_script(step, config, verbose=args.verbose)
        if exit_code != 0:
            failed_steps.append(step)
    
    # Summary
    print(f"\n{'='*70}")
    print("Pipeline Summary")
    print(f"{'='*70}")
    print(f"Total steps: {len(steps_to_run)}")
    print(f"Successful: {len(steps_to_run) - len(failed_steps)}")
    print(f"Failed: {len(failed_steps)}")
    
    if failed_steps:
        print(f"\n❌ Failed steps: {', '.join(failed_steps)}")
        return 1
    else:
        print(f"\n✅ All steps completed successfully!")
        print(f"Output directory: {config.get_output_dir(exp_subfolder=True)}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
