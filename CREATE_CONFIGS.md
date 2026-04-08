# Creating & Customizing Experiment Configs

This guide shows how to create new experiment configurations for your testing.

---

## Quick Start: 5-Minute Setup for New Experiment

### Step 1: Copy Existing Config
```bash
cp experiments/freq10Hz.yaml experiments/freq12Hz.yaml
```

### Step 2: Edit the File
Open `experiments/freq12Hz.yaml` and change:
```yaml
# Before:
experiment_name: freq10Hz
mtu_length_filter_freq: 10

# After:
experiment_name: freq12Hz
mtu_length_filter_freq: 12
```

### Step 3: Run It
```bash
conda run python run_pipeline.py --config experiments/freq12Hz.yaml --steps example_cleaned
```

**Done!** Results go to `Outputs/freq12Hz/`

---

## Full Config File Reference

### Minimal Config (Required Fields)
```yaml
# Minimal config - only essentials
experiment_name: mytest
mtu_length_filter_freq: 10

paths:
  base: 'G:/Shared drives/Stanford Football'
  output_base: 'Outputs'
```

### Standard Config (Recommended)
```yaml
# Standard config - recommended for consistency
experiment_name: freq10Hz
description: Test with 10 Hz MTU length filter

# Filter frequencies
filter_freq: 15                    # Kinematics
coord_filter_freq: 10             # Coordinate filtering  
mtu_length_filter_freq: 10        # MTU length ← CHANGE THIS

# Session parameters (usually same)
subject_num: 2
date: March_2
session: '7'
type: sprint

# Enable diagnostics
enable_mtu_filter_diagnostics: false

# Paths (usually same)
paths:
  base: 'G:/Shared drives/Stanford Football'
  output_base: 'Outputs'

# Scripts to run (optional - defines pipeline order)
scripts:
  - example_cleaned
  - CalcStrideMaxLastThreeStrides
  - SeparateSteps
  - CalcStepVelReedMethodWithFlags
```

### Advanced Config (Custom Paths)
```yaml
experiment_name: custom_path_test

# Different session/subject?
subject_num: 3
date: April_1
session: '8'
type: walking

# Different data location?
paths:
  base: 'G:/Shared drives/Stanford Football'
  output_base: 'Outputs'

# Custom scripts order
scripts:
  - CalcStrideMaxLastThreeStrides  # Skip example_cleaned
  - SeparateSteps

mtu_length_filter_freq: 8
filter_freq: 15
coord_filter_freq: 10
```

---

## Field Explanations

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `experiment_name` | string | required | Used for output folder name, keep short (freq10Hz, test_v1, etc.) |
| `description` | string | optional | For your notes, not used by code |
| `mtu_length_filter_freq` | integer | 10 | Main parameter you're testing - **CHANGE THIS** |
| `filter_freq` | integer | 15 | Kinematics filter (usually constant) |
| `coord_filter_freq` | integer | 10 | Coordinate filter (usually constant) |
| `subject_num` | integer | 2 | Subject number (usually constant) |
| `date` | string | March_2 | Collection date folder (usually constant) |
| `session` | string | 7 | Session number (usually constant) - Note: quoted as string |
| `type` | string | sprint | Trial type (usually constant) |
| `enable_mtu_filter_diagnostics` | boolean | false | Enable detailed filtering output |
| `paths.base` | string | G:/Shared... | Root data location |
| `paths.output_base` | string | Outputs | Output folder name (creates subfolders per experiment) |
| `scripts` | list | all | Which scripts to run in pipeline |

---

## Common Variations to Test

### Filter Frequency Sweep
```bash
# Create configs for testing different frequencies
for freq in 5 7 10 12 15; do
  cp experiments/freq10Hz.yaml experiments/freq${freq}Hz.yaml
done
```

Then edit each file (e.g., `freq7Hz.yaml`):
```yaml
experiment_name: freq7Hz
mtu_length_filter_freq: 7  # Change this
```

### Different Subjects/Sessions
```yaml
# For subject 3, session 8
experiment_name: subject3_session8
subject_num: 3
session: '8'
mtu_length_filter_freq: 10
```

### Testing Different Trial Types
```yaml
# For walking instead of sprint
experiment_name: walking_freq10Hz
type: walking  # Change from sprint
mtu_length_filter_freq: 10
```

### Custom Output Location
```yaml
experiment_name: freq10Hz_backup
paths:
  base: 'D:/Backup/Stanford Football'  # Different drive
  output_base: 'Results'  # Different folder name
```

---

## Output Folder Structure

When you run with a config, this is created:

```
G:\Shared drives\Stanford Football\March_2\subject2\
  CleanedKinematics\filtered_post_augmentation\Outputs\
    freq5Hz\
      bflh_mtu_max_steps_ID2_S7_sprint_LSTM_filtered.csv
      summary_plot.png
      overlay_plot.png
      ...
    freq10Hz\
      bflh_mtu_max_steps_ID2_S7_sprint_LSTM_filtered.csv
      summary_plot.png
      overlay_plot.png
      ...
    freq12Hz\
      ...
```

Each experiment gets its own folder automatically. **No overwrites possible!**

---

## Tips & Best Practices

### 1. Naming Conventions
```yaml
# GOOD - clear, descriptive
experiment_name: freq10Hz
experiment_name: subject2_session7_sprint
experiment_name: test_5hz_baseline

# AVOID - unclear
experiment_name: test
experiment_name: v2
experiment_name: final
```

### 2. Batch Testing
```bash
# Create 5 configs at once
for freq in 5 7 10 12 15; do
  cp experiments/freq10Hz.yaml experiments/freq${freq}Hz.yaml
  sed -i "s/freq10Hz/freq${freq}Hz/" experiments/freq${freq}Hz.yaml
  sed -i "s/mtu_length_filter_freq: 10/mtu_length_filter_freq: ${freq}/" experiments/freq${freq}Hz.yaml
done
```

### 3. Keep Baseline
Always keep your original working config:
```bash
experiments/
  freq5Hz.yaml          # ← Keep as baseline/reference
  freq10Hz.yaml         # Your test
  freq7Hz.yaml          # Another test
  freq12Hz.yaml         # Another test
```

### 4. Version Control
Store configs in git for reproducibility:
```bash
git add experiments/freq*.yaml
git commit -m "Add filter frequency sweep configs (5-15 Hz)"
```

### 5. Document Your Changes
```yaml
# freq10Hz.yaml
experiment_name: freq10Hz
description: "Test 10 Hz MTU filter (vs baseline 5 Hz) - see issue #42"

# Later, you'll remember WHY you created this config
```

---

## Troubleshooting Config Issues

### Config file not found
```bash
# Check file exists
ls experiments/freq10Hz.yaml

# Use full path if needed
python run_pipeline.py --config C:\full\path\experiments\freq10Hz.yaml

# Check from correct directory
cd c:\Users\steudelkri\Documents\opencap-processing
```

### YAML parsing errors
```bash
# YAML is whitespace-sensitive! Common issues:

# ✗ WRONG - Tab instead of spaces
experiment_name: freq10Hz
	mtu_length_filter_freq: 10  # ← TAB (wrong)

# ✓ CORRECT - Spaces
experiment_name: freq10Hz
  mtu_length_filter_freq: 10  # ← SPACES (right)

# Validate YAML:
python -c "import yaml; yaml.safe_load(open('experiments/freq10Hz.yaml'))"
```

### Paths have wrong slashes
```yaml
# Windows uses backslash but YAML strings work better with forward slash

# ✓ CORRECT
paths:
  base: 'G:/Shared drives/Stanford Football'

# Also works
paths:
  base: 'G:\\Shared drives\\Stanford Football'

# Avoid mixed:
paths:
  base: 'G:\Shared drives/Stanford Football'  # ✗ confusing
```

### Output not where expected
```bash
# Check what path config generated
python run_pipeline.py --config experiments/freq10Hz.yaml --show-config
# Look for: Output Dir: G:\Shared drives\...\Outputs\freq10Hz\

# Or check environment variable set by pipeline runner
echo %OPENCAP_OUTPUT_DIR%
```

---

## Advanced: Creating Config Variants Programmatically

### Python Script to Generate Configs
```python
import yaml
import os

# Create sweep of filter frequencies
for freq in range(5, 20, 2):  # 5, 7, 9, 11, ..., 19 Hz
    config = {
        'experiment_name': f'freq{freq}Hz',
        'description': f'Testing {freq} Hz MTU length filter',
        'mtu_length_filter_freq': freq,
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
    
    filename = f'experiments/freq{freq}Hz.yaml'
    os.makedirs('experiments', exist_ok=True)
    with open(filename, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    print(f"Created {filename}")
```

Then run all of them:
```bash
for config in experiments/freq*.yaml; do
    python run_pipeline.py --config $config --steps CalcStrideMaxLastThreeStrides
done
```

---

## Next Steps

1. **Copy existing config:**
   ```bash
   cp experiments/freq10Hz.yaml experiments/freq12Hz.yaml
   ```

2. **Edit the new config:**
   - Change `experiment_name: freq12Hz`
   - Change `mtu_length_filter_freq: 12`

3. **Run it:**
   ```bash
   conda run python run_pipeline.py --config experiments/freq12Hz.yaml
   ```

4. **Compare results:**
   ```
   Outputs/freq10Hz/ vs Outputs/freq12Hz/
   ```

**That's it!** You now have organized, comparable experiments. 🎉
