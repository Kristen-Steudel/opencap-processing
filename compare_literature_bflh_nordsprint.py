# Compare per-stride hip, knee, and ankle angle trajectories against
# NordSprint literature kinematics (mean ± 1 SD) using Pearson correlation.
#
# Both datasets are in degrees, so they share the same axis.
# Literature bands are plotted as mean ± 1 SD shaded regions.

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.signal import butter, filtfilt
from scipy.stats import pearsonr
from matplotlib import cm

# ===== CONFIGURATION =====
subject = 5
session = "S7"
date = 'March_2'
trial_type = 'sprint'
coord_filter_freq = 10  # Hz lowpass for coordinate values (match example_cleaned.py)
n_strides_to_plot = 2
lit_speeds = ['7p0', '8p0','4p0']  # NordSprint speed bins to plot (first one is used for Pearson r)

base_path = rf'G:\Shared drives\Stanford Football\{date}\subject{subject}\CleanedKinematics\filtered_post_augmentation\Outputs'
mot_file = rf'G:\Shared drives\Stanford Football\{date}\subject{subject}\CleanedKinematics\OpenPose_default\3-cameras\Kinematics\FiltPostAug\ID{subject}_{session}_{trial_type}_LSTM_filtpostaug15Hz_filteredkinematics_15Hz.mot'
lit_file = r'G:\Shared drives\Stanford Football\LiteratureData\NordSprintKinematics\All_Kinematics_Combined.csv'
hamner_dir = r'G:\Shared drives\Stanford Football\LiteratureData\SamHamnerKinematics'

# Joints to compare: (OpenSim column name, display label, Hamner CSV filename)
JOINTS = [
    ('hip_flexion', 'Hip Flexion', 'SamHamner2013_HipAngle_5p0.csv'),
    ('knee_angle', 'Knee Angle', 'SamHamner2013_KneeAngle_5p0.csv'),
    ('ankle_angle', 'Ankle Angle', 'SamHamner2013_AnkleAngle_5p0.csv'),
]

# ===== LOAD .MOT FILE =====
def read_mot_file(filepath):
    with open(filepath) as f:
        lines = f.readlines()
    header_end = 0
    for i, line in enumerate(lines):
        if line.strip().lower() == 'endheader':
            header_end = i + 1
            break
    col_names = lines[header_end].strip().split('\t')
    data = []
    for line in lines[header_end + 1:]:
        vals = line.strip().split('\t')
        if len(vals) == len(col_names):
            data.append([float(v) for v in vals])
    return pd.DataFrame(data, columns=col_names)


def butter_lowpass_filter(data, cutoff, fs, order=4):
    b, a = butter(order, cutoff / (0.5 * fs), btype='low')
    return filtfilt(b, a, data)


mot_df = read_mot_file(mot_file)
fs = 1.0 / np.mean(np.diff(mot_df['time'].values))
print(f"Loaded .mot file: {mot_file}")
print(f"  {len(mot_df)} frames at ~{fs:.1f} Hz")

# Apply lowpass filter to joint angle columns
for joint_base, _, _ in JOINTS:
    for side in ['_r', '_l']:
        col = joint_base + side
        if col in mot_df.columns:
            mot_df[col] = butter_lowpass_filter(mot_df[col].values, coord_filter_freq, fs)

# ===== LOAD LITERATURE DATA =====
lit_df = pd.read_csv(lit_file)
normalized_x = lit_df['Percent_Stride'].values  # 0-100 with 101 points

# Extract mean and std for right-side literature curves at each speed.
# The right-side NordSprint data is used as the reference for both left and
# right experimental strides.
lit_curves = {}  # keyed by (joint_base, speed)
for speed in lit_speeds:
    for joint_base, _, _ in JOINTS:
        mean_col = f'{joint_base}_r_{speed}_Mean'
        std_col = f'{joint_base}_r_{speed}_Std'
        if mean_col in lit_df.columns and std_col in lit_df.columns:
            lit_curves[(joint_base, speed)] = {
                'mean': lit_df[mean_col].values,
                'std': lit_df[std_col].values,
            }

primary_speed = lit_speeds[0]
print(f"Literature speed bins: {[s.replace('p','.') for s in lit_speeds]} m/s (right-side reference)")
print(f"Primary speed for Pearson r: {primary_speed.replace('p','.')} m/s")
print(f"NordSprint curves loaded: {len(lit_curves)}")

# ===== LOAD HAMNER 2013 DATA =====
# Headerless CSVs (column 0 = gait cycle %, column 1 = angle in degrees)
hamner_curves = {}
for joint_base, _, hamner_filename in JOINTS:
    hamner_path = os.path.join(hamner_dir, hamner_filename)
    if not os.path.exists(hamner_path):
        print(f"  Hamner file not found: {hamner_path}")
        continue
    raw = np.loadtxt(hamner_path, delimiter=',')
    order = np.argsort(raw[:, 0])
    x_sorted = raw[order, 0]
    y_sorted = raw[order, 1]
    _, unique_idx = np.unique(x_sorted, return_index=True)
    hamner_interp = interp1d(x_sorted[unique_idx], y_sorted[unique_idx],
                             kind='linear', fill_value='extrapolate')(normalized_x)
    hamner_curves[joint_base] = hamner_interp

print(f"Hamner 2013 curves loaded: {list(hamner_curves.keys())}")

# ===== LOAD STRIDE TIMES =====
left_stride_times_df = pd.read_csv(rf'{base_path}\step_times_left.csv')
right_stride_times_df = pd.read_csv(rf'{base_path}\step_times_right.csv')
print(f"Left foot contacts: {len(left_stride_times_df)}, Right foot contacts: {len(right_stride_times_df)}")


def get_stride_window(df, t0, t1):
    return df[(df['time'] >= t0) & (df['time'] <= t1)].reset_index(drop=True)


def interpolate_to_percent(stride_df, col, x_out):
    pct = np.linspace(0, 100, len(stride_df))
    return interp1d(pct, stride_df[col], kind='linear', fill_value='extrapolate')(x_out)


# ===== COMPUTE PER-STRIDE CURVES AND CORRELATIONS =====
results = []

def process_strides(stride_times_df, side_label, side_suffix):
    for i in range(len(stride_times_df) - 1):
        t0 = stride_times_df['time'].iloc[i]
        t1 = stride_times_df['time'].iloc[i + 1]
        stride_df = get_stride_window(mot_df, t0, t1)
        if len(stride_df) < 2:
            continue

        entry = {
            'side': side_label,
            'stride_index': i,
            'start_time': t0,
            'end_time': t1,
        }

        for joint_base, _, _ in JOINTS:
            col = joint_base + side_suffix
            if col not in stride_df.columns:
                continue
            curve = interpolate_to_percent(stride_df, col, normalized_x)
            entry[f'{col}_curve'] = curve

            if (joint_base, primary_speed) in lit_curves:
                r_val, p_val = pearsonr(curve, lit_curves[(joint_base, primary_speed)]['mean'])
                entry[f'{col}_r'] = r_val
                entry[f'{col}_p'] = p_val

        results.append(entry)

process_strides(left_stride_times_df, 'left', '_l')
process_strides(right_stride_times_df, 'right', '_r')

# Number strides per side in reverse order (stride 1 = latest)
for side in ['left', 'right']:
    side_results = [r for r in results if r['side'] == side]
    for rank, r in enumerate(reversed(side_results), start=1):
        r['stride_number'] = rank

# ===== SAVE CORRELATION METRICS =====
metric_rows = []
for r in results:
    row = {
        'side': r['side'],
        'stride_number': r['stride_number'],
        'start_time': r['start_time'],
        'end_time': r['end_time'],
    }
    for joint_base, _, _ in JOINTS:
        suffix = '_l' if r['side'] == 'left' else '_r'
        col = joint_base + suffix
        row[f'pearson_r_{col}'] = r.get(f'{col}_r', np.nan)
        row[f'p_value_{col}'] = r.get(f'{col}_p', np.nan)
    metric_rows.append(row)

metrics_df = pd.DataFrame(metric_rows).sort_values(['side', 'stride_number']).reset_index(drop=True)
metrics_file = rf'{base_path}\nordsprint_kinematics_correlation_ID{subject}_{session}_{trial_type}.csv'
metrics_df.to_csv(metrics_file, index=False)

print(f"\n{'='*70}")
print(f"NordSprint Kinematics Comparison (Pearson r vs {primary_speed.replace('p','.')} m/s)")
print(f"{'='*70}")
print(metrics_df.to_string(index=False))
print(f"\nSaved to: {metrics_file}")

# ===== PLOT: 3 joints × 2 sides =====
fig, axes = plt.subplots(3, 2, figsize=(18, 16))

left_results = sorted([r for r in results if r['side'] == 'left'], key=lambda r: r['stride_number'])
right_results = sorted([r for r in results if r['side'] == 'right'], key=lambda r: r['stride_number'])

n_left = min(n_strides_to_plot, len(left_results))
n_right = min(n_strides_to_plot, len(right_results))

left_to_plot = left_results[:n_left]
right_to_plot = right_results[:n_right]

left_colors = cm.Blues(np.linspace(0.4, 0.9, max(n_left, 1)))
right_colors = cm.Reds(np.linspace(0.4, 0.9, max(n_right, 1)))

for row_idx, (joint_base, joint_label, _) in enumerate(JOINTS):
    for col_idx, (side_label, side_suffix, strides_to_plot, colors) in enumerate([
        ('Left', '_l', left_to_plot, left_colors),
        ('Right', '_r', right_to_plot, right_colors),
    ]):
        ax = axes[row_idx, col_idx]
        joint_col = joint_base + side_suffix

        # Literature mean ± 1 SD bands for each speed (always right-side NordSprint)
        speed_band_colors = {'8p0': 'black', '4p0': 'green', '5p0': 'purple',
                             '6p0': 'orange', '7p0': 'brown', '7p5': 'teal'}
        for speed in lit_speeds:
            key = (joint_base, speed)
            if key not in lit_curves:
                continue
            mean = lit_curves[key]['mean']
            std = lit_curves[key]['std']
            clr = speed_band_colors.get(speed, 'gray')
            speed_label = speed.replace('p', '.')
            ax.fill_between(normalized_x, mean - std, mean + std,
                            color=clr, alpha=0.15, label=f'NordSprint ±1 SD ({speed_label} m/s)')
            ax.plot(normalized_x, mean + std, ':', color=clr, linewidth=1, alpha=0.5)
            ax.plot(normalized_x, mean - std, ':', color=clr, linewidth=1, alpha=0.5)
            ax.plot(normalized_x, mean, '-', color=clr, linewidth=2.5,
                    label=f'NordSprint Mean ({speed_label} m/s)')

        # Hamner 2013 curve
        if joint_base in hamner_curves:
            ax.plot(normalized_x, hamner_curves[joint_base], color='magenta',
                    linewidth=2.5, linestyle='--', label='Hamner 2013 (5.0 m/s)')

        # Experimental strides
        for idx, r in enumerate(strides_to_plot):
            curve_key = f'{joint_col}_curve'
            r_key = f'{joint_col}_r'
            if curve_key not in r:
                continue
            r_val = r.get(r_key, float('nan'))
            ax.plot(normalized_x, r[curve_key], color=colors[idx],
                    label=f'Stride {r["stride_number"]} (r={r_val:.3f})', linewidth=2)

        ax.set_xlabel('Gait Cycle (%)', fontsize=12)
        ax.set_ylabel('Angle (deg)', fontsize=12)
        ax.set_title(f'{side_label} {joint_label}', fontsize=13, fontweight='bold')
        if row_idx == 0 and col_idx == 0:
            ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_xlim([0, 100])

speed_str = ' & '.join(s.replace('p', '.') for s in lit_speeds)
plt.suptitle(f'Subject {subject} {session} ({trial_type}) vs NordSprint ({speed_str} m/s) & Hamner 2013',
             fontsize=15, fontweight='bold', y=1.01)
plt.tight_layout()
plot_file = rf'{base_path}\nordsprint_kinematics_comparison_ID{subject}_{session}_{trial_type}.png'
plt.savefig(plot_file, dpi=300, bbox_inches='tight')
plt.show()

print(f"\nComparison plot saved to: {plot_file}")

# ===== SUMMARY STATS =====
for side in ['left', 'right']:
    side_df = metrics_df[metrics_df['side'] == side]
    if len(side_df) == 0:
        continue
    print(f"\n{side.upper()} strides:")
    suffix = '_l' if side == 'left' else '_r'
    for joint_base, joint_label, _ in JOINTS:
        col = f'pearson_r_{joint_base}{suffix}'
        if col in side_df.columns:
            vals = side_df[col].dropna()
            if len(vals) > 0:
                print(f"  {joint_label}: mean r = {vals.mean():.4f}, "
                      f"range = [{vals.min():.4f}, {vals.max():.4f}]")
