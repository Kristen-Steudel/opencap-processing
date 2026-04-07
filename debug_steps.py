import pandas as pd
import numpy as np

# Load the step output CSV
output_file = r'G:\Shared drives\Stanford Football\March_2\subject2\CleanedKinematics\filtered_post_augmentation\Outputs\bflh_mtu_max_steps_ID2_S7_sprint_LSTM_filtered.csv'
step_output_df = pd.read_csv(output_file)

print("Full step_output_df:")
print(step_output_df[['step_number', 'step_side']])

# Separate by side
left_steps = step_output_df[step_output_df['step_side'] == 'left']
right_steps = step_output_df[step_output_df['step_side'] == 'right']

print(f"\nLeft steps total: {len(left_steps)}")
print(left_steps[['step_number', 'step_side']].to_string())

print(f"\nRight steps total: {len(right_steps)}")
print(right_steps[['step_number', 'step_side']].to_string())

# Simulate what the script does
n_steps_to_plot = 4
left_steps_to_plot = left_steps.tail(n_steps_to_plot).copy()
right_steps_to_plot = right_steps.tail(n_steps_to_plot).copy()

print(f"\n\nLeft steps to plot (last {n_steps_to_plot}):")
print(f"  Count: {len(left_steps_to_plot)}")
print(left_steps_to_plot[['step_number', 'step_side']].to_string())

print(f"\nRight steps to plot (last {n_steps_to_plot}):")
print(f"  Count: {len(right_steps_to_plot)}")
print(right_steps_to_plot[['step_number', 'step_side']].to_string())

print(f"\n\nPlotted last {len(left_steps_to_plot)} LEFT steps and last {len(right_steps_to_plot)} RIGHT steps")
