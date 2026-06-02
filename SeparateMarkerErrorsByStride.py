"""
Split a trial-level marker-errors CSV into one CSV per stride.

Stride windows come from consecutive foot-contact times in step_times.csv
(same logic as SeparateMOTFile.py): for each side, stride i runs from
contact[i] to contact[i+1].

Usage:
    python SeparateMarkerErrorsByStride.py
"""

import os
import pandas as pd
import numpy as np

# =====================================================================
# Configuration
# =====================================================================
stride_times_file = (
    r'G:\Shared drives\Stanford Football\ExampleSubject\subject5'
    r'\CleanedKinematics\Outputs\step_times.csv')

marker_errors_csv = (
    r'G:\Shared drives\Stanford Football\ExampleSubject\subject5'
    r'\OpenSimData\OpenPose_1x736_2scales\3-cameras\Kinematics'
    r'\ID5_S7_sprint_LSTM_marker_errors.csv')

output_dir = (
    r'G:\Shared drives\Stanford Football\ExampleSubject\subject5'
    r'\OpenSimData\OpenPose_1x736_2scales\3-cameras\Kinematics'
    r'\stride_marker_errors')

# If True, reset each stride CSV so time starts at 0 (easier for plotting).
RESET_TIME_TO_ZERO = True

# Keep only the last N strides.  Set to None to export every stride.
LAST_N_STRIDES = 4
# False: last N strides by time across the whole trial.
# True:  last N strides per leg (e.g. N=2 -> 2 left + 2 right = 4 files).
LAST_N_PER_LEG = False


def load_stride_times(path):
    """Load step_times.csv; accept step_times.csv or steps_times.csv typo."""
    if not os.path.isfile(path):
        alt = path.replace('step_times.csv', 'steps_times.csv')
        if os.path.isfile(alt):
            path = alt
        else:
            raise FileNotFoundError(f'Stride times file not found:\n  {path}')
    df = pd.read_csv(path)
    if 'time' not in df.columns:
        raise ValueError(f'Expected a "time" column in {path}')
    return df


def build_stride_windows(stride_times_df):
    """
    Return list of dicts with side, start_time, end_time, duration.
    stride_number is assigned later (1 = most recent stride in time).
    """
    windows = []
    if 'side' in stride_times_df.columns:
        sides = ['left', 'right']
        grouped = {s: stride_times_df[stride_times_df['side'] == s]['time'].values
                   for s in sides}
    else:
        grouped = {'all': stride_times_df['time'].values}

    for side, times in grouped.items():
        times = np.sort(times)
        for i in range(len(times) - 1):
            windows.append({
                'side': side,
                'start_time': float(times[i]),
                'end_time': float(times[i + 1]),
                'duration': float(times[i + 1] - times[i]),
                'contact_index': i + 1,
            })

    windows.sort(key=lambda w: w['start_time'])
    return windows


def filter_last_n_strides(windows, n, per_leg=False):
    """
    Return strides to export (optionally last N per leg or overall).
    stride_number: 1 = latest in time, higher numbers = earlier strides.
    """
    if n is None or n <= 0:
        kept = sorted(windows, key=lambda w: w['start_time'])
    elif per_leg:
        kept = []
        for side in sorted({w['side'] for w in windows}):
            side_windows = sorted(
                [w for w in windows if w['side'] == side],
                key=lambda w: w['start_time'])
            kept.extend(side_windows[-n:])
        kept.sort(key=lambda w: w['start_time'])
    else:
        kept = sorted(windows, key=lambda w: w['start_time'])[-n:]

    for idx, w in enumerate(reversed(kept), start=1):
        w['stride_number'] = idx
    return kept


def trim_stride(df, start_time, end_time, reset_time):
    """Extract rows in [start_time, end_time]."""
    mask = (df['time'] >= start_time) & (df['time'] <= end_time)
    seg = df.loc[mask].copy()
    if len(seg) == 0:
        return None
    if reset_time:
        seg['time'] = seg['time'] - seg['time'].iloc[0]
    return seg


def main():
    os.makedirs(output_dir, exist_ok=True)

    print('=' * 70)
    print('Separate marker errors by stride')
    print('=' * 70)
    print(f'  Stride times:    {stride_times_file}')
    print(f'  Marker errors:   {marker_errors_csv}')
    print(f'  Output folder:   {output_dir}')
    print()

    stride_times_df = load_stride_times(stride_times_file)
    print(f'Loaded {len(stride_times_df)} foot-contact events')
    print(stride_times_df.head())

    if not os.path.isfile(marker_errors_csv):
        raise FileNotFoundError(f'Marker errors CSV not found:\n  {marker_errors_csv}')

    errors_df = pd.read_csv(marker_errors_csv)
    if 'time' not in errors_df.columns:
        raise ValueError('Marker errors CSV must have a "time" column')

    t_min, t_max = errors_df['time'].min(), errors_df['time'].max()
    print(f'\nMarker errors: {len(errors_df)} rows, time {t_min:.4f}–{t_max:.4f} s')

    all_windows = build_stride_windows(stride_times_df)
    windows = filter_last_n_strides(
        all_windows, LAST_N_STRIDES, per_leg=LAST_N_PER_LEG)

    if LAST_N_STRIDES is not None:
        mode = f'last {LAST_N_STRIDES} per leg' if LAST_N_PER_LEG else f'last {LAST_N_STRIDES} overall'
        print(f'\nFound {len(all_windows)} strides; keeping {mode} -> {len(windows)} stride(s)')
    print(f'\nExtracting {len(windows)} stride(s)...')

    summary_rows = []
    saved = 0

    for w in windows:
        n = w['stride_number']
        out_path = os.path.join(output_dir, f'stride{n}_marker_errors.csv')
        seg = trim_stride(errors_df, w['start_time'], w['end_time'], RESET_TIME_TO_ZERO)

        if seg is None:
            print(f'  stride{n:3d} ({w["side"]:5s}): '
                  f'{w["start_time"]:.3f}–{w["end_time"]:.3f} s  WARNING — no rows')
            continue

        seg.to_csv(out_path, index=False)
        saved += 1

        mag_cols = [c for c in seg.columns if c.endswith('_error_mag')]
        mean_mag = seg[mag_cols].mean().mean() if mag_cols else np.nan
        max_mag = seg[mag_cols].max().max() if mag_cols else np.nan

        summary_rows.append({
            'stride_number': n,
            'side': w['side'],
            'start_time': w['start_time'],
            'end_time': w['end_time'],
            'duration': w['duration'],
            'n_frames': len(seg),
            'mean_error_mag_m': mean_mag,
            'max_error_mag_m': max_mag,
            'filename': os.path.basename(out_path),
        })

        print(f'  stride{n:3d} ({w["side"]:5s}): '
              f'{w["start_time"]:.3f}–{w["end_time"]:.3f} s  '
              f'({w["duration"]:.3f} s, {len(seg)} frames)  ->  {os.path.basename(out_path)}')

    summary_path = os.path.join(output_dir, 'stride_marker_errors_summary.csv')
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False)

    print(f'\nSaved {saved} stride CSV file(s) to:\n  {output_dir}')
    print(f'Summary: {summary_path}')
    print('=' * 70)


if __name__ == '__main__':
    main()
