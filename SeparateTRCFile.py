# Trim TRC marker files into per-stride segments using stride times from a CSV.
#
# The coordinate columns in each data row are written back verbatim —
# only Frame# (col 0) and Time (col 1) are modified.

import os
import glob
import numpy as np

# =====================================================================
# Configuration
# =====================================================================

stride_times_file = r'G:\Shared drives\Stanford Football\March_2\subject5\CleanedKinematics\Outputs\step_times.csv'

trc_folder  = r'G:\Shared drives\Stanford Football\March_2\subject5\MarkerData\OpenPose_1x736_2scales\3-cameras\PostAugmentation_v0.3'
output_dir  = r'G:\Shared drives\Stanford Football\March_2\subject5\CleanedKinematics\Outputs\Strides'

# Time offset applied to stride times before searching within the TRC.
# 'auto' : offset = trc_first_time - stride_times_min  (safest default)
# 0.0    : TRC and stride times share the same origin
# <float>: manually set, e.g. 1.083
trc_time_offset = 'auto'

# =====================================================================
# Load stride times
# =====================================================================

import pandas as pd

stride_times_df = pd.read_csv(stride_times_file)
left_stride_times  = stride_times_df[stride_times_df['side'] == 'left' ]['time'].values
right_stride_times = stride_times_df[stride_times_df['side'] == 'right']['time'].values

print(f"Loaded stride events: {len(left_stride_times)} left, {len(right_stride_times)} right")
print(f"  Left  time range: {left_stride_times.min():.4f} – {left_stride_times.max():.4f} s")
print(f"  Right time range: {right_stride_times.min():.4f} – {right_stride_times.max():.4f} s")

# =====================================================================
# TRC helpers
# =====================================================================

def parse_trc_rows(lines):
    """
    Return a list of (time_float, parts_list) for every data row (line 5+).
    parts_list is the raw tab-split list — nothing is converted to float.
    """
    rows = []
    for line in lines[5:]:
        line = line.rstrip('\r\n')
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            continue
        try:
            t = float(parts[1])
            rows.append((t, parts))
        except ValueError:
            continue
    return rows


def save_trc_segment(header_lines, trc_rows, start_time, end_time, output_path):
    """
    Extract rows where start_time <= time <= end_time and save as a TRC file.
    Only Frame# and Time are rewritten; all coordinate columns are verbatim.
    Returns True if at least one frame was written.
    """
    seg = [(t, parts) for t, parts in trc_rows if start_time <= t <= end_time]

    if not seg:
        return False

    t0               = seg[0][0]
    orig_start_frame = seg[0][1][0].strip()   # frame number string from source file

    with open(output_path, 'w', newline='\n') as f:
        # Line 0: update only the embedded filename at the end
        line0_parts = header_lines[0].rstrip('\r\n').split('\t')
        line0_parts[-1] = os.path.basename(output_path)
        f.write('\t'.join(line0_parts) + '\n')

        # Line 1: metadata label row — unchanged
        f.write(header_lines[1].rstrip('\r\n') + '\n')

        # Line 2: metadata value row — update NumFrames and OrigDataStartFrame
        meta_labels = header_lines[1].strip().split('\t')
        meta_values = header_lines[2].rstrip('\r\n').split('\t')
        new_vals = list(meta_values)
        for idx, lbl in enumerate(meta_labels):
            lbl = lbl.strip()
            if lbl == 'NumFrames' and idx < len(new_vals):
                new_vals[idx] = str(len(seg))
            elif lbl == 'OrigDataStartFrame' and idx < len(new_vals):
                new_vals[idx] = str(orig_start_frame)
        f.write('\t'.join(new_vals) + '\n')

        # Lines 3–4: marker names and axis labels — unchanged
        f.write(header_lines[3].rstrip('\r\n') + '\n')
        f.write(header_lines[4].rstrip('\r\n') + '\n')

        # Data: reset Frame# (col 0) and Time (col 1); everything else verbatim
        for new_frame_idx, (t, parts) in enumerate(seg, start=1):
            new_parts    = list(parts)
            new_parts[0] = str(new_frame_idx)
            new_parts[1] = f'{t - t0:.6f}'
            f.write('\t'.join(new_parts) + '\n')

    return True


# =====================================================================
# Process TRC files
# =====================================================================

trc_files = sorted(glob.glob(os.path.join(trc_folder, '*.trc')))
if not trc_files:
    print(f"\nNo TRC files found in:\n  {trc_folder}")
else:
    print(f"\n{'='*60}")
    print(f"Found {len(trc_files)} TRC file(s) in:")
    print(f"  {trc_folder}")
    print(f"{'='*60}")

    for trc_path in trc_files:
        base = os.path.splitext(os.path.basename(trc_path))[0]
        print(f"\n{os.path.basename(trc_path)}")

        with open(trc_path, 'r') as f:
            trc_lines = f.readlines()

        header_lines = trc_lines[:5]
        trc_rows     = parse_trc_rows(trc_lines)

        if not trc_rows:
            print("  No data rows found — skipping.")
            continue

        trc_t_min = trc_rows[0][0]
        trc_t_max = trc_rows[-1][0]
        print(f"  TRC frames: {len(trc_rows)}   time: {trc_t_min:.4f} – {trc_t_max:.4f} s")

        # Compute offset between TRC time base and stride-times base
        stride_t_min = min(left_stride_times.min(), right_stride_times.min())
        if trc_time_offset == 'auto':
            offset = trc_t_min - stride_t_min
        else:
            offset = float(trc_time_offset)

        if abs(offset) > 0.001:
            print(f"  Time offset: {offset:+.4f} s  (stride times shifted into TRC coordinates)")
        else:
            print(f"  Time offset: {offset:+.4f} s  (already aligned)")

        # Left strides
        left_dir = os.path.join(output_dir, 'left_strides', 'trc')
        os.makedirs(left_dir, exist_ok=True)
        left_ok = 0
        for i in range(len(left_stride_times) - 1):
            t0 = left_stride_times[i]   + offset
            t1 = left_stride_times[i+1] + offset
            out = os.path.join(left_dir, f'{base}_left_stride_{i+1:03d}.trc')
            if save_trc_segment(header_lines, trc_rows, t0, t1, out):
                left_ok += 1
                print(f"  Left  {i+1:3d}: stride {left_stride_times[i]:.3f}–{left_stride_times[i+1]:.3f} s"
                      f"  →  {os.path.basename(out)}")
            else:
                print(f"  Left  {i+1:3d}: WARNING — no TRC frames in {t0:.3f}–{t1:.3f} s")

        # Right strides
        right_dir = os.path.join(output_dir, 'right_strides', 'trc')
        os.makedirs(right_dir, exist_ok=True)
        right_ok = 0
        for i in range(len(right_stride_times) - 1):
            t0 = right_stride_times[i]   + offset
            t1 = right_stride_times[i+1] + offset
            out = os.path.join(right_dir, f'{base}_right_stride_{i+1:03d}.trc')
            if save_trc_segment(header_lines, trc_rows, t0, t1, out):
                right_ok += 1
                print(f"  Right {i+1:3d}: stride {right_stride_times[i]:.3f}–{right_stride_times[i+1]:.3f} s"
                      f"  →  {os.path.basename(out)}")
            else:
                print(f"  Right {i+1:3d}: WARNING — no TRC frames in {t0:.3f}–{t1:.3f} s")

        print(f"  Saved {left_ok} left, {right_ok} right stride files.")

print(f"\nDone.  TRC strides saved under:\n  {output_dir}")
