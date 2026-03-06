# Plot the biceps femoris long head muscle-tendon unit velocities that were
# extracted using the opensim function to get_lengthening_velocities. 

import pandas as pd
import matplotlib.pyplot as plt
import os


velocities_file_path = rf'G:\Shared drives\Stanford Football\March_2\subject2\Kinematics\Outputs\muscle_tendon_velocities_ID2_S7_sprint_LSTM_filtered.csv'
step_times = f'G:\Shared drives\Stanford Football\March_2\subject2\Kinematics\Outputs\stride_times.csv'
output_dir = rf'G:\Shared drives\Stanford Football\March_2\subject2\Kinematics\Outputs\MTU_Velocity_Plots'
os.makedirs(output_dir, exist_ok=True)

# Display the stride times to see when steps were and how I want to plot the velocities with respect to the steps
stride_times_df = pd.read_csv(step_times)
print(stride_times_df.head())

# Load the muscle-tendon velocities from the CSV file
velocities_df = pd.read_csv(velocities_file_path)
# Check the column names to find the one corresponding to the biceps femoris long head
print("Column names in the velocities CSV file:")
print(velocities_df.columns)

# Separate the left and right steps
left_steps = stride_times_df[stride_times_df['side'] == 'left']['time'].values
right_steps = stride_times_df[stride_times_df['side']== 'right']['time'].values

print(f"Number of left steps: {len(left_steps)}")
print(f"Number of right steps: {len(right_steps)}")

def create_stride_intervals(step_times):
    intervals = []
    for i in range(len(step_times) - 1):
        intervals.append((step_times[i], step_times[i + 1]))
    return intervals

left_intervals = create_stride_intervals(left_steps)
right_intervals = create_stride_intervals(right_steps)

# Plot left steps
fig, axes = plt.subplots(len(left_intervals), 1, figsize = (12, 4*len(left_intervals)))
for idx, (stride_start, stride_end) in enumerate(left_intervals):
    step_velocities = velocities_df[(velocities_df['time'] >= stride_start) & (velocities_df['time'] <= stride_end)]
    normalized_time = 100 * (step_velocities['time'] - stride_start) / (stride_end - stride_start)
    axes[idx].plot(normalized_time, step_velocities['bflh_l'], label='Left Biceps Femoris Long Head Velocity', linewidth = 2, color = 'blue')
    axes[idx].set_title(f'Left Step {idx + 1} Velocity')
    axes[idx].set_xlabel('Time (s)')
    axes[idx].set_ylabel('Velocity (m/s)')
    axes[idx].legend()
    axes[idx].grid()

plt.tight_layout()
plt.show()
plt.savefig(f'{output_dir}/BFLH_MTU_Velocity_Left_Strides.png', dpi=300)
plt.close()

# Plot right steps
fig, axes = plt.subplots(len(right_intervals), 1, figsize = (12, 4*len(right_intervals)))
for idx, (stride_start, stride_end) in enumerate(right_intervals):                      
    step_velocities = velocities_df[(velocities_df['time'] >= stride_start) & (velocities_df['time'] <= stride_end)]
    normalized_time = 100 * (step_velocities['time'] - stride_start) / (stride_end - stride_start)
    axes[idx].plot(normalized_time, step_velocities['bflh_r'], label='Right Biceps Femoris Long Head Velocity', linewidth = 2, color = 'orange')
    axes[idx].set_title(f'Right Step {idx + 1} Velocity')
    axes[idx].set_xlabel('Time (s)')
    axes[idx].set_ylabel('Velocity (m/s)')
    axes[idx].legend()
    axes[idx].grid()

plt.tight_layout()
plt.show()
plt.savefig(f'{output_dir}/BFLH_MTU_Velocity_Right_Strides.png', dpi=300)
plt.close()



# Overlay all left steps
plt.figure(figsize=(12, 6))
for idx, (stride_start, stride_end) in enumerate(left_intervals):
    step_velocities = velocities_df[(velocities_df['time'] >= stride_start) & (velocities_df['time'] <= stride_end)]
    normalized_time = 100 * (step_velocities['time'] - stride_start) / (stride_end - stride_start)
    plt.plot(normalized_time, step_velocities['bflh_l'], alpha=0.6, label=f'Step {idx + 1}')

plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
plt.xlabel('Step Cycle (%)')
plt.ylabel('Velocity (m/s)')
plt.title('Left BFLH MTU Velocity - All Steps Overlaid')
plt.legend()
plt.grid(True, alpha=0.3)
plt.xlim(0, 100)
plt.tight_layout()
plt.show()
plt.savefig(f'{output_dir}/BFLH_MTU_Left_Strides_lay_over.png', dpi=300)
plt.close()


# Overlay all right steps
plt.figure(figsize=(12, 6))
for idx, (stride_start, stride_end) in enumerate(right_intervals):
    step_velocities = velocities_df[(velocities_df['time'] >= stride_start) & (velocities_df['time'] <= stride_end)]
    normalized_time = 100 * (step_velocities['time'] - stride_start) / (stride_end - stride_start)
    plt.plot(normalized_time, step_velocities['bflh_r'], alpha=0.6, label=f'Step {idx + 1}')

plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
plt.xlabel('Step Cycle (%)')
plt.ylabel('Velocity (m/s)')
plt.title('Right BFLH MTU Velocity - All Steps Overlaid')
plt.legend()
plt.grid(True, alpha=0.3)
plt.xlim(0, 100)
plt.tight_layout()
plt.show()
plt.savefig(f'{output_dir}/BFLH_MTU_Right_Strides_lay_over.png', dpi=300)
plt.close()

# Full time series with step boundaries
plt.figure(figsize=(14, 6))
plt.plot(velocities_df['time'], velocities_df['bflh_l'], label='Left BFLH', linewidth=1.5, alpha=0.7)
plt.plot(velocities_df['time'], velocities_df['bflh_r'], label='Right BFLH', linewidth=1.5, alpha=0.7)

# Add vertical lines for foot strikes
for time in left_steps:
    plt.axvline(x=time, color='blue', linestyle='--', alpha=0.5, linewidth=0.8)
for time in right_steps:
    plt.axvline(x=time, color='red', linestyle='--', alpha=0.5, linewidth=0.8)

plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
plt.xlabel('Time (s)')
plt.ylabel('Velocity (m/s)')
plt.title('BFLH MTU Velocity Over Time (Blue = Left Strikes, Red = Right Strikes)')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

plt.savefig(f'{output_dir}/BFLH_MTU_Velocity_Over_Time.png', dpi=300)
plt.close()
