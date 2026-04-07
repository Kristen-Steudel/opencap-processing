import pandas as pd

output_file = r'G:\Shared drives\Stanford Football\March_2\subject2\CleanedKinematics\filtered_post_augmentation\Outputs\bflh_mtu_max_steps_ID2_S7_sprint_LSTM_filtered.csv'
step_df = pd.read_csv(output_file)

print('Total steps:', len(step_df))
print('\nSteps by side:')
print(step_df.groupby('step_side').size())
print('\nFull dataframe:')
print(step_df[['step_number', 'step_side']])

left_steps = step_df[step_df['step_side'] == 'left']
right_steps = step_df[step_df['step_side'] == 'right']

print(f'\nLeft steps available: {len(left_steps)}')
print(f'Left steps to plot (last 4): {len(left_steps.tail(4))}')
print(left_steps.tail(4)[['step_number', 'step_side']].to_string())

print(f'\nRight steps available: {len(right_steps)}')
print(f'Right steps to plot (last 4): {len(right_steps.tail(4))}')
print(right_steps.tail(4)[['step_number', 'step_side']].to_string())
