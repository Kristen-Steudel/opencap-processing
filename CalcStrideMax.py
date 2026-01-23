# Load in MOT file for individual steps/strides, calculate the BFLH peak MTU length and velocity for each step/stride, 
# and save the maximum values to a new csv file.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import utilsKinematics

# load stride times csv
left_stride_times_file = r'G:\Shared drives\Stanford Football\January_19\subject2\Kinematics\Outputs\stride_times_left.csv'
left_stride_times_df = pd.read_csv(left_stride_times_file)
right_stride_times_file = r'G:\Shared drives\Stanford Football\January_19\subject2\Kinematics\Outputs\stride_times_right.csv'
right_stride_times_df = pd.read_csv(right_stride_times_file)
last_left_stride_touchdown = left_stride_times_df['time'].iloc[-1]
takeoff_last_left_stride = left_stride_times_df['time'].iloc[-2]
last_right_stride_touchdown = right_stride_times_df['time'].iloc[-1]
takeoff_last_right_stride = right_stride_times_df['time'].iloc[-2]


# load muscle-tendon unit lengths and velocities from csv in subject folder > Kinematics > Outputs
mtu_lengths_file = r'G:\Shared drives\Stanford Football\January_19\subject2\Kinematics\Outputs\muscle_tendon_lengths_ID2_S2_fly_LSTM.csv'
mtu_lengths_df = pd.read_csv(mtu_lengths_file)

# shorten the csv times to only the stride times
left_stride_mtu_lengths_df = mtu_lengths_df[
    (mtu_lengths_df['time'] >= takeoff_last_left_stride) & 
    (mtu_lengths_df['time'] <= last_left_stride_touchdown)
].reset_index(drop=True)
right_stride_mtu_lengths_df = mtu_lengths_df[
    (mtu_lengths_df['time'] >= takeoff_last_right_stride) & 
    (mtu_lengths_df['time'] <= last_right_stride_touchdown)
].reset_index(drop=True)

# shorten mtu_lengths_df to only time and BFLH columns
bflh_length_col = ['bflh_r', 'bflh_l']
left_mtu_lengths_df = left_stride_mtu_lengths_df[['time'] + bflh_length_col]
right_mtu_lengths_df = right_stride_mtu_lengths_df[['time'] + bflh_length_col]


# calculate velocities
left_mtu_lengths_df['bflh_r_vel'] = np.gradient(left_mtu_lengths_df['bflh_r'], left_mtu_lengths_df['time'])
left_mtu_lengths_df['bflh_l_vel'] = np.gradient(left_mtu_lengths_df['bflh_l'], left_mtu_lengths_df['time'])

right_mtu_lengths_df['bflh_r_vel'] = np.gradient(right_mtu_lengths_df['bflh_r'], right_mtu_lengths_df['time'])
right_mtu_lengths_df['bflh_l_vel'] = np.gradient(right_mtu_lengths_df['bflh_l'], right_mtu_lengths_df['time'])

print(left_mtu_lengths_df.head())
print(right_mtu_lengths_df.head())

# find max length and velocity for each stride
left_bflh_l_max_lengths = []
left_bflh_l_max_velocities = []
right_bflh_r_max_lengths = []
right_bflh_r_max_velocities = []

# left side
max_length_l = left_mtu_lengths_df['bflh_l'].max()
left_bflh_l_max_lengths.append(max_length_l)

max_velocity_l = left_mtu_lengths_df['bflh_l_vel'].max()
left_bflh_l_max_velocities.append(max_velocity_l)

# right side
max_length_r = right_mtu_lengths_df['bflh_r'].max()
right_bflh_r_max_lengths.append(max_length_r)

max_velocity_r = right_mtu_lengths_df['bflh_r_vel'].max()
right_bflh_r_max_velocities.append(max_velocity_r)

# Create a plot of the bflh lengths and velocities for left and right sides
plt.figure(figsize=(12, 6))
plt.subplot(2, 2, 1)
plt.plot(left_mtu_lengths_df['time'], left_mtu_lengths_df['bflh_l'], label='Left BFLH Length', color='blue')
plt.axhline(y=max_length_l, color='blue', linestyle='--', label='Left Max Length')
plt.xlabel('Time (s)')
plt.ylabel('Muscle-Tendon Unit Length (m)')
plt.title('BFLH Muscle-Tendon Unit Lengths')
plt.legend()
plt.subplot(2, 2, 2)
plt.plot(right_mtu_lengths_df['time'], right_mtu_lengths_df['bflh_r'], label='Right BFLH Length', color='red')
plt.axhline(y=max_length_r, color='red', linestyle='--', label='Right Max Length')
plt.xlabel('Time (s)')
plt.ylabel('Muscle-Tendon Unit Length (m)')
plt.legend()
plt.subplot(2, 2, 3)
plt.plot(left_mtu_lengths_df['time'], left_mtu_lengths_df['bflh_l_vel'], label='Left BFLH Velocity', color='blue')
plt.axhline(y=max_velocity_l, color='blue', linestyle='--', label='Left Max Velocity')
plt.xlabel('Time (s)')
plt.ylabel('Muscle-Tendon Unit Velocity (m/s)')
plt.legend()
plt.subplot(2, 2, 4)
plt.plot(right_mtu_lengths_df['time'], right_mtu_lengths_df['bflh_r_vel'], label='Right BFLH Velocity', color='red')
plt.axhline(y=max_velocity_r, color='red', linestyle='--', label='Right Max Velocity')
plt.xlabel('Time (s)')
plt.ylabel('Muscle-Tendon Unit Velocity (m/s)')
plt.legend()
plt.tight_layout()
plt.show()
plt.savefig(r'G:\Shared drives\Stanford Football\January_19\subject2\Kinematics\Outputs\bflh_mtu_lengths_velocities_ID2_S2_fly_LSTM.png')