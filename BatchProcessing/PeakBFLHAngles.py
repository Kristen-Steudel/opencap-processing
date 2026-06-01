# PeakBFLHAngles.py
#
# For every stride (left and right), locates the peak normalized BFLH
# muscle-tendon length, records the gait-cycle percentage at which it occurs,
# and extracts the following joint angles from the filtered .mot file at
# that instant:
#   - hip flexion (ipsilateral)
#   - pelvis tilt
#   - lumbar extension
#   - knee angle (ipsilateral)
#   - thigh tilt  (≈ pelvis_tilt + ipsilateral hip_flexion)
#
# Stride speed is computed from the change in pelvis_tx over the stride
# duration — no external velocity tool needed.
#
# The output CSV includes subject/session/trial metadata so rows from
# many trials can be concatenated and used directly for speed-vs-angle
# scatter plots.
#
# Inputs from pipeline_config.py.

import os
import numpy as np
import pandas as pd

# import pipeline_config as cfg
import sys as _sys
_BP = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_BP)
for _p in (_ROOT, _BP, os.path.join(_BP, 'batch_configs')):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
import importlib as _il
cfg = _il.import_module(os.environ.get('PIPELINE_CONFIG', 'pipeline_config'))

# =====================================================================
# CONFIGURATION
# =====================================================================
paths = cfg.PATHS

mot_file   = paths['mot_file']              # filtered kinematics (.mot)
bflh_file  = paths['normalized_bflh_csv']  # normalized BFLH lengths
output_csv = paths['peak_bflh_angles_csv']
os.makedirs(os.path.dirname(output_csv), exist_ok=True)

tag = paths['file_tag']

# =====================================================================
# HELPERS
# =====================================================================

def read_mot_file(filepath):
    """Parse a .mot/.sto file into a DataFrame."""
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


def value_at_time(df, t, col):
    """Return df[col] at the frame nearest to time t. NaN if col absent."""
    if col not in df.columns:
        return np.nan
    idx = int(np.argmin(np.abs(df['time'].values - t)))
    return float(df[col].iloc[idx])


# =====================================================================
# LOAD DATA
# =====================================================================
print(f"Loading .mot file:     {mot_file}")
mot_df = read_mot_file(mot_file)
print(f"  {len(mot_df)} frames  |  columns: {list(mot_df.columns)}")

print(f"Loading BFLH lengths:  {bflh_file}")
bflh_df = pd.read_csv(bflh_file)

print(f"Loading stride times ...")
left_contacts  = pd.read_csv(paths['step_times_left'])['time'].values
right_contacts = pd.read_csv(paths['step_times_right'])['time'].values
print(f"  Left contacts: {len(left_contacts)}  |  Right contacts: {len(right_contacts)}")

# =====================================================================
# PROCESS STRIDES
# =====================================================================
records = []

def process_strides(contact_times, side):
    """
    Iterate over consecutive foot contacts to define strides.
    For each stride, find peak BFLH length and extract angles at that instant.

    side : 'left' or 'right'
    """
    s = side[0]                    # 'l' or 'r'
    bflh_col = f'bflh_{s}'        # column in bflh_df
    hip_col  = f'hip_flexion_{s}' # column in mot_df
    knee_col = f'knee_angle_{s}'  # column in mot_df

    if bflh_col not in bflh_df.columns:
        print(f"  WARNING: '{bflh_col}' not in BFLH CSV — skipping {side} side.")
        return

    for i in range(len(contact_times) - 1):
        t0       = float(contact_times[i])
        t1       = float(contact_times[i + 1])
        duration = t1 - t0

        # ── BFLH peak within this stride window ──────────────────────
        mask        = (bflh_df['time'] >= t0) & (bflh_df['time'] <= t1)
        bflh_window = bflh_df.loc[mask]
        if len(bflh_window) < 2:
            continue

        bflh_vals  = bflh_window[bflh_col].values
        bflh_times = bflh_window['time'].values

        peak_idx  = int(np.argmax(bflh_vals)) # Using argmax here to find the peak BFLH length
        peak_len  = float(bflh_vals[peak_idx])
        peak_time = float(bflh_times[peak_idx])
        peak_pct  = (peak_time - t0) / duration * 100.0

        # ── stride speed from pelvis forward translation ──────────────
        if 'pelvis_tx' in mot_df.columns:
            tx0          = value_at_time(mot_df, t0, 'pelvis_tx')
            tx1          = value_at_time(mot_df, t1, 'pelvis_tx')
            stride_speed = (tx1 - tx0) / duration if duration > 0 else np.nan
        else:
            stride_speed = np.nan

        # ── joint angles at the peak BFLH instant ────────────────────
        hip_flexion    = value_at_time(mot_df, peak_time, hip_col)
        pelvis_tilt    = value_at_time(mot_df, peak_time, 'pelvis_tilt')
        lumbar_ext     = value_at_time(mot_df, peak_time, 'lumbar_extension')
        knee_angle     = value_at_time(mot_df, peak_time, knee_col)

        # Thigh tilt relative to vertical ≈ pelvis_tilt + hip_flexion
        # (both in degrees; positive = forward lean of each segment)
        thigh_tilt = (pelvis_tilt + hip_flexion
                      if not (np.isnan(pelvis_tilt) or np.isnan(hip_flexion))
                      else np.nan)

        records.append({
            'subject_id':        cfg.SUBJECT_NUM,
            'session':           cfg.SESSION,
            'trial_type':        cfg.TRIAL_TYPE,
            'file_tag':          tag,
            'side':              side,
            'stride_index':      i,               # 0-based, chronological
            # stride_number filled in below
            'stride_duration_s': round(duration, 4),
            'stride_speed_ms':   round(float(stride_speed), 4) if not np.isnan(stride_speed) else np.nan,
            'peak_bflh_norm':    round(peak_len, 6),
            'peak_bflh_pct':     round(peak_pct, 2),
            'hip_flexion_deg':   round(hip_flexion, 3) if not np.isnan(hip_flexion) else np.nan,
            'pelvis_tilt_deg':   round(pelvis_tilt,  3) if not np.isnan(pelvis_tilt)  else np.nan,
            'lumbar_ext_deg':    round(lumbar_ext,   3) if not np.isnan(lumbar_ext)   else np.nan,
            'knee_angle_deg':    round(knee_angle,   3) if not np.isnan(knee_angle)   else np.nan,
            'thigh_tilt_deg':    round(thigh_tilt,   3) if not np.isnan(thigh_tilt)   else np.nan,
        })


process_strides(left_contacts,  'left')
process_strides(right_contacts, 'right')

# =====================================================================
# ASSIGN STRIDE NUMBERS  (1 = last stride, matching pipeline convention)
# =====================================================================
df_out = pd.DataFrame(records)

for side in ['left', 'right']:
    mask = df_out['side'] == side
    n    = int(mask.sum())
    # stride_number counts down from n so that the last stride = 1
    df_out.loc[mask, 'stride_number'] = list(range(n, 0, -1))

df_out['stride_number'] = df_out['stride_number'].astype(int)

# Re-order columns: put stride_number right after stride_index
cols = list(df_out.columns)
cols.remove('stride_number')
cols.insert(cols.index('stride_index') + 1, 'stride_number')
df_out = df_out[cols]

df_out = df_out.sort_values(['side', 'stride_number']).reset_index(drop=True)

# =====================================================================
# SAVE & PRINT
# =====================================================================
df_out.to_csv(output_csv, index=False)

print(f"\n{'='*70}")
print(f"Peak BFLH Angles  —  {tag}")
print(f"{'='*70}")
print(df_out.to_string(index=False))
print(f"\nSaved {len(df_out)} stride rows → {output_csv}")

# Per-stride summary
summary_cols = [
    'stride_number', 'stride_speed_ms', 'peak_bflh_norm', 'peak_bflh_pct',
    'hip_flexion_deg', 'pelvis_tilt_deg', 'lumbar_ext_deg',
    'knee_angle_deg', 'thigh_tilt_deg',
]
for side in ['left', 'right']:
    sub = df_out[df_out['side'] == side][summary_cols]
    if sub.empty:
        continue
    print(f"\n{side.upper()} strides:")
    print(sub.to_string(index=False))
