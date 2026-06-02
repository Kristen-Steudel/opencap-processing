"""
Compare kinematics marker positions (STO) to post-augmentation markers (TRC).

The STO file contains model marker locations saved during IK (columns like
r_knee_study_tx, r_knee_study_ty, r_knee_study_tz).  The TRC file contains
experimental marker positions (Vec3 per marker).  Marker error is the Euclidean
distance between matched markers at each time point.

Usage:
    python _test_marker_error.py
"""

import os
import numpy as np
import pandas as pd
import opensim as osim
from scipy.interpolate import interp1d

# =====================================================================
# Configuration
# =====================================================================
subj_dir = r'G:\Shared drives\Stanford Football\ExampleSubject\subject5'
variant = 'OpenPose_1x736_2scales'
trial_stem = 'ID5_S7_sprint_LSTM'

sto_file = os.path.join(
    subj_dir, 'OpenSimData', variant, '3-cameras', 'Kinematics',
    f'{trial_stem}_ik_model_marker_locations.sto')
trc_file = os.path.join(
    subj_dir, 'MarkerData', variant, '3-cameras',
    'PostAugmentation_v0.3', f'{trial_stem}.trc')
output_csv = os.path.join(
    subj_dir, 'OpenSimData', variant, '3-cameras', 'Kinematics',
    f'{trial_stem}_marker_errors.csv')
output_sto = os.path.join(
    subj_dir, 'OpenSimData', variant, '3-cameras', 'Kinematics',
    f'{trial_stem}_marker_errors.sto')

# Only compare markers present in both files.  None = all shared *_study markers.
MARKER_NAMES = None

# Time offset applied to TRC before interpolation (seconds).
# 'auto' shifts TRC so its first time aligns with STO first time.
TIME_OFFSET = 'auto'


def log(msg):
    print(msg, flush=True)


def _marker_name_from_sto_col(col):
    """r_knee_study_tx -> r_knee_study"""
    for suffix in ('_tx', '_ty', '_tz'):
        if col.endswith(suffix):
            return col[:-len(suffix)]
    return None


def load_sto_markers(sto_path):
    """Load flat XYZ columns from IK model marker locations STO."""
    log(f'Loading STO: {sto_path}')
    table = osim.TimeSeriesTable(sto_path)
    times = np.asarray(table.getIndependentColumn())
    labels = list(table.getColumnLabels())

    # Group columns by marker
    components = {}
    for col in labels:
        base = _marker_name_from_sto_col(col)
        if base is None:
            continue
        comp = col.rsplit('_', 1)[-1]  # tx, ty, tz
        components.setdefault(base, {})[comp] = col

    markers = {}
    for name, cols in components.items():
        if not {'tx', 'ty', 'tz'}.issubset(cols):
            continue
        x = np.array([table.getDependentColumn(cols['tx'])[i]
                      for i in range(len(times))])
        y = np.array([table.getDependentColumn(cols['ty'])[i]
                      for i in range(len(times))])
        z = np.array([table.getDependentColumn(cols['tz'])[i]
                      for i in range(len(times))])
        markers[name] = np.column_stack([x, y, z])

    log(f'  {len(markers)} markers, {len(times)} frames, '
        f'time {times[0]:.4f}–{times[-1]:.4f} s')
    return times, markers


def load_trc_markers(trc_path):
    """Load marker positions from TRC via OpenSim TimeSeriesTableVec3."""
    log(f'Loading TRC: {trc_path}')
    table = osim.TimeSeriesTableVec3(trc_path)
    times = np.asarray(table.getIndependentColumn())
    labels = list(table.getColumnLabels())

    markers = {}
    for name in labels:
        col = table.getDependentColumn(name)
        positions = np.array([[col[i][0], col[i][1], col[i][2]]
                              for i in range(len(times))])
        markers[name] = positions

    log(f'  {len(markers)} markers, {len(times)} frames, '
        f'time {times[0]:.4f}–{times[-1]:.4f} s')
    return times, markers


def interpolate_markers(ref_times, ref_markers, target_times):
    """Interpolate each marker trajectory onto target_times."""
    out = {}
    for name, pos in ref_markers.items():
        f_x = interp1d(ref_times, pos[:, 0], kind='linear',
                       fill_value='extrapolate', assume_sorted=True)
        f_y = interp1d(ref_times, pos[:, 1], kind='linear',
                       fill_value='extrapolate', assume_sorted=True)
        f_z = interp1d(ref_times, pos[:, 2], kind='linear',
                       fill_value='extrapolate', assume_sorted=True)
        out[name] = np.column_stack([f_x(target_times),
                                     f_y(target_times),
                                     f_z(target_times)])
    return out


def compute_errors(kin_times, kin_markers, exp_times, exp_markers,
                   marker_list):
    """Return DataFrame with per-frame errors for each marker."""
    rows = []
    for i, t in enumerate(kin_times):
        row = {'time': t}
        for name in marker_list:
            kin = kin_markers[name][i]
            exp = exp_markers[name][i]
            diff = kin - exp
            row[f'{name}_error_x'] = diff[0]
            row[f'{name}_error_y'] = diff[1]
            row[f'{name}_error_z'] = diff[2]
            row[f'{name}_error_mag'] = np.linalg.norm(diff)
        rows.append(row)
    return pd.DataFrame(rows)


def write_sto(df, path):
    """Write error table in OpenSim STO format."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write('Marker Errors (kinematics STO vs post-augmentation TRC)\n')
        f.write('version=1\n')
        f.write(f'nRows={len(df)}\n')
        f.write(f'nColumns={len(df.columns)}\n')
        f.write('inDegrees=no\n')
        f.write('endheader\n')
        f.write('\t'.join(df.columns) + '\n')
        for _, row in df.iterrows():
            f.write('\t'.join(f'{row[c]:.6f}' for c in df.columns) + '\n')
    log(f'STO written: {path}')


def main():
    log('=' * 70)
    log('MARKER ERROR: kinematics STO vs post-augmentation TRC')
    log('=' * 70)

    kin_times, kin_markers = load_sto_markers(sto_file)
    exp_times, exp_markers = load_trc_markers(trc_file)

    shared = sorted(set(kin_markers) & set(exp_markers))
    if MARKER_NAMES:
        shared = [m for m in MARKER_NAMES if m in shared]

    # Prefer study markers (same naming as STO); fall back to all shared.
    study_markers = [m for m in shared if 'study' in m.lower() or '.' in m]
    marker_list = study_markers if study_markers else shared

    log(f'\nMatched {len(marker_list)} markers for comparison')
    if not marker_list:
        log('ERROR: no shared markers between STO and TRC.')
        log(f'  STO sample: {sorted(kin_markers)[:8]}')
        log(f'  TRC sample: {sorted(exp_markers)[:8]}')
        return 1

    if TIME_OFFSET == 'auto':
        offset = float(exp_times[0] - kin_times[0])
    else:
        offset = float(TIME_OFFSET)
    exp_times_aligned = exp_times - offset
    if abs(offset) > 0.001:
        log(f'TRC time offset: {offset:+.4f} s (applied before interpolation)')

    exp_on_kin = interpolate_markers(exp_times_aligned, exp_markers, kin_times)

    df = compute_errors(kin_times, kin_markers, kin_times, exp_on_kin,
                        marker_list)

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    log(f'CSV written: {output_csv}')
    write_sto(df, output_sto)

    mag_cols = [c for c in df.columns if c.endswith('_error_mag')]
    log('\nSummary (mean / max error in mm):')
    rms_all = []
    for col in mag_cols:
        name = col.replace('_error_mag', '')
        vals = df[col].values
        rms_all.append(vals)
        log(f'  {name:22s}  mean={np.mean(vals)*1000:7.2f} mm  '
            f'max={np.max(vals)*1000:7.2f} mm')

    stacked = np.concatenate(rms_all)
    log(f'\n  ALL MARKERS          mean={np.mean(stacked)*1000:7.2f} mm  '
        f'RMS={np.sqrt(np.mean(stacked**2))*1000:7.2f} mm  '
        f'max={np.max(stacked)*1000:7.2f} mm')
    log('=' * 70)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
