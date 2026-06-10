# Compare kinematic data to Reed OpenCap Accelerative Running mean & standard deviation

import pandas as pd
import matplotlib.pyplot as plt

left_csv_600 = r'/Users/steudelk/Documents/Github/process-opencap-sprinting/LiteratureData/ReedGurchiek/constant600/group_mean_left.csv'
left_csv_std_600 = r'/Users/steudelk/Documents/Github/process-opencap-sprinting/LiteratureData/ReedGurchiek/constant600/group_std_left.csv'
right_side_csv_600 = r'/Users/steudelk/Documents/Github/process-opencap-sprinting/LiteratureData/ReedGurchiek/constant600/group_mean_right.csv'
right_side_csv_std_600 = r'/Users/steudelk/Documents/Github/process-opencap-sprinting/LiteratureData/ReedGurchiek/constant600/group_std_right.csv'

df_left = pd.read_csv(left_csv_600)
df_right = pd.read_csv(right_side_csv_600)
df_left_std = pd.read_csv(left_csv_std_600)
df_right_std = pd.read_csv(right_side_csv_std_600)

plt.figure(figsize=(10, 6))
plt.plot(df_left['Percent_Stride'], df_left['pelvis_tilt'], label='pelvis tilt left')
plt.fill_between(df_left['Percent_Stride'], 
                 df_left['pelvis_tilt'] - df_left_std['pelvis_tilt'],  # lower bound
                 df_left['pelvis_tilt'] + df_left_std['pelvis_tilt'],  # upper bound
                 alpha=0.3,  # transparency (0-1)
                 label='± 1 std')
plt.xlabel('Percent Stride')
plt.ylabel('Pelvis Tilt (degrees)')
plt.title('Pelvis Tilt vs. Percent Stride')
plt.legend()


# Add in the results from the simulations
results = r'/Users/steudelk/Documents/Github/process-opencap-sprinting/results/Kinematics/ID2_S7_sprint.mot'
stride_times = r'/Users/steudelk/Library/CloudStorage/GoogleDrive-steudelk@stanford.edu/Shared drives/Stanford Football/March_2/subject2/Kinematics/Outputs/stride_times.csv'

df_results = pd.read_csv(results)
df_stride_times = pd.read_csv(stride_times)
stride_start = df_stride_times['time'].iloc[-4]  # Get the last left stride start time
stride_end = df_stride_times['time'].iloc[-2]  # Get the last left stride end time

df_results_stride = df_results[(df_results['time'] >= stride_start) & (df_results['time'] <= stride_end)]
df_percent = df_results_stride.copy()
df_percent['time'] = (df_percent['time'] - stride_start) / (stride_end - stride_start) * 100
df_percent['pelvis_tilt'] = df_percent['pelvis_tilt']

# Need to normalize to a percent of 100%
plt.plot(df_percent['time'], df_percent['pelvis_tilt'], label='Simulation Results')
plt.show()