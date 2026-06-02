"""
Plot per-stride marker errors (x, y, z, magnitude) from stride CSV files.

Reads stride{N}_marker_errors.csv files produced by SeparateMarkerErrorsByStride.py
and saves one figure per stride to the same folder.

Usage:
    python PlotMarkerErrorsByStride.py
"""

import os
import re
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =====================================================================
# Configuration (match SeparateMarkerErrorsByStride.py)
# =====================================================================
stride_errors_dir = (
    r'G:\Shared drives\Stanford Football\ExampleSubject\subject5'
    r'\OpenSimData\OpenPose_1x736_2scales\3-cameras\Kinematics'
    r'\stride_marker_errors')

# Plot errors in millimeters (STO/TRC differences are stored in meters).
PLOT_MM = True
SCALE = 1000.0 if PLOT_MM else 1.0
Y_UNIT = 'mm' if PLOT_MM else 'm'

DPI = 200
SHOW_PLOT = False

# Subplot grid: None = auto sqrt layout
NCOLS = None

STRIDE_FILE_PATTERN = 'stride*_marker_errors.csv'


def marker_names_from_columns(columns):
    """Return sorted marker base names from *_error_mag columns."""
    names = []
    for col in columns:
        if col.endswith('_error_mag'):
            names.append(col[: -len('_error_mag')])
    return sorted(names)


def stride_number_from_path(path):
    m = re.search(r'stride(\d+)_marker_errors\.csv', os.path.basename(path), re.I)
    return int(m.group(1)) if m else None


def load_summary(summary_path):
    if not os.path.isfile(summary_path):
        return None
    df = pd.read_csv(summary_path)
    if 'stride_number' not in df.columns:
        return None
    return df.set_index('stride_number', drop=False)


def plot_stride_figure(df, stride_num, out_path, meta=None):
    """One subplot per marker; x, y, z, and magnitude vs time."""
    markers = marker_names_from_columns(df.columns)
    if not markers:
        raise ValueError('No *_error_mag columns found in stride CSV')

    t = df['time'].values
    n_markers = len(markers)
    ncols = NCOLS or int(np.ceil(np.sqrt(n_markers)))
    nrows = int(np.ceil(n_markers / ncols))

    fig_w = min(3.0 * ncols, 24)
    fig_h = min(2.2 * nrows, 30)
    fig, axes = plt.subplots(nrows, ncols, figsize=(fig_w, fig_h), squeeze=False)

    comp_styles = {
        'x': {'color': '#1f77b4', 'ls': '-', 'lw': 1.0},
        'y': {'color': '#ff7f0e', 'ls': '-', 'lw': 1.0},
        'z': {'color': '#2ca02c', 'ls': '-', 'lw': 1.0},
        'mag': {'color': '#d62728', 'ls': '--', 'lw': 1.2},
    }

    for idx, name in enumerate(markers):
        ax = axes.flat[idx]
        for comp, style in comp_styles.items():
            col = f'{name}_error_{comp}'
            if col not in df.columns:
                continue
            ax.plot(t, df[col].values * SCALE, label=comp, **style)

        short = name.replace('_study', '')
        ax.set_title(short, fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.25)
        if idx % ncols == 0:
            ax.set_ylabel(f'error ({Y_UNIT})', fontsize=8)

    for idx in range(n_markers, nrows * ncols):
        axes.flat[idx].set_visible(False)

    for ax in axes[-1, :]:
        if ax.get_visible():
            ax.set_xlabel('time (s)', fontsize=8)

    title = f'Stride {stride_num} marker errors'
    if meta is not None:
        side = meta.get('side', '')
        t0 = meta.get('start_time', np.nan)
        t1 = meta.get('end_time', np.nan)
        if side or (not np.isnan(t0) and not np.isnan(t1)):
            title += f'  ({side}, {t0:.3f}–{t1:.3f} s)' if side else f'  ({t0:.3f}–{t1:.3f} s)'
    fig.suptitle(title, fontsize=11, y=1.01)

    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper right', fontsize=8,
               bbox_to_anchor=(0.99, 0.99))

    fig.tight_layout(rect=[0, 0, 0.92, 0.98])
    fig.savefig(out_path, dpi=DPI, bbox_inches='tight')
    if SHOW_PLOT:
        plt.show()
    plt.close(fig)


def main():
    if not os.path.isdir(stride_errors_dir):
        raise FileNotFoundError(f'Stride errors folder not found:\n  {stride_errors_dir}')

    pattern = os.path.join(stride_errors_dir, STRIDE_FILE_PATTERN)
    csv_paths = sorted(glob.glob(pattern), key=stride_number_from_path)
    if not csv_paths:
        raise FileNotFoundError(f'No stride marker-error CSVs matching:\n  {pattern}')

    summary = load_summary(
        os.path.join(stride_errors_dir, 'stride_marker_errors_summary.csv'))

    print('=' * 70)
    print('Plot marker errors by stride')
    print('=' * 70)
    print(f'  Input folder:  {stride_errors_dir}')
    print(f'  Stride files:  {len(csv_paths)}')
    print()

    saved = 0
    for csv_path in csv_paths:
        stride_num = stride_number_from_path(csv_path)
        df = pd.read_csv(csv_path)
        if 'time' not in df.columns:
            raise ValueError(f'Missing "time" column in {csv_path}')

        meta = None
        if summary is not None and stride_num in summary.index:
            meta = summary.loc[stride_num].to_dict()

        out_path = os.path.join(
            stride_errors_dir, f'stride{stride_num}_marker_errors.png')
        plot_stride_figure(df, stride_num, out_path, meta=meta)
        saved += 1
        n_markers = len(marker_names_from_columns(df.columns))
        print(f'  stride {stride_num}: {n_markers} markers, '
              f'{len(df)} frames  ->  {os.path.basename(out_path)}')

    print(f'\nSaved {saved} plot(s) to:\n  {stride_errors_dir}')
    print('=' * 70)


if __name__ == '__main__':
    main()
