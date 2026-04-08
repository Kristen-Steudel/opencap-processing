# Quick Reference: Config System

## What's New

You now have **two working approaches** for managing experiments:

### Approach 1: Config Files ⭐ (Recommended)
**Best for:** Systematic testing, keeping multiple results, comparing variations

```bash
# Run with config file (experiment name + params auto-managed)
conda run python run_pipeline.py --config experiments/freq10Hz.yaml --steps example_cleaned

# Run full pipeline (all scripts in sequence)
conda run python run_pipeline.py --config experiments/freq10Hz.yaml

# Dry run - see what would execute without running
conda run python run_pipeline.py --config experiments/freq10Hz.yaml --dry-run
```

**Output:** `Outputs/freq10Hz/` (auto-organized by experiment)

### Approach 2: Hardcoded (Original) ✓ (Still works)
**Best for:** Quick tests, single tweaks

```bash
# Edit parameters in example_cleaned.py, then run
mtu_length_filter_freq = 10
conda run python example_cleaned.py
```

**Output:** Depends on your hardcoded paths

---

## Files Created

| File | Purpose |
|------|---------|
| `config_manager.py` | Core config loading utility |
| `run_pipeline.py` | Orchestrate multi-script runs |
| `experiments/freq5Hz.yaml` | Config for 5 Hz filter (baseline) |
| `experiments/freq10Hz.yaml` | Config for 10 Hz filter (your test) |
| `example_cleaned_with_config.py` | Shows how to integrate config with scripts |
| `test_config_system.py` | Validates the system works |
| `CONFIG_GUIDE.md` | Full documentation |

---

## Most Common Tasks

### Create New Experiment Variation
```bash
# Copy existing config
cp experiments/freq10Hz.yaml experiments/freq7Hz.yaml

# Edit freq7Hz.yaml: change mtu_length_filter_freq: 10 → 7

# Run
conda run python run_pipeline.py --config experiments/freq7Hz.yaml
```

### Run Your 4 Scripts with Same Config
```bash
# All 4 scripts will use freq10Hz parameters + output folder
conda run python run_pipeline.py --config experiments/freq10Hz.yaml \
  --steps example_cleaned CalcStrideMaxLastThreeStrides SeparateSteps CalcStepVelReedMethodWithFlags
```

### Compare Results Side-by-Side
```bash
# Outputs automatically organized:
# Outputs/freq5Hz/result.csv
# Outputs/freq10Hz/result.csv
# → Easy to compare both versions!
```

### Run Single Script from Config
```bash
conda run python run_pipeline.py --config experiments/freq10Hz.yaml --steps CalcStrideMaxLastThreeStrides
```

### Quick Test (No Config File Needed)
```bash
# Inline parameters - creates experiment on the fly
conda run python run_pipeline.py --mtu-freq 12 --exp-name freq12Hz --steps example_cleaned
```

---

## Getting File Paths in Your Scripts (Future)

When you're ready to integrate, add this to top of your scripts:

```python
from config_manager import ConfigManager
import os

# Try config from config system
config_file = os.environ.get('OPENCAP_CONFIG_FILE')
if config_file:
    config = ConfigManager.from_yaml(config_file)
    mtu_filter_freq = config.get_mtu_filter_freq()
    output_dir = config.get_output_dir(exp_subfolder=True)
else:
    # Fallback
    mtu_filter_freq = 10
    output_dir = "Outputs/default"
```

Then get paths automatically:
```python
# Instead of hardcoding: output_csv_dir = "G:\Shared\...\Outputs\..."
output_csv_dir = config.get_output_dir(exp_subfolder=True)
csv_file = config.get_csv_output_path('bflh_mtu_max_steps_ID2_S7_sprint_LSTM_filtered.csv')
```

---

## Structure Comparison

**Before (Hardcoded):**
```
Outputs/
  various_results_all_mixed_together.csv
  manual_tracking_nightmare
```

**After (Config System):**
```
Outputs/
  freq5Hz/
    bflh_mtu_max_*.csv
    plots/
  freq10Hz/
    bflh_mtu_max_*.csv
    plots/
  freq7Hz/
    bflh_mtu_max_*.csv
    plots/
```

Each experiment = separate folder, easy to compare!

---

## Troubleshooting

**"Config file not found"?**
```bash
# Use full path or check relative path is correct
python run_pipeline.py --config C:\full\path\experiments\freq10Hz.yaml

# Check it exists:
dir experiments\*.yaml
```

**"YAML parsing error"?**
```bash
# YAML is whitespace-sensitive. Check:
# - Use spaces (not tabs)
# - Indentation consistent
# Or validate: python -c "import yaml; yaml.safe_load(open('experiments/freq10Hz.yaml'))"
```

**"Script not found"?**
```bash
# List available scripts
python run_pipeline.py --list-scripts

# Run from correct directory (repo root)
cd c:\Users\steudelkri\Documents\opencap-processing
```

---

## What I Recommend: Start Here

### Day 1: Try Config System
```bash
# Test it works
conda run python test_config_system.py

# Test your first config run (dry run - no actual execution)
conda run python run_pipeline.py --config experiments/freq10Hz.yaml --dry-run

# When ready, run a single step
conda run python run_pipeline.py --config experiments/freq10Hz.yaml --steps example_cleaned
```

### Day 2: Create Variations
```bash
# 3 new experiments (freq7Hz, freq12Hz, freq15Hz)
for freq in 7 12 15; do
  cp experiments/freq10Hz.yaml experiments/freq${freq}Hz.yaml
  # Edit each file to change: mtu_length_filter_freq: 10 → $freq
done

# Run them
conda run python run_pipeline.py --config experiments/freq7Hz.yaml --steps CalcStrideMaxLastThreeStrides
conda run python run_pipeline.py --config experiments/freq12Hz.yaml --steps CalcStrideMaxLastThreeStrides
# Results in: Outputs/freq7Hz/, Outputs/freq12Hz/ (organized!)
```

### Day 3+: Full Integration
- Modify your 4 scripts to read from config (5 lines each)
- Run full pipelines: `python run_pipeline.py --config experiments/freq10Hz.yaml`
- All 4 scripts use same params automatically

---

## Questions?

- See `CONFIG_GUIDE.md` for full documentation
- Look at `config_manager.py` docstrings for API details
- Run `python run_pipeline.py --help` for all options
