"""
Config Manager for OpenCap Processing Pipeline

Handles loading and managing experiment configurations.
Allows scripts to use either:
  1. Config files (YAML) for structured experiment management
  2. Direct parameter passing for quick prototyping

Usage:
    from config_manager import ConfigManager
    
    # Load from config file
    config = ConfigManager('experiments/freq10Hz.yaml')
    
    # Or create programmatically
    config = ConfigManager.from_dict({
        'mtu_length_filter_freq': 10,
        'experiment_name': 'freq10Hz',
        ...
    })
    
    # Get paths
    output_dir = config.get_output_dir()
    kinematics_file = config.get_kinematics_file()
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Load and manage experiment configurations."""
    
    def __init__(self, config_file: Optional[str] = None, config_dict: Optional[Dict] = None):
        """
        Initialize ConfigManager.
        
        Args:
            config_file: Path to YAML config file
            config_dict: Dictionary with config (used if config_file is None)
        """
        self.config = {}
        self.config_file = config_file
        
        if config_file and os.path.exists(config_file):
            self.load_from_yaml(config_file)
        elif config_dict:
            self.config = config_dict
        else:
            # Load default config
            self._load_defaults()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ConfigManager':
        """Create ConfigManager from dictionary."""
        cm = cls(config_dict=config_dict)
        return cm
    
    @classmethod
    def from_yaml(cls, yaml_file: str) -> 'ConfigManager':
        """Create ConfigManager from YAML file."""
        return cls(config_file=yaml_file)
    
    def load_from_yaml(self, config_file: str):
        """Load configuration from YAML file."""
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
        self.config_file = config_file
    
    def _load_defaults(self):
        """Load default configuration."""
        self.config = {
            'experiment_name': 'default',
            'mtu_length_filter_freq': 10,
            'filter_freq': 15,
            'coord_filter_freq': 10,
            'enable_mtu_filter_diagnostics': False,
            'subject_num': 2,
            'date': 'March_2',
            'session': '7',
            'type': 'sprint',
            'paths': {
                'base': 'G:/Shared drives/Stanford Football',
                'output_base': 'Outputs'
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by key (supports dot notation: 'paths.base')."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value if value is not None else default
    
    def get_mtu_filter_freq(self) -> int:
        """Get MTU length filter frequency."""
        return self.get('mtu_length_filter_freq', 10)
    
    def get_filter_freq(self) -> int:
        """Get filter frequency."""
        return self.get('filter_freq', 15)
    
    def get_coord_filter_freq(self) -> int:
        """Get coordinate filter frequency."""
        return self.get('coord_filter_freq', 10)
    
    def get_experiment_name(self) -> str:
        """Get experiment name."""
        return self.get('experiment_name', 'default')
    
    def get_subject_num(self) -> int:
        """Get subject number."""
        return self.get('subject_num', 2)
    
    def get_session_num(self) -> str:
        """Get session number."""
        return str(self.get('session', '7'))
    
    def get_session_type(self) -> str:
        """Get session type (e.g., 'sprint')."""
        return self.get('type', 'sprint')
    
    def get_date(self) -> str:
        """Get date."""
        return self.get('date', 'March_2')
    
    def get_output_dir(self, exp_subfolder: bool = True) -> str:
        """
        Get output directory.
        
        Args:
            exp_subfolder: If True, append experiment_name as subfolder
        
        Returns:
            Path to output directory
        """
        base_path = self.get('paths.base', 'G:/Shared drives/Stanford Football')
        date = self.get_date()
        subject_num = self.get_subject_num()
        
        output_base = self.get('paths.output_base', 'Outputs')
        
        # Build path: {base}/{date}/subject{num}/CleanedKinematics/filtered_post_augmentation/Outputs
        output_dir = os.path.normpath(
            os.path.join(
                base_path,
                date,
                f'subject{subject_num}',
                'CleanedKinematics',
                'filtered_post_augmentation',
                output_base
            )
        )
        
        # Add experiment subfolder if requested
        if exp_subfolder:
            exp_name = self.get_experiment_name()
            output_dir = os.path.join(output_dir, exp_name)
            os.makedirs(output_dir, exist_ok=True)
        
        return output_dir
    
    def get_session_id(self) -> str:
        """Get session ID path."""
        base_path = self.get('paths.base', 'G:/Shared drives/Stanford Football')
        date = self.get_date()
        subject_num = self.get_subject_num()
        
        session_id = os.path.normpath(
            os.path.join(
                base_path,
                date,
                f'subject{subject_num}',
                'CleanedKinematics',
                'filtered_post_augmentation'
            )
        )
        return session_id
    
    def get_trial_name(self) -> str:
        """Get trial name based on config parameters."""
        subject_num = self.get_subject_num()
        session = self.get_session_num()
        session_type = self.get_session_type()
        filter_freq = self.get_filter_freq()
        
        return f'ID{subject_num}_S{session}_{session_type}_LSTM_filtpostaug{filter_freq}Hz_filteredkinematics_{filter_freq}Hz'
    
    def get_csv_output_path(self, filename: str) -> str:
        """Get full path for CSV output file."""
        output_dir = self.get_output_dir(exp_subfolder=True)
        return os.path.join(output_dir, filename)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export config as dictionary."""
        return self.config.copy()
    
    def to_yaml(self, output_file: str):
        """Export config to YAML file."""
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        with open(output_file, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
    
    def print_summary(self):
        """Print config summary."""
        print("=" * 60)
        print(f"Experiment: {self.get_experiment_name()}")
        print("=" * 60)
        print(f"MTU Length Filter Freq: {self.get_mtu_filter_freq()} Hz")
        print(f"Filter Freq: {self.get_filter_freq()} Hz")
        print(f"Coord Filter Freq: {self.get_coord_filter_freq()} Hz")
        print(f"Subject: {self.get_subject_num()}")
        print(f"Session: {self.get_session_num()}")
        print(f"Type: {self.get_session_type()}")
        print(f"Date: {self.get_date()}")
        print(f"Output Dir: {self.get_output_dir(exp_subfolder=True)}")
        print(f"Trial Name: {self.get_trial_name()}")
        print("=" * 60)
