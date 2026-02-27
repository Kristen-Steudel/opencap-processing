# Determine the speed of running of each stride using the pelvis x direction velocity - assume this is in the direction of running. Then, determine the average speed of each stride and filter out strides that are above or below a certain threshold. This is to remove strides where the subject was not running at a consistent speed, which may indicate that they were not running at all (e.g., walking, standing still, etc.).
# This assumption may need to be adjusted/revisited later depending on how well it performs.

# Using Reed's methods: low-pass filter the pelvis translation signal with a 2-Hz cutoff frequency
# Divide the pelvis displacement during the step along the running direction by the step time. 

import numpy as np
import opensim as osim
import pandas as pd
from scipy.signal import butter, filtfilt
import matplotlib.pyplot as plt

def butter_lowpass_filter(data, cutoff=2, fs=1000, order=4):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = filtfilt(b, a, data)
    return y

date = 'February_9'
subject_id = 'subject2'

data_dir = f'G:\\Shared drives\\Stanford Football'
date_dir = f'{data_dir}\\{date}'
subject_dir = f'{date_dir}\\{subject_id}'

# Add in file that contains the step times so that we can calculate the speed of each stride based on the times
stride_times = f'G:\Shared drives\Stanford Football\February_9\subject2\Kinematics\Outputs\stride_times.csv'

times_frame = pd.read_csv(stride_times)

kinematics_file = f'{subject_dir}\\OpenSimData\\OpenPose_default\\3-cameras\\Kinematics\\ID2_S5_decel_LSTM_filtered.mot'

# Load the kinematics data
mot_table = osim.TimeSeriesTable(kinematics_file)

# Check what metadata exists in the original file
print("\nOriginal file metadata:")
keys = mot_table.getTableMetaDataKeys()
for key in keys:
    print(f"  {key}: {mot_table.getTableMetaDataString(key)}")

column_labels = mot_table.getColumnLabels()
print("Column Labels:", list(column_labels))

pelvis_x = mot_table.getDependentColumn('pelvis_tx').to_numpy() # Assuming 'pelvis_tx' is the x direction velocity of the pelvis
pelvis_x_filtered = butter_lowpass_filter(pelvis_x, cutoff=2, fs=1000, order=4)
pelvis_x_velocity = np.gradient(pelvis_x_filtered, mot_table.getIndependentColumn()) # Compute the velocity using the gradient of the filtered position with time

# Create a plot of the pelvis x position over time to visually inspect it
time = mot_table.getIndependentColumn()
plt.figure(figsize=(10, 5))
plt.plot(time, pelvis_x, label='Original Pelvis X Position')
plt.plot(time, pelvis_x_filtered, label='Filtered Pelvis X Position')
plt.xlabel('Time (s)')
plt.ylabel('Pelvis X Position (m)')
plt.title('Pelvis X Position Over Time')
plt.grid(True)
plt.legend()
plt.show()

# Create a plot of the pelvis x velocity over time to visually inspect it
plt.figure(figsize=(10, 5))
plt.plot(time, pelvis_x_velocity)
plt.xlabel('Time (s)')
plt.ylabel('Pelvis X Velocity (m/s)')
plt.title('Pelvis X Velocity Over Time')
plt.grid(True)
plt.show()


