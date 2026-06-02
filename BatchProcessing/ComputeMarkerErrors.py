"""
ComputeMarkerErrors.py — compare IK marker locations (STO) to post-augmentation TRC.

Inputs (from pipeline config):
  - kinematics_marker_sto : model marker positions saved during IK
  - post_augmentation_trc : experimental marker positions (PostAugmentation)

Output:
  - marker_errors_csv / marker_errors_sto : per-frame errors per matched marker
"""

import os
import sys as _sys
import numpy as np
import pandas as pd
import opensim as osim
from scipy.interpolate import interp1d

_BP = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_BP)
for _p in (_ROOT, _BP, os.path.join(_BP, 'batch_configs')):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
import importlib as _il
cfg = _il.import_module(os.environ.get('PIPELINE_CONFIG', 'pipeline_config'))
paths = cfg.PATHS

TIME_OFFSET = getattr(cfg, 'TRC_TIME_OFFSET', 'auto')
MARKER_NAMES = getattr(cfg, 'MARKER_ERROR_NAMES', None)


def _marker_name_from_sto_col(col):
    for suffix in ('_tx', '_ty', '_tz'):
        if col.endswith(suffix):
            return col[:-len(suffix)]
    return None


def load_sto_markers(sto_path):
    table = osim.TimeSeriesTable(sto_path)
    times = np.asarray(table.getIndependentColumn())
    labels = list(table.getColumnLabels())
    components = {}
    for col in labels:
        base = _marker_name_from_sto_col(col)
        if base is None:
            continue
        comp = col.rsplit('_', 1)[-1]
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
    return times, markers


def load_trc_markers(trc_path):
    table = osim.TimeSeriesTableVec3(trc_path)
    times = np.asarray(table.getIndependentColumn())
    markers = {}
    for name in table.getColumnLabels():
        col = table.getDependentColumn(name)
        markers[name] = np.array([[col[i][0], col[i][1], col[i][2]]
                                  for i in range(len(times))])
    return times, markers


def interpolate_markers(ref_times, ref_markers, target_times):
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


def compute_errors(kin_times, kin_markers, exp_markers, marker_list):
    rows = []
    for i, t in enumerate(kin_times):
        row = {'time': t}
        for name in marker_list:
            diff = kin_markers[name][i] - exp_markers[name][i]
            row[f'{name}_error_x'] = diff[0]
            row[f'{name}_error_y'] = diff[1]
            row[f'{name}_error_z'] = diff[2]
            row[f'{name}_error_mag'] = np.linalg.norm(diff)
        rows.append(row)
    return pd.DataFrame(rows)


def write_sto(df, path):
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


# --- main ---
sto_path = paths['kinematics_marker_sto']
trc_path = paths['post_augmentation_trc']
out_csv = paths['marker_errors_csv']
out_sto = paths['marker_errors_sto']

print('=' * 60)
print('Compute Marker Errors')
print('=' * 60)
print(f'  Kin markers (STO): {sto_path}')
print(f'  Exp markers (TRC): {trc_path}')

if not os.path.isfile(sto_path):
    raise FileNotFoundError(f'Kinematics marker STO not found: {sto_path}')
if not os.path.isfile(trc_path):
    raise FileNotFoundError(f'Post-augmentation TRC not found: {trc_path}')

kin_times, kin_markers = load_sto_markers(sto_path)
exp_times, exp_markers = load_trc_markers(trc_path)

shared = sorted(set(kin_markers) & set(exp_markers))
if MARKER_NAMES:
    shared = [m for m in MARKER_NAMES if m in shared]
study_markers = [m for m in shared if 'study' in m.lower() or '.' in m]
marker_list = study_markers if study_markers else shared

if not marker_list:
    raise RuntimeError('No shared markers between STO and TRC.')

print(f'  Comparing {len(marker_list)} markers, {len(kin_times)} frames')

if TIME_OFFSET == 'auto':
    offset = float(exp_times[0] - kin_times[0])
else:
    offset = float(TIME_OFFSET)
if abs(offset) > 0.001:
    print(f'  TRC time offset: {offset:+.4f} s')
exp_on_kin = interpolate_markers(exp_times - offset, exp_markers, kin_times)

df = compute_errors(kin_times, kin_markers, exp_on_kin, marker_list)
os.makedirs(os.path.dirname(out_csv), exist_ok=True)
df.to_csv(out_csv, index=False)
write_sto(df, out_sto)
print(f'  Saved: {out_csv}')
print(f'  Saved: {out_sto}')

mag_cols = [c for c in df.columns if c.endswith('_error_mag')]
stacked = np.concatenate([df[c].values for c in mag_cols])
print(f'  Mean error: {np.mean(stacked)*1000:.2f} mm')
print(f'  RMS error:  {np.sqrt(np.mean(stacked**2))*1000:.2f} mm')
print(f'  Max error:  {np.max(stacked)*1000:.2f} mm')
print('=' * 60)
