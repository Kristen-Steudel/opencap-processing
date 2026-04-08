"""
Example: How to use ConfigManager with your scripts

This file demonstrates two approaches:

APPROACH 1: Config File (Best for systematic testing)
    python example_cleaned_with_config.py --config experiments/freq10Hz.yaml

APPROACH 2: Inline Parameters (Best for quick testing)
    python example_cleaned_with_config.py --mtu-freq 10 --exp-name freq10Hz

APPROACH 3: Original (Keep using hardcoded in example_cleaned.py)
    python example_cleaned.py
"""

import os
import sys
import argparse
import subprocess


def main():
    parser = argparse.ArgumentParser(
        description='Run example_cleaned.py with configurable parameters'
    )
    
    # Config options
    config_group = parser.add_argument_group('Configuration')
    config_group.add_argument(
        '--config',
        help='Path to YAML config file (e.g., experiments/freq10Hz.yaml)'
    )
    config_group.add_argument(
        '--mtu-freq',
        type=int,
        help='MTU length filter frequency in Hz (default: 10)'
    )
    config_group.add_argument(
        '--exp-name',
        help='Experiment name to use for output folder (default: from config)'
    )
    config_group.add_argument(
        '--show-config',
        action='store_true',
        help='Load config and print it without running'
    )
    
    args = parser.parse_args()
    
    # Import config manager
    from config_manager import ConfigManager
    
    # Load or create config
    if args.config:
        if not os.path.exists(args.config):
            print(f"❌ Config file not found: {args.config}")
            return 1
        config = ConfigManager.from_yaml(args.config)
    else:
        # Use defaults or override with args
        config_dict = {
            'experiment_name': args.exp_name or 'freq10Hz',
            'mtu_length_filter_freq': args.mtu_freq or 10,
            'filter_freq': 15,
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
    
    # Print config summary
    config.print_summary()
    
    if args.show_config:
        return 0
    
    # Extract config values - these will be used instead of hardcoded values
    mtu_filter_freq = config.get_mtu_filter_freq()
    output_dir = config.get_output_dir(exp_subfolder=True)
    
    print(f"\n✅ Config ready. Would run example_cleaned.py with:")
    print(f"   - MTU filter freq: {mtu_filter_freq} Hz")
    print(f"   - Output dir: {output_dir}")
    print(f"\nNOTE: To actually use this config in example_cleaned.py, modify that script")
    print(f"      to import and use ConfigManager (see config_supported_example/ for full example)")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
