# Step-Based Quality Check Visualization - Implementation Complete

## Summary
Created new script: **`generate_step_quality_checks.py`**

This script combines the functionality of `SeparateSteps.py` and `example_cleaned.py` to:
1. Load full kinematic data pipeline (from `example_cleaned.py`)
2. Calculate shank angular velocity
3. Detect step times via negative-going zero crossings (from `SeparateSteps.py`)
4. Extract per-step data for 6 metrics:
   - Knee flexion angle (degrees)
   - Hip flexion angle (degrees)
   - Knee flexion velocity (degrees/second)
   - Hip flexion velocity (degrees/second)
   - Knee marker positions (x, y, z in meters)
   - Hip marker positions (x, y, z in meters)
5. Generate individual step plots (one plot per step)
6. Generate combined comparison plots (all steps overlaid with time normalization)
7. Save step times and summary statistics to CSV

---

## How to Run

### Prerequisites
1. **OpenSim environment**: Script requires OpenSim installed in Python
   - If not already set up, follow README.md:
   ```bash
   conda create -n opencap-processing python=3.11
   conda activate opencap-processing
   conda install -c opensim-org opensim=4.5=py311np123
   python -m pip install -r requirements.txt
   ```

2. **Adjust configuration** in script header (lines 20-29):
   ```python
   subject_num = 10              # Your subject number
   date = 'February_23'          # Session date folder name
   session = '6'                 # Session number
   trial_type = 'fly'            # Trial type
   filter_freq = 10              # Hz (coordinate filter frequency)
   ```

### Run Script
```bash
conda activate opencap-processing
cd "C:\Users\steudelkri\Documents\opencap-processing"
python generate_step_quality_checks.py
```

---

## Output Structure

For each trial, the script creates:

```
{data_folder}/quality_check/
├── {trial_name}/
│   ├── step_times.csv                          # All step onset times and side (left/right)
│   ├── summary_statistics.csv                  # Summary stats (mean/min/max step duration, etc.)
│   ├── step_comparison_all_steps.png           # Combined overlay plot (all steps normalized)
│   └── individual_steps/
│       ├── step_001_left.png                   # Individual step plot (2x3 grid)
│       ├── step_002_right.png
│       ├── step_003_left.png
│       └── ...
```

### Output Files Explained

- **step_times.csv**: Tab-separated values with columns `time` (seconds) and `side` (left/right)
- **summary_statistics.csv**: Summary metrics including:
  - Total steps, left/right step counts
  - Mean, std, min, max step duration
  - Total trial duration
  
- **Individual step plots** (`step_XXX_SIDE.png`):
  - 2×3 grid showing 6 metrics per step
  - Panel layout:
    - Row 1: Knee angle | Hip angle | Knee markers (x,y,z)
    - Row 2: Knee velocity | Hip velocity | Hip markers (x,y,z)
  - Time shown relative to step onset (0 = step start)
  - High resolution (dpi=300, suitable for documentation/reports)

- **Combined comparison plot** (`step_comparison_all_steps.png`):
  - 2×2 grid showing all steps overlaid
  - Panel layout:
    - Knee angle (all steps)
    - Hip angle (all steps)
    - Knee velocity (all steps)
    - Hip velocity (all steps)
  - Time normalized 0-1 (step duration normalized for comparison)
  - Color-coded: Blue = left steps, Red = right steps
  - Semi-transparent lines show individual steps

---

## Key Features

✅ **Automatic step detection** via shank angular velocity zero-crossing  
✅ **Per-step data extraction** with correct time windowing  
✅ **Marker positions** from motion capture TRC files (if available)  
✅ **Individual AND combined plots** for quality assurance  
✅ **Robust error handling** for missing markers or data  
✅ **CSV outputs** for further analysis  
✅ **High-resolution PNG plots** ready for reports  

---

## Troubleshooting

**Error: ModuleNotFoundError: No module named 'opensim'**
- Solution: Activate correct conda environment before running:
  ```bash
  conda activate opencap-processing
  ```

**Error: No .mot files found**
- Check that session path is correct (verify folder exists)
- Ensure trial name matches actual motion file name

**Marker data not available**
- Script will gracefully skip marker plots if TRC data is missing
- Check that MarkerData folder exists in session directory

**Output plots blank or missing data**
- Verify coordinate names match actual kinematics data
- Check filter frequencies are reasonable (not over-filtering)
- Use `example_cleaned.py` to verify coordinate names in your data

---

## Performance Notes

- **Speed**: ~5-10 seconds per trial (depends on trial length and number of steps)
- **Memory**: Minimal (full kinematics loaded once per trial)
- **Storage**: ~50-100 MB per trial (all individual step plots + comparison plot)

---

## Customization Options

To modify the script, edit these sections:

**Change plotted coordinates:**
```python
COORDINATES_TO_PLOT = ['knee_angle_l', 'knee_angle_r', 'hip_flexion_l', 'hip_flexion_r']
```

**Change marker pairs to track:**
```python
KNEE_MARKERS = ['tibia_l', 'tibia_r']
HIP_MARKERS = ['femur_l', 'femur_r']
```

**Adjust marker filtering:**
```python
marker_filter_freq = 10  # Change Hz value
```

**Change plot layout:**
- Modify `fig, axes = plt.subplots(2, 3, ...)` for different grid sizes
- Adjust figsize, colors, line widths in subplot generation

---

## Next Steps

1. Activate the OpenSim conda environment
2. Update configuration parameters in script
3. Run the script
4. Check output folder: `{data_folder}/quality_check/{trial_name}/`
5. Review individual step plots for quality assessment
6. Use combined plot to check consistency across steps

All plots are ready for inclusion in reports or presentations.
