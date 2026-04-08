# Data Processing Pipeline: Two Approaches

This guide shows you two methods for managing experiments with different parameters, keeping all results organized for comparison.

---

## Quick Comparison

| Aspect | Config File Approach | Hardcoded Approach |
|--------|----------------------|-------------------|
| **Setup** | 5 min - one-time | 1 min - per-change |
| **Flexibility** | Excellent - easy to create new variation | Medium - edit each script |
| **Reproducibility** | ✅ Great - configs are version-controllable | ⚠️ Risk of forgetting changes |
| **Batch Running** | ✅ Easy - run multiple experiments | ❌ Manual - run scripts one by one |
| **Output Organization** | ✅ Auto-organized by experiment name | ⚠️ Manual - risk of overwrites |
| **Best For** | Systematic testing 5-20+ combinations | Quick one-off tests |

---

## Approach 1: Config File System (RECOMMENDED)

### Setup (One-time)

The system is already set up! Files created:
- `config_manager.py` - Core utility
- `experiments/freq5Hz.yaml` - Baseline config
- `experiments/freq10Hz.yaml` - New test config
- `run_pipeline.py` - Pipeline orchestrator
- `example_cleaned_with_config.py` - Example integration

### Usage

**Option 1a: Run with pipeline runner (SIMPLEST)**
```bash
# Run single script with config
conda run python run_pipeline.py --config experiments/freq10Hz.yaml --steps example_cleaned

# Run full pipeline
conda run python run_pipeline.py --config experiments/freq10Hz.yaml

# Run multiple experiments (compare both)
conda run python run_pipeline.py --config experiments/freq5Hz.yaml --steps CalcStrideMaxLastThreeStrides
conda run python run_pipeline.py --config experiments/freq10Hz.yaml --steps CalcStrideMaxLastThreeStrides
```

**Option 1b: Inline config (no YAML file needed)**
```bash
# Quick test with parameters (no config file)
conda run python run_pipeline.py \
  --mtu-freq 12 \
  --exp-name freq12Hz \
  --steps example_cleaned
```

**Option 1c: Direct script with config**
```bash
# For single script testing
conda run python example_cleaned_with_config.py --config experiments/freq10Hz.yaml --show-config
```

### Output Structure

Outputs auto-organized by experiment:
```
Outputs/
  freq5Hz/
    bflh_mtu_max_steps_*.csv
    *.png
  freq10Hz/
    bflh_mtu_max_steps_*.csv
    *.png
```

### How to Add New Experiments

1. Copy existing config:
   ```bash
   cp experiments/freq10Hz.yaml experiments/freq7Hz.yaml
   ```

2. Edit `freq7Hz.yaml`:
   ```yaml
   experiment_name: freq7Hz
   mtu_length_filter_freq: 7
   ```

3. Run:
   ```bash
   conda run python run_pipeline.py --config experiments/freq7Hz.yaml
   ```

### Integrating Your Scripts (Future Refinement)

To make your scripts read from config automatically:

In `CalcStrideMaxLastThreeStrides.py`, add at top:
```python
from config_manager import ConfigManager
import os

# Try to load config from environment (set by pipeline runner)
config_file = os.environ.get('OPENCAP_CONFIG_FILE')
if config_file and config_file != 'inline':
    config = ConfigManager.from_yaml(config_file)
    mtu_length_filter_freq = config.get_mtu_filter_freq()
    output_dir = config.get_output_dir(exp_subfolder=True)
else:
    # Fallback to defaults or hardcoded values
    mtu_length_filter_freq = 10
    output_dir = "Outputs/freq10Hz"
```

Then get file paths from config:
```python
# Instead of: output_file = "G:/Shared.../Outputs/bflh_mtu_max_steps_..."
# Use:
output_file = config.get_csv_output_path('bflh_mtu_max_steps_ID2_S7_sprint_LSTM_filtered.csv')
```

---

## Approach 2: Hardcoded (Current Method)

### For Quick Testing

**Step 1: Edit example_cleaned.py**
```python
mtu_length_filter_freq = 10  # Change from 5 to 10
```

**Step 2: Change output folder**
Find and update this line:
```python
output_csv_dir = os.path.join(..., 'Outputs', 'freq10Hz')  # Add subfolder
```

**Step 3: Run**
```bash
conda run python example_cleaned.py
```

### Output Structure (Manual Management)
```
Outputs/
  bflh_mtu_max_steps_*.csv         # freq5Hz results (old)
  bflh_mtu_max_steps_*.csv         # freq10Hz results - BE CAREFUL OF OVERWRITES!
```

### Risks
- ❌ Easy to forget which parameter was used
- ❌ Easy to accidentally overwrite results
- ❌ Hard to reproduce past experiments
- ❌ Need to manually track which version is which

---

## Recommended Workflow for You

Since you want to test 5-20 variations and keep results:

### Phase 1: Quick Start (This Week)
1. Use **Approach 1 (Config)** for new tests
2. Keep **Approach 2 (Hardcoded)** for quick tweaks
3. Run parallel experiments with different configs

Example:
```bash
# Terminal 1: Test freq10Hz
conda run python run_pipeline.py --config experiments/freq10Hz.yaml --steps example_cleaned

# Terminal 2 (another window): Test freq7Hz  
conda run python run_pipeline.py --config experiments/freq7Hz.yaml --steps example_cleaned

# Then compare outputs in Outputs/freq10Hz vs Outputs/freq7Hz
```

### Phase 2: Full Integration (Next Week)
- Modify your scripts to read from config (see section above)
- Run full pipelines: `python run_pipeline.py --config experiments/freq10Hz.yaml`
- All 4 scripts automatically use same parameters/paths

### Phase 3: Batch Comparison
```bash
# Auto-run multiple experiments
for freq in 5 7 10 12 15; do
  python run_pipeline.py --config experiments/freq${freq}Hz.yaml --steps CalcStrideMaxLastThreeStrides
done
```

Then compare all results in:
```
Outputs/freq5Hz/
Outputs/freq7Hz/
Outputs/freq10Hz/
...
```

---

## Getting File Paths for Downstream Scripts

### Method 1: From Config (Current System)
```python
from config_manager import ConfigManager

config = ConfigManager.from_yaml('experiments/freq10Hz.yaml')

# Get paths
output_dir = config.get_output_dir(exp_subfolder=True)        # Full output path
csv_file = config.get_csv_output_path('bflh_mtu_max_steps_ID2_S7_sprint_LSTM_filtered.csv')
trial_name = config.get_trial_name()
```

### Method 2: From Environment (Set by run_pipeline.py)
```python
import os

# When running via run_pipeline.py, these are set automatically:
output_dir = os.environ.get('OPENCAP_OUTPUT_DIR')
mtu_freq = int(os.environ.get('OPENCAP_MTU_FILTER_FREQ'))
experiment = os.environ.get('OPENCAP_EXPERIMENT_NAME')
```

### Method 3: From Command Line Arguments
```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', help='Output directory')
parser.add_argument('--config', help='Config file')
args = parser.parse_args()

if args.config:
    from config_manager import ConfigManager
    config = ConfigManager.from_yaml(args.config)
    output_dir = config.get_output_dir(exp_subfolder=True)
```

---

## Example: Using Both Approaches Today

### Quick Test 1: Original approach (existing workflow)
```bash
# Edit example_cleaned.py: mtu_length_filter_freq = 5
conda run python example_cleaned.py
# Results go to: Outputs/freq5Hz/ (if you add subfolder)
```

### Quick Test 2: Config approach (new workflow)  
```bash
# Use config file (no code edits needed)
conda run python run_pipeline.py --config experiments/freq10Hz.yaml --steps example_cleaned
# Results go to: Outputs/freq10Hz/ (automatically organized)
```

### Results
Both outputs coexist:
```
Outputs/
  freq5Hz/
    bflh_mtu_max_steps_ID2_S7_sprint_LSTM_filtered.csv
    plots/
  freq10Hz/
    bflh_mtu_max_steps_ID2_S7_sprint_LSTM_filtered.csv
    plots/
```

Easy to compare: both versions saved, organized by experiment name.

---

## Available Commands Reference

### Pipeline Runner
```bash
# Show help
conda run python run_pipeline.py --help

# List available scripts
conda run python run_pipeline.py --list-scripts

# Run with config
conda run python run_pipeline.py --config experiments/freq10Hz.yaml

# Run specific steps
conda run python run_pipeline.py --config experiments/freq10Hz.yaml --steps example_cleaned CalcStrideMaxLastThreeStrides

# Dry run (show what would execute)
conda run python run_pipeline.py --config experiments/freq10Hz.yaml --dry-run

# Inline config (no YAML file)
conda run python run_pipeline.py --mtu-freq 10 --exp-name freq10Hz --steps example_cleaned
```

### Example Script
```bash
# Show config without running
conda run python example_cleaned_with_config.py --config experiments/freq10Hz.yaml --show-config

# With inline parameters
conda run python example_cleaned_with_config.py --mtu-freq 10 --exp-name freq10Hz
```

---

## Troubleshooting

**Q: Config file not found?**
- Check path: `experiments/freq10Hz.yaml` (relative to repo root)
- Or use full path: `python run_pipeline.py --config C:\full\path\experiments\freq10Hz.yaml`

**Q: Scripts can't find outputs?**
- Config creates subdirectories automatically
- Check actual output path: `python run_pipeline.py --config experiments/freq10Hz.yaml --show-config`

**Q: Want to change experiment later?**
- Edit config file (YAML) - don't need to edit Python scripts
- Create new config file for new variation

**Q: Outputs going to wrong place?**
- Override in config file's `paths` section
- Or use `--output-base` argument to pipeline runner
