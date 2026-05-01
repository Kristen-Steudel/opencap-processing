# Filter kinematics from a .mot file with a zero-phase shift fourth-order
# Butterworth lowpass filter and write the result to a new .mot file.

import numpy as np
from scipy.signal import filtfilt, butter
import opensim as osim

def butter_lowpass_filter(data, cutoff, fs, order=4):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)

# ===== CONFIGURATION =====
filt_freq = 10  # Hz cutoff frequency

input_file = r'G:\Shared drives\Stanford Football\AnalysisCompare\MedFiltPostAugFiltKinFiltLengthFilt\ID5_S7_sprint_LSTM_MedFiltPostAugFiltKinFiltLengthFilt.mot'
output_file = r'G:\Shared drives\Stanford Football\AnalysisCompare\MedFiltPostAugFiltKinFiltLengthFilt\ID5_S7_sprint_LSTM_MedFiltPostAugFiltKinFilt_10Hz_LengthFilt.mot'

# ===== LOAD =====
mot_table = osim.TimeSeriesTable(input_file)
print(f"Loaded: {input_file}")

keys = mot_table.getTableMetaDataKeys()
for key in keys:
    print(f"  {key}: {mot_table.getTableMetaDataString(key)}")

column_labels = mot_table.getColumnLabels()
time = mot_table.getIndependentColumn()

fs = 1.0 / np.mean(np.diff(time))
print(f"Columns: {len(column_labels)}, Frames: {mot_table.getNumRows()}, Fs: {fs:.2f} Hz")

# ===== FILTER =====
n_rows = mot_table.getNumRows()
n_cols = mot_table.getNumColumns()
filtered_matrix = osim.Matrix(n_rows, n_cols)

for i, label in enumerate(column_labels):
    data = mot_table.getDependentColumn(label).to_numpy()
    filtered_data = butter_lowpass_filter(data, cutoff=filt_freq, fs=fs)
    for j in range(len(filtered_data)):
        filtered_matrix.set(j, i, filtered_data[j])

# ===== WRITE =====
mot_table_filtered = osim.TimeSeriesTable(time, filtered_matrix, list(column_labels))
for key in keys:
    mot_table_filtered.addTableMetaDataString(key, mot_table.getTableMetaDataString(key))

osim.STOFileAdapter.write(mot_table_filtered, output_file)
print(f"Filtered kinematics ({filt_freq} Hz) saved to: {output_file}")
