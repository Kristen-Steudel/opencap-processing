"""
Convert OpenSim .sto IK solution files to .mot kinematics format.

Handles:
  - Extracting only /value columns (dropping /speed columns)
  - Converting full path column names to short coordinate names
  - Converting rotational coordinates from radians to degrees
  - Skipping patellofemoral (beta) columns not present in .mot files
  - Writing proper .mot header
"""

import numpy as np
import os
import glob

# ===== CONFIGURATION =====
sto_folder = r'G:\Shared drives\Stanford Football\AnalysisCompare\SplinedKinematics'
output_folder = sto_folder  # save .mot files alongside .sto files

TRANSLATIONAL_COORDS = {'pelvis_tx', 'pelvis_ty', 'pelvis_tz'}
SKIP_COORDS = {'knee_angle_r_beta', 'knee_angle_l_beta'}

# ===== FUNCTIONS =====

def parse_sto(filepath):
    """Read an OpenSim .sto file and return header metadata, column names, and data."""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    header_end = None
    for i, line in enumerate(lines):
        if line.strip().lower() == 'endheader':
            header_end = i
            break

    if header_end is None:
        raise ValueError(f"No 'endheader' found in {filepath}")

    col_line = lines[header_end + 1].strip()
    col_names = col_line.split('\t')

    data_lines = lines[header_end + 2:]
    data = []
    for line in data_lines:
        line = line.strip()
        if line:
            data.append([float(v) for v in line.split('\t')])
    data = np.array(data)

    return col_names, data


def sto_col_to_short_name(col):
    """Extract coordinate name from full .sto path like /jointset/hip_r/hip_flexion_r/value."""
    parts = col.strip('/').split('/')
    if len(parts) >= 3:
        return parts[-2]
    return col


def convert_sto_to_mot(sto_path, output_path):
    """Convert a .sto IK solution to .mot kinematics format."""
    col_names, data = parse_sto(sto_path)

    time_idx = 0
    time_data = data[:, time_idx]

    value_indices = []
    short_names = []
    for i, col in enumerate(col_names):
        if i == 0:
            continue
        if not col.endswith('/value'):
            continue
        short = sto_col_to_short_name(col)
        if short in SKIP_COORDS:
            continue
        value_indices.append(i)
        short_names.append(short)

    nRows = data.shape[0]
    nColumns = 1 + len(short_names)  # time + coordinates

    mot_data = np.zeros((nRows, nColumns))
    mot_data[:, 0] = time_data

    for j, (idx, name) in enumerate(zip(value_indices, short_names)):
        col_data = data[:, idx]
        if name not in TRANSLATIONAL_COORDS:
            col_data = np.degrees(col_data)
        mot_data[:, j + 1] = col_data

    header = (
        "Coordinates\n"
        "version=1\n"
        f"nRows={nRows}\n"
        f"nColumns={nColumns}\n"
        "inDegrees=yes\n"
        "\n"
        "Units are S.I. units (second, meters, Newtons, ...)\n"
        "If the header above contains a line with 'inDegrees', this indicates whether rotational values are in degrees (yes) or radians (no).\n"
        "\n"
        "endheader\n"
    )

    all_col_names = ['time'] + short_names

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(header)
        f.write('\t'.join(all_col_names) + '\n')
        for row in mot_data:
            f.write('\t'.join(f'{v:>18.8f}' for v in row) + '\n')

    print(f"  Converted: {os.path.basename(sto_path)}")
    print(f"       -> {output_path}")
    print(f"       {nRows} rows, {len(short_names)} coordinates")


# ===== MAIN =====
sto_files = glob.glob(os.path.join(sto_folder, '*.sto'))

if not sto_files:
    print(f"No .sto files found in: {sto_folder}")
else:
    print(f"Found {len(sto_files)} .sto file(s) in {sto_folder}\n")
    for sto_path in sorted(sto_files):
        basename = os.path.splitext(os.path.basename(sto_path))[0]
        mot_path = os.path.join(output_folder, basename + '.mot')
        convert_sto_to_mot(sto_path, mot_path)
        print()

print("Done.")
