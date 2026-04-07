# Load in MOT file for individual steps/steps, calculate the BFLH peak MTU length and velocity for each step/step, 
# and save the maximum values to a new csv file.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

import utilsKinematics

subject = 2
session = "S7"
base_path = rf'G:\Shared drives\Stanford Football\March_2\subject{subject}\CleanedKinematics\filtered_post_augmentation\Outputs'
type = 'sprint'
filt_freq = 8  # Hz, was 15 Hz

# Load step times csv
left_step_times_file = rf'{base_path}\step_times_left.csv'
left_step_times_df = pd.read_csv(left_step_times_file)
right_step_times_file = rf'{base_path}\step_times_right.csv'
right_step_times_df = pd.read_csv(right_step_times_file)

# IMPORTANT: HOW STEPS ARE CURRENTLY BEING DEFINED
# ================================================
# The current approach analyzes CONSECUTIVE CONTACTS OF THE SAME FOOT (which is technically a STRIDE, not a STEP):
# - "LEFT steps" = from left contact at time[i] to left contact at time[i+1]
#   * This is a LEFT STRIDE (left foot leaves ground and returns to ground)
#   * During this period, bflh_l (left leg) is analyzed
#
# - "RIGHT steps" = from right contact at time[i] to right contact at time[i+1]  
#   * This is a RIGHT STRIDE (right foot leaves ground and returns to ground)
#   * During this period, bflh_r (right leg) is analyzed
#
# WHAT THIS MEANS:
# If the user wants to analyze a TRUE STEP (alternating foot contacts), where the analyzed leg
# is the one that CONTACTS the ground at the END of the step, then we need to:
# 1. Merge left_step_times and right_step_times into one chronological sequence
# 2. For each consecutive pair of contact times, the step side = the foot that contacts at the END
# 3. Example: if sequence is [L(0.2s), R(0.5s), L(0.8s), ...], then:
#    - Step 1: L(0.2s) → R(0.5s)  = RIGHT step (right foot lands at end)
#    - Step 2: R(0.5s) → L(0.8s)  = LEFT step (left foot lands at end)

# load muscle-tendon unit lengths and velocities from csv in subject folder > Kinematics > Outputs

# This is the path for bflh lengths that are not normalized yet
#mtu_lengths_file = rf'{base_path}\muscle_tendon_lengths_ID{subject}_{session}_fly_LSTM.csv'

# Plot the normalized lengths using this csv file instead
mtu_lengths_file = rf'{base_path}\normalized_muscle_tendon_lengths_ID{subject}_{session}_{type}_LSTM_filtpostaug15Hz_filteredkinematics_15Hz_filtered_15Hz.csv'
#normalized_muscle_tendon_lengths_ID2_S7_sprint_LSTM_filtpostaug15Hz_filteredkinematics_15Hz_filtered_15Hz
mtu_lengths_df = pd.read_csv(mtu_lengths_file)

print(f"Loaded {len(left_step_times_df)} left foot contact times")
print(f"Loaded {len(right_step_times_df)} right foot contact times")

# ===== MERGE CONTACTS INTO CHRONOLOGICAL SEQUENCE =====
# Create a unified timeline of all foot contacts with side information
all_contacts = []
for _, row in left_step_times_df.iterrows():
    all_contacts.append({'time': row['time'], 'side': 'left'})
for _, row in right_step_times_df.iterrows():
    all_contacts.append({'time': row['time'], 'side': 'right'})

# Sort by time to get chronological order
all_contacts_df = pd.DataFrame(all_contacts).sort_values('time').reset_index(drop=True)
print(f"\nTotal contacts (left + right): {len(all_contacts_df)}")
print(f"Contact sequence:\n{all_contacts_df.head(10)}")

# ===== PROCESS TRUE STEPS =====
# Each step goes from one foot contact to the next (opposite) foot contact
# The step is NAMED after the foot that LANDS at the END
step_data = []

for i in range(0, len(all_contacts_df) - 1):
    start_time = all_contacts_df.loc[i, 'time']
    start_side = all_contacts_df.loc[i, 'side']
    
    end_time = all_contacts_df.loc[i + 1, 'time']
    end_side = all_contacts_df.loc[i + 1, 'side']
    
    # Skip if same foot is contacting twice (shouldn't happen with good data)
    if start_side == end_side:
        print(f"WARNING: Same foot contacts at indices {i} and {i+1}")
        continue
    
    # Extract step data between contacts
    step_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(step_mtu_df) == 0:
        continue
    
    # Select the appropriate muscle based on which foot LANDS at the END of the step
    # (the step is named after the landing foot, so we analyze that leg)
    if end_side == 'left':
        muscle_col = 'bflh_l'
    else:
        muscle_col = 'bflh_r'
    
    # Calculate velocity (with check for minimum data points)
    if len(step_mtu_df) > 1:
        step_mtu_df['bflh_vel'] = np.gradient(step_mtu_df[muscle_col], step_mtu_df['time'])
    else:
        # Not enough data points for gradient calculation
        continue
    
    # Find max values
    max_length = step_mtu_df[muscle_col].max()
    max_velocity = step_mtu_df['bflh_vel'].max()
    avg_velocity = step_mtu_df[step_mtu_df['bflh_vel'] > 0]['bflh_vel'].mean()
    
    # Store results in reverse-numbered list (step 1 = closest to capture volume)
    step_data.append({
        'step_number': None,  # Will be renumbered after collecting all steps
        'step_side': end_side,  # Side of the landing foot (foot being analyzed)
        'start_time': start_time,
        'start_contact': start_side,
        'end_time': end_time,
        'end_contact': end_side,
        'step_duration': end_time - start_time,
        'bflh_max_length': max_length,
        'bflh_max_velocity': max_velocity,
        'bflh_avg_lengthening_velocity': avg_velocity
    })

# Create output DataFrame
step_output_df = pd.DataFrame(step_data)

# RENUMBER STEPS IN REVERSE ORDER (step 1 = closest to capture volume, highest time)
# Step 1 should be the LAST step chronologically
step_output_df = step_output_df.iloc[::-1].reset_index(drop=True)
step_output_df['step_number'] = range(1, len(step_output_df) + 1)
step_output_df = step_output_df.sort_values('step_number').reset_index(drop=True)

# Save to CSV file
output_file = rf'{base_path}\bflh_mtu_max_steps_ID{subject}_{session}_{type}_LSTM_filtered.csv'
step_output_df.to_csv(output_file, index=False)

print(f"\n{'='*60}")
print(f"Processed {len(step_output_df)} TRUE STEPS")
print(f"(Steps are defined as: from one foot contact → opposite foot contact)")
print(f"(Step is named after the foot that LANDS at the END)")
print(f"{'='*60}")
print(step_output_df)
print(f"\nSaved to: {output_file}")
print(step_output_df.describe())

# Create visualization for all steps
fig, axes = plt.subplots(2, 3, figsize=(15, 10))

# Separate steps by side for visualization
left_steps = step_output_df[step_output_df['step_side'] == 'left']
right_steps = step_output_df[step_output_df['step_side'] == 'right']

# Max lengths by step number, colored by side
step_numbers = step_output_df['step_number']
max_lengths = step_output_df['bflh_max_length']
colors = ['blue' if side == 'left' else 'red' for side in step_output_df['step_side']]
axes[0, 0].scatter(step_numbers, max_lengths, c=colors, s=100)
# Plot connecting lines with matching colors
for i in range(len(step_numbers) - 1):
    axes[0, 0].plot(step_numbers.iloc[i:i+2], max_lengths.iloc[i:i+2], 
                   color=colors[i], linewidth=2, alpha=0.6)
axes[0, 0].set_xlabel('Step Number')
axes[0, 0].set_ylabel('Max MTU Length (Normalized)')
axes[0, 0].set_title('BFLH Max Lengths Across All Steps (Blue=Left, Red=Right)')
axes[0, 0].grid(True, alpha=0.3)

# Max velocities by step number
max_velocities = step_output_df['bflh_max_velocity']
axes[0, 1].scatter(step_numbers, max_velocities, c=colors, s=100)
# Plot connecting lines with matching colors
for i in range(len(step_numbers) - 1):
    axes[0, 1].plot(step_numbers.iloc[i:i+2], max_velocities.iloc[i:i+2], 
                   color=colors[i], linewidth=2, alpha=0.6)
axes[0, 1].set_xlabel('Step Number')
axes[0, 1].set_ylabel('Max MTU Velocity (Normalized/s)')
axes[0, 1].set_title('BFLH Max Velocities Across All Steps')
axes[0, 1].grid(True, alpha=0.3)

# Average lengthening velocities
avg_velocities = step_output_df['bflh_avg_lengthening_velocity']
axes[0, 2].scatter(step_numbers, avg_velocities, c=colors, s=100)
# Plot connecting lines with matching colors
for i in range(len(step_numbers) - 1):
    axes[0, 2].plot(step_numbers.iloc[i:i+2], avg_velocities.iloc[i:i+2], 
                   color=colors[i], linewidth=2, alpha=0.6)
axes[0, 2].set_xlabel('Step Number')
axes[0, 2].set_ylabel('Avg Lengthening Velocity (Norm/s)')
axes[0, 2].set_title('BFLH Avg Lengthening Velocities')
axes[0, 2].grid(True, alpha=0.3)

# Left steps only
axes[1, 0].plot(left_steps['step_number'], left_steps['bflh_max_length'], 'o-', color='blue', label='Left')
axes[1, 0].set_xlabel('Step Number')
axes[1, 0].set_ylabel('Max MTU Length (Normalized)')
axes[1, 0].set_title('LEFT Steps - Max Lengths')
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].legend()

# Right steps only
axes[1, 1].plot(right_steps['step_number'], right_steps['bflh_max_length'], 'o-', color='red', label='Right')
axes[1, 1].set_xlabel('Step Number')
axes[1, 1].set_ylabel('Max MTU Length (Normalized)')
axes[1, 1].set_title('RIGHT Steps - Max Lengths')
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].legend()

# Step durations
axes[1, 2].scatter(step_numbers, step_output_df['step_duration'], c=colors, s=100)
# Plot connecting lines with matching colors
for i in range(len(step_numbers) - 1):
    axes[1, 2].plot(step_numbers.iloc[i:i+2], step_output_df['step_duration'].iloc[i:i+2], 
                   color=colors[i], linewidth=2, alpha=0.6)
axes[1, 2].set_xlabel('Step Number')
axes[1, 2].set_ylabel('Step Duration (s)')
axes[1, 2].set_title('Step Duration (time from one contact to next)')
axes[1, 2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(rf'{base_path}\bflh_mtu_all_steps_summary_ID{subject}_{session}_{type}_LSTM_filtered.png', dpi=300, bbox_inches='tight')
plt.show()

print("\nSummary plot saved successfully!")

# ========== OVERLAY PLOTS: Plot first N steps by side ==========

# Create overlay plots for FIRST N STEPS (separated by left/right side)
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Define normalized x-axis (0 to 100%)
normalized_x = np.linspace(0, 100, 101)

# Get first N left and right steps (steps 1-8 are closest to capture volume with reverse numbering)
n_steps_to_plot = 4  # 4 left + 4 right = 8 total steps (steps 1-8 with reverse numbering)
left_steps_to_plot = left_steps.head(n_steps_to_plot).copy()
right_steps_to_plot = right_steps.head(n_steps_to_plot).copy()

# Generate colors for each step - use more regular/constrained color ranges
from matplotlib import cm
left_colors = cm.Blues(np.linspace(0.5, 0.95, len(left_steps_to_plot)))
right_colors = cm.Reds(np.linspace(0.5, 0.95, len(right_steps_to_plot)))

# ===== PLOT LEFT STEPS - MTU LENGTHS =====
for plot_idx, (idx, step_row) in enumerate(left_steps_to_plot.iterrows()):
    start_time = step_row['start_time']
    end_time = step_row['end_time']
    step_num = step_row['step_number']
    
    step_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(step_mtu_df) > 1:
        # Interpolate to normalized 0-100% step cycle
        step_percent = np.linspace(0, 100, len(step_mtu_df))
        interp_func = interp1d(step_percent, step_mtu_df['bflh_l'], 
                              kind='linear', fill_value='extrapolate')
        normalized_length = interp_func(normalized_x)
        
        # Plot with label showing step number
        axes[0, 0].plot(normalized_x, normalized_length, 
                       color=left_colors[plot_idx], label=f'Step {step_num}', linewidth=2.5)
        
        # Mark the peak
        max_idx = np.argmax(normalized_length)
        axes[0, 0].plot(normalized_x[max_idx], normalized_length[max_idx], 
                       'o', color=left_colors[plot_idx], markersize=10, 
                       markeredgecolor='black', markeredgewidth=2)

axes[0, 0].set_xlabel('Step Cycle (%)', fontsize=14)
axes[0, 0].set_ylabel('MTU Length (Normalized)', fontsize=14)
axes[0, 0].set_title(f'LEFT Steps - BFLH Lengths (First {len(left_steps_to_plot)} steps)', fontsize=14, fontweight='bold')
axes[0, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=11)
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].set_xlim([0, 100])

# ===== PLOT RIGHT STEPS - MTU LENGTHS =====
for plot_idx, (idx, step_row) in enumerate(right_steps_to_plot.iterrows()):
    start_time = step_row['start_time']
    end_time = step_row['end_time']
    step_num = step_row['step_number']
    
    step_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(step_mtu_df) > 1:
        # Interpolate to normalized 0-100% step cycle
        step_percent = np.linspace(0, 100, len(step_mtu_df))
        interp_func = interp1d(step_percent, step_mtu_df['bflh_r'], 
                              kind='linear', fill_value='extrapolate')
        normalized_length = interp_func(normalized_x)
        
        # Plot with label showing step number
        axes[0, 1].plot(normalized_x, normalized_length, 
                       color=right_colors[plot_idx], label=f'Step {step_num}', linewidth=2.5)
        
        # Mark the peak
        max_idx = np.argmax(normalized_length)
        axes[0, 1].plot(normalized_x[max_idx], normalized_length[max_idx], 
                       'o', color=right_colors[plot_idx], markersize=10, 
                       markeredgecolor='black', markeredgewidth=2)

axes[0, 1].set_xlabel('Step Cycle (%)', fontsize=14)
axes[0, 1].set_ylabel('MTU Length (Normalized)', fontsize=14)
axes[0, 1].set_title(f'RIGHT Steps - BFLH Lengths (First {len(right_steps_to_plot)} steps)', fontsize=14, fontweight='bold')
axes[0, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=11)
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].set_xlim([0, 100])

# ===== PLOT LEFT STEPS - MTU VELOCITIES =====
for plot_idx, (idx, step_row) in enumerate(left_steps_to_plot.iterrows()):
    start_time = step_row['start_time']
    end_time = step_row['end_time']
    step_num = step_row['step_number']
    
    step_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(step_mtu_df) > 1:
        # Calculate velocity and interpolate
        step_mtu_df['bflh_l_vel'] = np.gradient(step_mtu_df['bflh_l'], step_mtu_df['time'])
        step_percent = np.linspace(0, 100, len(step_mtu_df))
        interp_func = interp1d(step_percent, step_mtu_df['bflh_l_vel'], 
                              kind='linear', fill_value='extrapolate')
        normalized_velocity = interp_func(normalized_x)
        
        # Plot
        axes[1, 0].plot(normalized_x, normalized_velocity, 
                       color=left_colors[plot_idx], label=f'Step {step_num}', linewidth=2.5)
        
        # Mark the peak
        max_idx = np.argmax(normalized_velocity)
        axes[1, 0].plot(normalized_x[max_idx], normalized_velocity[max_idx], 
                       'o', color=left_colors[plot_idx], markersize=10, 
                       markeredgecolor='black', markeredgewidth=2)

axes[1, 0].set_xlabel('Step Cycle (%)', fontsize=14)
axes[1, 0].set_ylabel('MTU Velocity (Norm Units/s)', fontsize=14)
axes[1, 0].set_title(f'LEFT Steps - BFLH Velocities (First {len(left_steps_to_plot)} steps)', fontsize=14, fontweight='bold')
axes[1, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=11)
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].set_xlim([0, 100])

# ===== PLOT RIGHT STEPS - MTU VELOCITIES =====
for plot_idx, (idx, step_row) in enumerate(right_steps_to_plot.iterrows()):
    start_time = step_row['start_time']
    end_time = step_row['end_time']
    step_num = step_row['step_number']
    
    step_mtu_df = mtu_lengths_df[
        (mtu_lengths_df['time'] >= start_time) & 
        (mtu_lengths_df['time'] <= end_time)
    ].reset_index(drop=True)
    
    if len(step_mtu_df) > 1:
        # Calculate velocity and interpolate
        step_mtu_df['bflh_r_vel'] = np.gradient(step_mtu_df['bflh_r'], step_mtu_df['time'])
        step_percent = np.linspace(0, 100, len(step_mtu_df))
        interp_func = interp1d(step_percent, step_mtu_df['bflh_r_vel'], 
                              kind='linear', fill_value='extrapolate')
        normalized_velocity = interp_func(normalized_x)
        
        # Plot
        axes[1, 1].plot(normalized_x, normalized_velocity, 
                       color=right_colors[plot_idx], label=f'Step {step_num}', linewidth=2.5)
        
        # Mark the peak
        max_idx = np.argmax(normalized_velocity)
        axes[1, 1].plot(normalized_x[max_idx], normalized_velocity[max_idx], 
                       'o', color=right_colors[plot_idx], markersize=10, 
                       markeredgecolor='black', markeredgewidth=2)

axes[1, 1].set_xlabel('Step Cycle (%)', fontsize=14)
axes[1, 1].set_ylabel('MTU Velocity (Norm Units/s)', fontsize=14)
axes[1, 1].set_title(f'RIGHT Steps - BFLH Velocities (First {len(right_steps_to_plot)} steps)', fontsize=14, fontweight='bold')
axes[1, 1].legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=11)
axes[1, 1].grid(True, alpha=0.3)
axes[1, 1].set_xlim([0, 100])

plt.tight_layout()
plt.savefig(rf'{base_path}\bflh_mtu_last_steps_overlay_ID{subject}_{session}_{type}_LSTM_filtered.png', 
            dpi=300, bbox_inches='tight')
plt.show()

print(f"\nOverlay plot saved successfully!")
print(f"Plotted first {len(left_steps_to_plot)} LEFT steps and first {len(right_steps_to_plot)} RIGHT steps")