# Filter the Kinematics with a zero-phase shift fourth-order Butterworth 15-Hz cutoff frequency

import numpy as np
import os
from scipy.signal import filtfilt, butter
import opensim as osim
import pandas as pd

def butter_lowpass_filter(data, cutoff=15, fs=1000, order=4):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = filtfilt(b, a, data)
    return y


# Configuration imported from pipeline_config.py (edit once, used by all scripts)
# import pipeline_config as cfg
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib as _il
cfg = _il.import_module(os.environ.get('PIPELINE_CONFIG', 'pipeline_config_CameraTest'))
paths = cfg.PATHS
filt_freq = cfg.FILT_FREQ
kinematics_file = paths['kinematics_input']

# Load the kinematics data
mot_table = osim.TimeSeriesTable(kinematics_file)

# Check what metadata exists in the original file
print("\nOriginal file metadata:")
keys = mot_table.getTableMetaDataKeys()
for key in keys:
    print(f"  {key}: {mot_table.getTableMetaDataString(key)}")

column_labels = mot_table.getColumnLabels()
print("Column Labels:", list(column_labels))

time = mot_table.getIndependentColumn()

fs = 1/np.mean(np.diff(time))
print(f"Sampling frequency: {fs:.2f} Hz")

# Filter all columns and store in a matrix
n_rows = mot_table.getNumRows()
n_cols = mot_table.getNumColumns()

filtered_matrix = osim.Matrix(n_rows, n_cols)

for i, label in enumerate(column_labels):
    data = mot_table.getDependentColumn(label).to_numpy()
    filtered_data = butter_lowpass_filter(data, cutoff=filt_freq, fs=fs, order=4)
    
    # Fill the matrix column by column
    for j in range(len(filtered_data)):
        filtered_matrix.set(j, i, filtered_data[j])

# Create new table with filtered data
mot_table_filtered = osim.TimeSeriesTable(time, filtered_matrix, list(column_labels))

# Copy metadata from original table
for key in keys:
    mot_table_filtered.addTableMetaDataString(key, mot_table.getTableMetaDataString(key))

output_file = paths['kinematics_filtered']

# Write to file
os.makedirs(os.path.dirname(output_file), exist_ok=True)
osim.STOFileAdapter.write(mot_table_filtered, output_file)
print(f"Filtered kinematics saved to: {output_file}")