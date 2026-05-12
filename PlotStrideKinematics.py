# PlotStrideKinematics.py
#
# Reads a filtered .mot file, detects stride boundaries using negative-going
# zero crossings of shank angular velocity (same method as SeparateSteps.py),
# then plots every available joint angle coordinate normalised to 0-100 %
# gait cycle, one subplot per coordinate, for the last N strides on both
# left and right sides.
#
# Inputs come from pipeline_config.py.

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.signal import butter, filtfilt

import pipeline_config as cfg

# =====================================================================
# CONFIGURATION
# =====================================================================
paths = cfg.PATHS

# .mot file to read
mot_file = paths['mot_file']

# Shank angular velocity CSV (produced by example_cleaned.py / SeparateSteps.py)
shank_csv = paths['shank_angular_velocity_csv']

# NordSprint all-kinematics literature file
lit_file = paths['lit_file_nordsprint_all']

# Speed bin to overlay from the literature CSV (must match a column suffix)
LIT_SPEED = '7p0'

# Output folder
output_dir = paths['outputs_dir']
os.makedirs(output_dir, exist_ok=True)

# Number of strides to overlay on each subplot
N_STRIDES = 3

# Lowpass filter applied to all joint-angle columns before plotting (Hz).
# Set to 0 or negative to skip filtering here (e.g. if mot_file is already
# filtered by FilterKinematics.py).
COORD_FILTER_FREQ = cfg.COORD_FILTER_FREQ

# Gait-cycle percentage grid for interpolation
GC_PCT = np.linspace(0, 100, 101)

# Font sizes
FS_TITLE  = 13
FS_LABEL  = 11
FS_TICK   = 10
FS_LEGEND = 10

# =====================================================================
# HELPERS
# =====================================================================

def read_mot_file(filepath):
    """Parse a .mot / .sto file into a DataFrame."""
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
    """Return interpolated times of positive-to-negative zero crossings."""
    crossing_times = []
    for i in range(len(signal) - 1):
        if signal[i] > 0 and signal[i + 1] <= 0:
            t0, t1 = time[i], time[i + 1]
            v0, v1 = signal[i], signal[i + 1]
            t_cross = t0 - v0 * (t1 - t0) / (v1 - v0) if v1 != v0 else t0
            crossing_times.append(t_cross)
    return np.array(crossing_times)


def interpolate_stride(stride_df, col):
    """Interpolate a single stride column onto GC_PCT (0-100 %)."""
    pct = np.linspace(0, 100, len(stride_df))
    return interp1d(pct, stride_df[col].values,
                    kind='linear', fill_value='extrapolate')(GC_PCT)


# =====================================================================
# LOAD LITERATURE DATA
# =====================================================================
# Build a lookup dict: col_name -> {'mean': array, 'std': array} on GC_PCT grid.
# Column naming convention in the CSV:
#   - sided coords  → "{coord}_{side}_{speed}_Mean"   e.g. hip_flexion_r_7p0_Mean
#   - unsided coords→ "{coord}_{speed}_Mean"           e.g. pelvis_tilt_7p0_Mean
lit_curves = {}
if os.path.exists(lit_file):
    lit_df = pd.read_csv(lit_file)
    lit_pct = lit_df['Percent_Stride'].values
    for col in lit_df.columns:
        if col.endswith(f'_{LIT_SPEED}_Mean'):
            coord_key = col[: -(len(f'_{LIT_SPEED}_Mean'))]
            std_col = col.replace('_Mean', '_Std')
            if std_col not in lit_df.columns:
                continue
            mean_raw = lit_df[col].values
            std_raw  = lit_df[std_col].values
            # Interpolate onto our 0-100 % grid
            mean_interp = interp1d(lit_pct, mean_raw, kind='linear',
                                   fill_value='extrapolate')(GC_PCT)
            std_interp  = interp1d(lit_pct, std_raw,  kind='linear',
                                   fill_value='extrapolate')(GC_PCT)
            lit_curves[coord_key] = {'mean': mean_interp, 'std': std_interp}
    print(f"Loaded literature: {lit_file}")
    print(f"  Speed: {LIT_SPEED.replace('p', '.')} m/s  |  "
          f"Matching curves: {len(lit_curves)}")
else:
    print(f"WARNING: Literature file not found, skipping overlay:\n  {lit_file}")

# =====================================================================
# LOAD DATA
# =====================================================================
print(f"\nLoading .mot file: {mot_file}")
mot_df = read_mot_file(mot_file)
fs_mot = 1.0 / np.mean(np.diff(mot_df['time'].values))
print(f"  {len(mot_df)} frames at ~{fs_mot:.1f} Hz")

# Identify angle columns (all except 'time', skip pelvis translations and
# any beta/reserve columns)
SKIP_SUFFIXES = ('_beta', '_reserve', '_residual')
angle_cols = [
    c for c in mot_df.columns
    if c != 'time'
    and not any(c.endswith(s) for s in SKIP_SUFFIXES)
    and not c.startswith('pelvis_t')   # pelvis translations are in metres
]
print(f"  Angle columns to plot ({len(angle_cols)}): {angle_cols}")

# Optional lowpass filter on angle columns
if COORD_FILTER_FREQ and COORD_FILTER_FREQ > 0:
    for col in angle_cols:
        mot_df[col] = butter_lowpass(mot_df[col].values, COORD_FILTER_FREQ, fs_mot)
    print(f"  Applied {COORD_FILTER_FREQ} Hz lowpass filter to angle columns.")

# =====================================================================
# DETECT STRIDE BOUNDARIES FROM SHANK ANGULAR VELOCITY
# =====================================================================
print(f"\nLoading shank angular velocity: {shank_csv}")
shank_df = pd.read_csv(shank_csv)

left_contacts  = find_negative_zero_crossings(
    shank_df['time'].values, shank_df['tibia_l_z'].values)
right_contacts = find_negative_zero_crossings(
    shank_df['time'].values, shank_df['tibia_r_z'].values)

print(f"  Left  foot contacts: {len(left_contacts)}")
print(f"  Right foot contacts: {len(right_contacts)}")

# =====================================================================
# EXTRACT STRIDES  (last N per side)
# =====================================================================

def extract_strides(mot_df, contact_times, n):
    """Return the last *n* strides as a list of DataFrames."""
    strides = []
    for i in range(len(contact_times) - 1):
        t0, t1 = contact_times[i], contact_times[i + 1]
        window = mot_df[(mot_df['time'] >= t0) & (mot_df['time'] <= t1)].reset_index(drop=True)
        if len(window) >= 2:
            strides.append(window)
    return strides[-n:] if len(strides) >= n else strides


left_strides  = extract_strides(mot_df, left_contacts,  N_STRIDES)
right_strides = extract_strides(mot_df, right_contacts, N_STRIDES)

print(f"  Left  strides extracted: {len(left_strides)}")
print(f"  Right strides extracted: {len(right_strides)}")

# =====================================================================
# PLOTTING
# =====================================================================
N_PLOT_COLS = 5      # subplots per row
N_ROWS_PER_PAGE = 2  # rows per figure — split here to keep titles & labels readable
SUBPLOT_W = 4.2      # inches per subplot column
SUBPLOT_H = 4.2      # inches per subplot row  (tall enough for title + data + xlabel)

# Split angle_cols into pages of N_PLOT_COLS * N_ROWS_PER_PAGE each
cols_per_page = N_PLOT_COLS * N_ROWS_PER_PAGE
col_pages = [angle_cols[i:i + cols_per_page]
             for i in range(0, len(angle_cols), cols_per_page)]


def make_page(page_cols, strides, side_label, colormap, page_num, total_pages,
              is_first_page, side_suffix):
    """
    Build one figure for a subset of coordinates.

    side_suffix : '_l' or '_r' — used to look up same-side literature curves.
    Literature mean is plotted as a solid black line; mean ± 1 SD as dotted
    black lines above and below.
    """
    colors = colormap(np.linspace(0.45, 0.9, max(len(strides), 1)))

    n_this_rows = int(np.ceil(len(page_cols) / N_PLOT_COLS))
    fig, axes = plt.subplots(
        nrows=n_this_rows, ncols=N_PLOT_COLS,
        figsize=(N_PLOT_COLS * SUBPLOT_W, n_this_rows * SUBPLOT_H),
        sharey=False)
    axes_flat = np.array(axes).flatten()

    last_row_start = (n_this_rows - 1) * N_PLOT_COLS
    lit_legend_added = False   # add literature legend entry once per page

    for idx, col in enumerate(page_cols):
        ax = axes_flat[idx]

        # ---- literature overlay ----
        # NordSprint right side = the "leading/ipsilateral" reference leg.
        # Mapping rule (based on which foot defines the stride):
        #   ipsilateral col (same side as stride contact) → NordSprint _r
        #   contralateral col                             → NordSprint _l
        #   unsided col (pelvis_tilt, lumbar_*, …)        → exact match
        if col.endswith('_l') or col.endswith('_r'):
            base     = col[:-2]
            col_side = col[-2:]          # '_l' or '_r'
            if col_side == side_suffix:  # ipsilateral → right reference
                lit_candidate = base + '_r'
            else:                        # contralateral → left reference
                lit_candidate = base + '_l'
        else:
            lit_candidate = col          # unsided coordinate
        lit_key = lit_candidate if lit_candidate in lit_curves else None
        if lit_key and lit_key in lit_curves:
            lc = lit_curves[lit_key]
            mean_label = f'NordSprint {LIT_SPEED.replace("p",".")} m/s mean' \
                         if (not lit_legend_added) else None
            sd_label   = f'NordSprint ± 1 SD' \
                         if (not lit_legend_added) else None
            ax.plot(GC_PCT, lc['mean'],
                    color='black', linewidth=2.0, linestyle='-',
                    label=mean_label, zorder=3)
            ax.plot(GC_PCT, lc['mean'] + lc['std'],
                    color='black', linewidth=1.2, linestyle=':',
                    label=sd_label, zorder=3)
            ax.plot(GC_PCT, lc['mean'] - lc['std'],
                    color='black', linewidth=1.2, linestyle=':',
                    zorder=3)
            lit_legend_added = True

        # ---- experimental strides ----
        for k, stride_df in enumerate(strides):
            interp = interpolate_stride(stride_df, col)
            label = f'Stride {k + 1}' if (is_first_page and idx == 0) else None
            ax.plot(GC_PCT, interp, color=colors[k], linewidth=1.8,
                    label=label, zorder=2)

        ax.set_title(col.replace('_', ' '), fontsize=FS_TITLE, pad=6)
        ax.tick_params(labelsize=FS_TICK)
        ax.grid(alpha=0.3)
        ax.axhline(0, color='k', linewidth=0.5, alpha=0.2)

        # x-label on bottom row only
        if idx >= last_row_start:
            ax.set_xlabel('Gait Cycle (%)', fontsize=FS_LABEL, labelpad=4)

        # y-label on leftmost column only
        if idx % N_PLOT_COLS == 0:
            ax.set_ylabel('Angle (deg)', fontsize=FS_LABEL)

    # Legend on first subplot of the first page
    if is_first_page:
        axes_flat[0].legend(fontsize=FS_LEGEND, loc='best')

    # Hide unused subplot panels
    for idx in range(len(page_cols), len(axes_flat)):
        axes_flat[idx].set_visible(False)

    page_str = f' (part {page_num}/{total_pages})' if total_pages > 1 else ''
    tag = paths['file_tag']
    fig.suptitle(f'{side_label} Stride Kinematics{page_str} — {tag}',
                 fontsize=FS_TITLE + 2, fontweight='bold', y=1.01)

    fig.set_constrained_layout(True)
    fig.set_constrained_layout_pads(hspace=0.12, wspace=0.08,
                                    h_pad=0.6, w_pad=0.4)
    return fig


def make_all_pages(strides, side_label, colormap, side_suffix):
    """Return a list of (fig, output_path) for all pages of one side."""
    figs = []
    total = len(col_pages)
    tag = paths['file_tag']
    side_slug = side_label.lower()
    for p_idx, page_cols in enumerate(col_pages):
        page_num = p_idx + 1
        fig = make_page(page_cols, strides, side_label, colormap,
                        page_num, total, is_first_page=(p_idx == 0),
                        side_suffix=side_suffix)
        suffix = f'_p{page_num}' if total > 1 else ''
        out_path = os.path.join(
            output_dir,
            f'stride_kinematics_{side_slug}{suffix}_{tag}.png')
        figs.append((fig, out_path))
    return figs


pages_l = make_all_pages(left_strides,  'Left',  plt.cm.Blues,   '_l')
pages_r = make_all_pages(right_strides, 'Right', plt.cm.Oranges, '_r')

for fig, path in pages_l + pages_r:
    fig.savefig(path, dpi=150, bbox_inches='tight')
    print(f"Saved: {path}")

plt.show()
print("\nDone.")
