# Streamlined kinematics processing for BFLH analysis and literature comparison.
# Takes a .mot kinematics file + model path, computes MTU lengths/velocities,
# coordinate values, and shank angular velocity, then saves all CSVs and plots
# to a single output folder.

import os
import utilsKinematics
from utilsPlotting import plot_dataframe
import opensim as osim
import pandas as pd
import numpy as np

# ===== CONFIGURATION =====
# Input paths
mot_file = r"G:\Shared drives\Stanford Football\AnalysisCompare\SplinedKinematics\sprint_spline_ik_solution_knot80.mot"
model_file = r"G:\Shared drives\Stanford Football\AnalysisCompare\LaiUhlrich2022_scaled.osim"
# Output folder (all CSVs and plots saved here)
output_dir = r"G:\Shared drives\Stanford Football\AnalysisCompare\SplinedKinematicsKnot80\Outputs"

# Toggle: filter BFLH muscle-tendon lengths/velocities or use raw
filter_mtu_lengths = True # Change this to False when I am running a test without LengthFilt in the folder name
mtu_length_filter_freq = 10  # Hz (only used when filter_mtu_lengths = True)

# Other filter settings
coord_filter_freq = 10       # Hz for coordinate values/speeds/accelerations
angular_vel_filter_freq = 2  # Hz for shank angular velocity (step detection)
velocity_filter_freq = 10     # Hz for MTU velocity output

# Trial label (used in output filenames)
trial_label = os.path.splitext(os.path.basename(mot_file))[0]

# ===== SETUP =====
os.makedirs(output_dir, exist_ok=True)

# Session root: utilsKinematics first checks {session_root}/OpenSimData/...,
# then falls back to a recursive search under session_root for the .mot and .osim.
# Set this to the common parent folder of your .mot and .osim files.
session_root = os.path.dirname(model_file)

modelName = os.path.splitext(os.path.basename(model_file))[0]
print(f"Session root: {session_root}")
print(f"Model: {modelName}")
print(f"Trial: {trial_label}")
print(f"Filter MTU lengths: {filter_mtu_lengths}" +
      (f" ({mtu_length_filter_freq} Hz)" if filter_mtu_lengths else " (raw)"))

# ===== NEUTRAL MTU LENGTHS FOR NORMALIZATION =====
def get_neutral_mtu_lengths(model_path):
    model = osim.Model(model_path)
    model.initSystem()
    neutral = {}
    muscles = model.getMuscles()
    for i in range(muscles.getSize()):
        m = muscles.get(i)
        neutral[m.getName()] = m.getOptimalFiberLength() + m.getTendonSlackLength()
    return neutral

neutral_mtu_lengths = get_neutral_mtu_lengths(model_file)
print("\nNeutral MTU Lengths (BFLH):")
for name, length in neutral_mtu_lengths.items():
    if 'bflh' in name.lower():
        print(f"  {name}: {length:.4f} m")

# ===== PROCESS KINEMATICS =====
kin = utilsKinematics.kinematics(
    session_root, trial_label, modelName=modelName,
    lowpass_cutoff_frequency_for_coordinate_values=coord_filter_freq)
print(f"\nLoaded: {kin.motionPath}")
print(f"Frames: {kin.table.getNumRows()}")

# Coordinate values, speeds, accelerations
coord_values = kin.get_coordinate_values(in_degrees=True)
coord_speeds = kin.get_coordinate_speeds(in_degrees=True, lowpass_cutoff_frequency=coord_filter_freq)
coord_accels = kin.get_coordinate_accelerations(in_degrees=True, lowpass_cutoff_frequency=coord_filter_freq)

# Muscle-tendon lengths (raw always computed; filtered based on toggle)
mtu_freq = mtu_length_filter_freq if filter_mtu_lengths else -1
mtu_lengths = kin.get_muscle_tendon_lengths(lowpass_cutoff_frequency=mtu_freq)
mtu_lengths_raw = kin.get_muscle_tendon_lengths(lowpass_cutoff_frequency=-1)

# Muscle-tendon velocities (spline approach)
vel_freq_for_lengths = mtu_length_filter_freq if filter_mtu_lengths else -1
mtu_velocities = kin.get_muscle_tendon_velocity_spline_approach(
    lowpass_cutoff_frequency_for_lengths=vel_freq_for_lengths,
    lowpass_cutoff_frequency_for_velocities=velocity_filter_freq)

# Shank angular velocity (for step detection)
angular_vel = kin.get_body_angular_velocity(
    body_names=['tibia_l', 'tibia_r'],
    lowpass_cutoff_frequency=angular_vel_filter_freq,
    expressed_in='ground')

# Normalize muscle-tendon lengths
normalized_mtu = mtu_lengths.copy()
for col in normalized_mtu.columns:
    if col != 'time' and col in neutral_mtu_lengths:
        normalized_mtu[col] = normalized_mtu[col] / neutral_mtu_lengths[col]

# ===== BUILD FILENAME SUFFIX =====
filt_tag = f"filtered_{mtu_length_filter_freq}Hz" if filter_mtu_lengths else "raw"

# ===== SAVE CSVs =====
def save(df, name):
    path = os.path.join(output_dir, f'{name}_{trial_label}_{filt_tag}.csv')
    df.to_csv(path, index=False if 'time' in df.columns else True)
    print(f"  Saved: {os.path.basename(path)}")

print(f"\nSaving CSVs to: {output_dir}")
save(coord_values, 'coordinate_values')
save(coord_speeds, 'coordinate_speeds')
save(angular_vel, 'shank_angular_velocity')
save(mtu_lengths, 'muscle_tendon_lengths')
save(mtu_lengths_raw, 'muscle_tendon_lengths_raw')
save(mtu_velocities, 'muscle_tendon_velocities_spline')
save(normalized_mtu, 'normalized_muscle_tendon_lengths')

# BFLH-only normalized lengths
bflh_cols = ['time'] + [c for c in normalized_mtu.columns if 'bflh' in c.lower()]
normalized_mtu[bflh_cols].to_csv(
    os.path.join(output_dir, f'normalized_bflh_length_{trial_label}_{filt_tag}.csv'), index=False)
print(f"  Saved: normalized_bflh_length_{trial_label}_{filt_tag}.csv")

# ===== PLOTS =====
print("\nSaving plots...")

plot_dataframe(
    dataframes=[coord_values],
    xlabel='Time (s)', ylabel='Pos (m or deg)',
    title='Coordinate values', labels=[trial_label],
    save_path=os.path.join(output_dir, f'coordinate_values_{trial_label}_{filt_tag}.png'))


plot_dataframe(
    dataframes=[coord_speeds],
    y=['hip_flexion_l', 'hip_flexion_r', 'knee_angle_l', 'knee_angle_r'],
    xlabel='Time (s)', ylabel='Vel (deg/s)',
    title='Coordinate speeds', labels=[trial_label],
    save_path=os.path.join(output_dir, f'coordinate_speeds_{trial_label}_{filt_tag}.png'))

plot_dataframe(
    dataframes=[mtu_lengths],
    y=['bflh_r', 'bflh_l'],
    xlabel='Time (s)', title=f'BFLH MTU Lengths ({filt_tag})',
    labels=[trial_label],
    save_path=os.path.join(output_dir, f'bflh_muscle_tendon_lengths_{trial_label}_{filt_tag}.png'))

plot_dataframe(
    dataframes=[normalized_mtu],
    y=['bflh_r', 'bflh_l'],
    xlabel='Time (s)', ylabel='Normalized Length',
    title=f'Normalized BFLH MTU Lengths ({filt_tag})',
    labels=[trial_label],
    save_path=os.path.join(output_dir, f'normalized_bflh_lengths_{trial_label}_{filt_tag}.png'))

plot_dataframe(
    dataframes=[mtu_velocities],
    y=['bflh_r', 'bflh_l'],
    xlabel='Time (s)', ylabel='Velocity (m/s)',
    title=f'BFLH MTU Velocities - Spline ({filt_tag})',
    labels=[trial_label],
    save_path=os.path.join(output_dir, f'bflh_muscle_tendon_velocities_spline_{trial_label}_{filt_tag}.png'))

plot_dataframe(
    dataframes=[angular_vel],
    y=['tibia_l_z', 'tibia_r_z'],
    xlabel='Time (s)', ylabel='Angular Velocity (rad/s)',
    title='Shank Sagittal Angular Velocity',
    labels=[trial_label],
    save_path=os.path.join(output_dir, f'shank_angular_velocity_{trial_label}_{filt_tag}.png'))

print("\nDone!")
