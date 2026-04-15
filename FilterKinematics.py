# Filter the Kinematics with a zero-phase shift fourth-order Butterworth 15-Hz cutoff frequency

import numpy as np
from scipy.signal import filtfilt, butter
import opensim as osim
import pandas as pd

def butter_lowpass_filter(data, cutoff=15, fs=1000, order=4):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = filtfilt(b, a, data)
    return y


# Requirements to Change for each run
#######################################################################################
date = 'March_2'
subject_id = 'subject2'
subject_num = (subject_id.replace('subject', ''))
type = 'sprint'
session_num = '7'
filt_freq = 10  # Hz, was 15 Hz
#######################################################################################

data_dir = f'G:\\Shared drives\\Stanford Football'
date_dir = f'{data_dir}\\{date}'
subject_dir = f'{date_dir}\\{subject_id}'

# For kinematics without cleaning
#kinematics_file = f'{subject_dir}\\OpenSimData\\OpenPose_default\\3-cameras\\Kinematics\\ID{subject_num}_S{session_num}_{type}_LSTM.mot'
# For kinematics with cleaning
kinematics_file = f'{subject_dir}\\CleanedKinematics\\OpenPose_default\\3-cameras\\Kinematics\\FiltPostAug\\ID{subject_num}_S{session_num}_{type}NoSync_LSTM_filt15Hz.mot'

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

# For filtered kinematics without marker cleaning
#output_file = f'{subject_dir}\\OpenSimData\\OpenPose_default\\3-cameras\\Kinematics\\ID{subject_num}_S{session_num}_{type}_LSTM_filtered_{filt_freq}Hz.mot'
# For filtered kinematics with marker cleaning
output_file = f'{subject_dir}\\CleanedKinematics\\OpenPose_default\\3-cameras\\Kinematics\\FiltPostAug\\ID{subject_num}_S{session_num}_{type}_LSTM_filtpostaug15Hz_filteredkinematics_{filt_freq}Hz.mot'

# Write to file
osim.STOFileAdapter.write(mot_table_filtered, output_file)
print(f"Filtered kinematics saved to: {output_file}")