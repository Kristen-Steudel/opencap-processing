"""
CompareTrials.py  —  Step 9 of run_pipeline_compare.py

Compares the last N_COMPARE strides from two trials of the same subject:
  Trial A : pipeline_config_CameraTest  (OpenPose 1x736)
  Trial B : pipeline_config_OpenCap     (OpenCap / standard pipeline)

Outputs (saved to subject1/Comparison/):
  compare_kinematics_{tagA}_vs_{tagB}.png   – all joint angles, both trials
  compare_bflh_{tagA}_vs_{tagB}.png         – BFLH length + velocity, both trials
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.signal import butter, filtfilt

# Config names can be overridden via env vars set by run_pipeline_compare.py.
# Defaults: CameraTest (Trial A) vs OpenCap (Trial B) for standalone use.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import importlib
_cfg_a_name = os.environ.get('COMPARE_CONFIG_A', 'pipeline_config_CameraTest')
_cfg_b_name = os.environ.get('COMPARE_CONFIG_B', 'pipeline_config_OpenCap')
cfg_a = importlib.import_module(_cfg_a_name)
cfg_b = importlib.import_module(_cfg_b_name)
print(f'Comparing  A: {_cfg_a_name}  vs  B: {_cfg_b_name}')

# =====================================================================
# SETTINGS
# =====================================================================
N_COMPARE = 2                  # last N strides per leg per trial
GC_PCT    = np.linspace(0, 100, 101)

LABEL_A   = f'OpenPose 1x736  ({cfg_a.PATHS["file_tag"]})'
LABEL_B   = f'OpenCap          ({cfg_b.PATHS["file_tag"]})'

COLORS_A  = plt.cm.Blues(np.linspace(0.55, 0.85, N_COMPARE))
COLORS_B  = plt.cm.Oranges(np.linspace(0.55, 0.85, N_COMPARE))

N_PLOT_COLS    = 5
N_ROWS_PER_PAGE = 2
SUBPLOT_W      = 4.0
SUBPLOT_H      = 4.0

compare_dir = os.path.join(
    r'G:\Shared drives\Sony Camera Testing', 'subject1', 'Comparison')
os.makedirs(compare_dir, exist_ok=True)

tag_a = cfg_a.PATHS['file_tag']
tag_b = cfg_b.PATHS['file_tag']

# =====================================================================
# HELPERS  (duplicated from PlotStrideKinematics.py for self-containment)
# =====================================================================

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


def butter_lowpass(data, cutoff, fs, order=4):
    b, a = butter(order, cutoff / (0.5 * fs), btype='low')
    return filtfilt(b, a, data)


def find_negative_zero_crossings(time, signal):
    crossing_times = []
    for i in range(len(signal) - 1):
        if signal[i] > 0 and signal[i + 1] <= 0:
            t0, t1 = time[i], time[i + 1]
            v0, v1 = signal[i], signal[i + 1]
            t_cross = t0 - v0 * (t1 - t0) / (v1 - v0) if v1 != v0 else t0
            crossing_times.append(t_cross)
    return np.array(crossing_times)


def extract_strides(mot_df, contact_times, n):
    """Return the last n stride DataFrames."""
    strides = []
    for i in range(len(contact_times) - 1):
        t0, t1 = contact_times[i], contact_times[i + 1]
        window = mot_df[
            (mot_df['time'] >= t0) & (mot_df['time'] <= t1)
        ].reset_index(drop=True)
        if len(window) >= 2:
            strides.append(window)
    return strides[-n:] if len(strides) >= n else strides


def stride_time_windows(contact_times, n):
    """Return the last n (t_start, t_end) pairs."""
    pairs = [(contact_times[i], contact_times[i + 1])
             for i in range(len(contact_times) - 1)]
    return pairs[-n:] if len(pairs) >= n else pairs


def interpolate_stride(stride_df, col):
    pct = np.linspace(0, 100, len(stride_df))
    return interp1d(pct, stride_df[col].values,
                    kind='linear', fill_value='extrapolate')(GC_PCT)


def interpolate_bflh_window(df, col, t0, t1):
    """Extract and interpolate a BFLH column over a time window [t0, t1]."""
    win = df[(df['time'] >= t0) & (df['time'] <= t1)]
    if len(win) < 2:
        return None
    t   = win['time'].values
    y   = win[col].values
    pct = (t - t[0]) / (t[-1] - t[0]) * 100
    return interp1d(pct, y, kind='linear', fill_value='extrapolate')(GC_PCT)


# =====================================================================
# LOAD ONE TRIAL
# =====================================================================

def load_trial(cfg, n):
    paths    = cfg.PATHS
    filt_hz  = cfg.COORD_FILTER_FREQ

    # Kinematics
    mot_df = read_mot_file(paths['mot_file'])
    fs     = 1.0 / np.mean(np.diff(mot_df['time'].values))

    if filt_hz and filt_hz > 0:
        skip_exact   = {'pelvis_tx', 'pelvis_ty', 'pelvis_tz', 'time'}
        skip_suffix  = ('_beta', '_reserve', '_residual')
        for col in mot_df.columns:
            if col in skip_exact or any(col.endswith(s) for s in skip_suffix):
                continue
            mot_df[col] = butter_lowpass(mot_df[col].values, filt_hz, fs)

    # Stride detection
    shank_df = pd.read_csv(paths['shank_angular_velocity_csv'])
    l_contacts = find_negative_zero_crossings(
        shank_df['time'].values, shank_df['tibia_l_z'].values)
    r_contacts = find_negative_zero_crossings(
        shank_df['time'].values, shank_df['tibia_r_z'].values)

    l_strides  = extract_strides(mot_df, l_contacts, n)
    r_strides  = extract_strides(mot_df, r_contacts, n)
    l_windows  = stride_time_windows(l_contacts, n)
    r_windows  = stride_time_windows(r_contacts, n)

    # BFLH length (normalized)
    bflh_len_df = None
    if os.path.exists(paths['normalized_bflh_csv']):
        bflh_len_df = pd.read_csv(paths['normalized_bflh_csv'], index_col=0)
        if 'time' not in bflh_len_df.columns:
            bflh_len_df = bflh_len_df.reset_index()

    # BFLH velocity (OpenSim-computed)
    tag     = paths['file_tag']
    vel_csv = os.path.join(paths['outputs_dir'], f'mtu_vel_opensim_{tag}.csv')
    bflh_vel_df = None
    if os.path.exists(vel_csv):
        bflh_vel_df = pd.read_csv(vel_csv, index_col=0)
        if 'time' not in bflh_vel_df.columns:
            bflh_vel_df = bflh_vel_df.reset_index()

    print(f"  [{tag}] left strides: {len(l_strides)}  right strides: {len(r_strides)}")

    return {
        'mot_df':       mot_df,
        'l_strides':    l_strides,
        'r_strides':    r_strides,
        'l_windows':    l_windows,
        'r_windows':    r_windows,
        'bflh_len_df':  bflh_len_df,
        'bflh_vel_df':  bflh_vel_df,
        'label':        f'A' if cfg is cfg_a else 'B',
    }


print('\nLoading Trial A:', tag_a)
data_a = load_trial(cfg_a, N_COMPARE)
print('Loading Trial B:', tag_b)
data_b = load_trial(cfg_b, N_COMPARE)

# =====================================================================
# ANGLE COLUMNS  (intersection of both trials)
# =====================================================================
SKIP_EXACT   = {'pelvis_tx', 'pelvis_ty', 'pelvis_tz'}
SKIP_SUFFIX  = ('_beta', '_reserve', '_residual')

def angle_cols_from(mot_df):
    return [c for c in mot_df.columns
            if c != 'time'
            and c not in SKIP_EXACT
            and not any(c.endswith(s) for s in SKIP_SUFFIX)]

cols_a = angle_cols_from(data_a['mot_df'])
cols_b = angle_cols_from(data_b['mot_df'])
shared_cols = [c for c in cols_a if c in set(cols_b)]
print(f'\nShared angle columns ({len(shared_cols)}): {shared_cols}')

# =====================================================================
# PLOT KINEMATICS COMPARISON
# =====================================================================

def plot_kinematics_page(page_cols, side_strides_a, side_strides_b,
                         side_label, page_num, total_pages, is_first):
    n_rows = int(np.ceil(len(page_cols) / N_PLOT_COLS))
    fig, axes = plt.subplots(
        nrows=n_rows, ncols=N_PLOT_COLS,
        figsize=(N_PLOT_COLS * SUBPLOT_W, n_rows * SUBPLOT_H),
        sharey=False)
    axes_flat = np.array(axes).flatten()
    last_row_start = (n_rows - 1) * N_PLOT_COLS

    for idx, col in enumerate(page_cols):
        ax = axes_flat[idx]

        for k, stride_df in enumerate(side_strides_a):
            if col not in stride_df.columns:
                continue
            y = interpolate_stride(stride_df, col)
            label = (f'{LABEL_A} str {k+1}' if (is_first and idx == 0) else None)
            ax.plot(GC_PCT, y, color=COLORS_A[k], linewidth=1.8,
                    linestyle='-', label=label)

        for k, stride_df in enumerate(side_strides_b):
            if col not in stride_df.columns:
                continue
            y = interpolate_stride(stride_df, col)
            label = (f'{LABEL_B} str {k+1}' if (is_first and idx == 0) else None)
            ax.plot(GC_PCT, y, color=COLORS_B[k], linewidth=1.8,
                    linestyle='--', label=label)

        ax.set_title(col.replace('_', ' '), fontsize=11, pad=5)
        ax.tick_params(labelsize=9)
        ax.grid(alpha=0.3)
        ax.axhline(0, color='k', linewidth=0.4, alpha=0.2)
        ax.set_xlim([0, 100])
        if idx >= last_row_start:
            ax.set_xlabel('Gait Cycle (%)', fontsize=10)
        if idx % N_PLOT_COLS == 0:
            ax.set_ylabel('Angle (deg)', fontsize=10)

    if is_first:
        axes_flat[0].legend(fontsize=8, loc='best')

    for idx in range(len(page_cols), len(axes_flat)):
        axes_flat[idx].set_visible(False)

    page_str = f' (part {page_num}/{total_pages})' if total_pages > 1 else ''
    fig.suptitle(
        f'{side_label} Kinematics Comparison{page_str}\n'
        f'{tag_a}  vs  {tag_b}',
        fontsize=12, fontweight='bold', y=1.01)
    fig.set_constrained_layout(True)
    return fig


cols_per_page = N_PLOT_COLS * N_ROWS_PER_PAGE
col_pages = [shared_cols[i:i + cols_per_page]
             for i in range(0, len(shared_cols), cols_per_page)]

print('\nSaving kinematics comparison figures...')
for side_label, strides_a, strides_b in [
        ('Left',  data_a['l_strides'], data_b['l_strides']),
        ('Right', data_a['r_strides'], data_b['r_strides'])]:
    total = len(col_pages)
    side_slug = side_label.lower()
    for p_idx, page_cols in enumerate(col_pages):
        fig = plot_kinematics_page(
            page_cols, strides_a, strides_b,
            side_label, p_idx + 1, total,
            is_first=(p_idx == 0))
        suffix = f'_p{p_idx+1}' if total > 1 else ''
        out = os.path.join(
            compare_dir,
            f'compare_kinematics_{side_slug}{suffix}_{tag_a}_vs_{tag_b}.png')
        fig.savefig(out, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f'  Saved: {out}')

# =====================================================================
# PLOT BFLH COMPARISON
# =====================================================================

def find_bflh_cols(df):
    """Return (left_col, right_col) for BFLH in the given DataFrame."""
    if df is None:
        return None, None
    cols = [c for c in df.columns if 'bflh' in c.lower()]
    left  = next((c for c in cols if c.endswith('_l')), None)
    right = next((c for c in cols if c.endswith('_r')), None)
    return left, right


def plot_bflh_comparison():
    len_l_a, len_r_a = find_bflh_cols(data_a['bflh_len_df'])
    len_l_b, len_r_b = find_bflh_cols(data_b['bflh_len_df'])
    vel_l_a, vel_r_a = find_bflh_cols(data_a['bflh_vel_df'])
    vel_l_b, vel_r_b = find_bflh_cols(data_b['bflh_vel_df'])

    # Rows: [length left, length right]  [velocity left, velocity right]
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    def fill_ax(ax, df_a, df_b, col_a, col_b, windows_a, windows_b, ylabel, title):
        if df_a is not None and col_a:
            for k, (t0, t1) in enumerate(windows_a):
                y = interpolate_bflh_window(df_a, col_a, t0, t1)
                if y is not None:
                    lbl = f'{LABEL_A} str {k+1}' if k == 0 else None
                    ax.plot(GC_PCT, y, color=COLORS_A[k], linewidth=1.8,
                            linestyle='-', label=lbl)
        if df_b is not None and col_b:
            for k, (t0, t1) in enumerate(windows_b):
                y = interpolate_bflh_window(df_b, col_b, t0, t1)
                if y is not None:
                    lbl = f'{LABEL_B} str {k+1}' if k == 0 else None
                    ax.plot(GC_PCT, y, color=COLORS_B[k], linewidth=1.8,
                            linestyle='--', label=lbl)
        ax.set_title(title, fontsize=12)
        ax.set_xlabel('Gait Cycle (%)', fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.grid(alpha=0.3)
        ax.set_xlim([0, 100])
        ax.legend(fontsize=8, loc='best')

    fill_ax(axes[0, 0],
            data_a['bflh_len_df'], data_b['bflh_len_df'],
            len_l_a, len_l_b,
            data_a['l_windows'], data_b['l_windows'],
            'Norm. BFLH length', 'Left  BFLH Length')
    fill_ax(axes[0, 1],
            data_a['bflh_len_df'], data_b['bflh_len_df'],
            len_r_a, len_r_b,
            data_a['r_windows'], data_b['r_windows'],
            'Norm. BFLH length', 'Right  BFLH Length')
    fill_ax(axes[1, 0],
            data_a['bflh_vel_df'], data_b['bflh_vel_df'],
            vel_l_a, vel_l_b,
            data_a['l_windows'], data_b['l_windows'],
            'BFLH velocity (norm/s)', 'Left  BFLH Velocity')
    fill_ax(axes[1, 1],
            data_a['bflh_vel_df'], data_b['bflh_vel_df'],
            vel_r_a, vel_r_b,
            data_a['r_windows'], data_b['r_windows'],
            'BFLH velocity (norm/s)', 'Right  BFLH Velocity')

    fig.suptitle(
        f'BFLH Comparison\n{tag_a}  vs  {tag_b}',
        fontsize=13, fontweight='bold')
    fig.tight_layout()
    out = os.path.join(
        compare_dir, f'compare_bflh_{tag_a}_vs_{tag_b}.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved: {out}')


print('\nSaving BFLH comparison figure...')
plot_bflh_comparison()

print('\nDone.  All comparison figures saved to:')
print(f'  {compare_dir}')
