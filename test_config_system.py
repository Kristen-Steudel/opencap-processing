"""
Quick test of config system
Run: python test_config_system.py
"""

import os
from config_manager import ConfigManager


def test_config_system():
    """Test that config system works correctly."""
    
    print("=" * 70)
    print("Testing Config System")
    print("=" * 70)
    
    # Test 1: Load freq5Hz config
    print("\n[Test 1] Loading freq5Hz.yaml...")
    try:
        config5 = ConfigManager.from_yaml('experiments/freq5Hz.yaml')
        config5.print_summary()
        assert config5.get_mtu_filter_freq() == 5, "MTU freq should be 5"
        print("✅ PASS: freq5Hz config loaded correctly\n")
    except Exception as e:
        print(f"❌ FAIL: {e}\n")
        return False
    
    # Test 2: Load freq10Hz config
    print("[Test 2] Loading freq10Hz.yaml...")
    try:
        config10 = ConfigManager.from_yaml('experiments/freq10Hz.yaml')
        config10.print_summary()
        assert config10.get_mtu_filter_freq() == 10, "MTU freq should be 10"
        print("✅ PASS: freq10Hz config loaded correctly\n")
    except Exception as e:
        print(f"❌ FAIL: {e}\n")
        return False
    
    # Test 3: Inline config creation
    print("[Test 3] Creating inline config...")
    try:
        config_inline = ConfigManager.from_dict({
            'experiment_name': 'testFreq7Hz',
            'mtu_length_filter_freq': 7,
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
        })
        config_inline.print_summary()
        assert config_inline.get_mtu_filter_freq() == 7, "MTU freq should be 7"
        print("✅ PASS: Inline config created correctly\n")
    except Exception as e:
        print(f"❌ FAIL: {e}\n")
        return False
    
    # Test 4: Output paths are different for each config
    print("[Test 4] Verifying output paths are unique...")
    try:
        out5 = config5.get_output_dir(exp_subfolder=True)
        out10 = config10.get_output_dir(exp_subfolder=True)
        
        assert 'freq5Hz' in out5, f"freq5Hz should be in path: {out5}"
        assert 'freq10Hz' in out10, f"freq10Hz should be in path: {out10}"
        assert out5 != out10, "Output dirs should be different"
        
        print(f"  freq5Hz output:  {out5}")
        print(f"  freq10Hz output: {out10}")
        print("✅ PASS: Output paths are unique\n")
    except Exception as e:
        print(f"❌ FAIL: {e}\n")
        return False
    
    # Test 5: Get trial names
    print("[Test 5] Verifying trial names...")
    try:
        trial5 = config5.get_trial_name()
        trial10 = config10.get_trial_name()
        
        print(f"  freq5Hz trial:  {trial5}")
        print(f"  freq10Hz trial: {trial10}")
        print("✅ PASS: Trial names generated\n")
    except Exception as e:
        print(f"❌ FAIL: {e}\n")
        return False
    
    # Test 6: CSV output paths
    print("[Test 6] Verifying CSV output paths...")
    try:
        csv_path = config10.get_csv_output_path('test_results.csv')
        print(f"  CSV path: {csv_path}")
        assert 'freq10Hz' in csv_path, "freq10Hz should be in CSV path"
        assert 'test_results.csv' in csv_path, "Filename should be in path"
        print("✅ PASS: CSV paths generated correctly\n")
    except Exception as e:
        print(f"❌ FAIL: {e}\n")
        return False
    
    print("=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print("\nConfig system is ready to use. Examples:")
    print("\n  1. List available scripts:")
    print("     python run_pipeline.py --list-scripts")
    print("\n  2. Run with config file:")
    print("     python run_pipeline.py --config experiments/freq10Hz.yaml --steps example_cleaned")
    print("\n  3. Dry run to see what would execute:")
    print("     python run_pipeline.py --config experiments/freq10Hz.yaml --dry-run")
    print("\n  4. Create new experiment variation:")
    print("     cp experiments/freq10Hz.yaml experiments/freq7Hz.yaml")
    print("     # Edit freq7Hz.yaml: change mtu_length_filter_freq to 7")
    print("     python run_pipeline.py --config experiments/freq7Hz.yaml --steps example_cleaned")
    print("\n" + "=" * 70)
    
    return True


if __name__ == '__main__':
    success = test_config_system()
    exit(0 if success else 1)
