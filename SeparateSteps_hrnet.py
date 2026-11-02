"""
Step 3 (HRNet): detect foot contacts from shank angular velocity zero crossings.

Reads/writes only under AccelStepVelocities/ (via pipeline_config_hrnet).
"""

import importlib
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

cfg = importlib.import_module(
    os.environ.get('PIPELINE_CONFIG', 'pipeline_config_hrnet'))
paths = cfg.PATHS
data_folder = paths['shank_angular_velocity_csv']


def find_negative_zero_crossings(time, signal_data):
    crossing_times = []
    crossing_indices = []

    for i in range(len(signal_data) - 1):
        if signal_data[i] > 0 and signal_data[i + 1] <= 0:
            t0, t1 = time[i], time[i + 1]
            v0, v1 = signal_data[i], signal_data[i + 1]
            if v1 != v0:
                crossing_time = t0 - v0 * (t1 - t0) / (v1 - v0)
            else:
                crossing_time = t0
            crossing_times.append(crossing_time)
            crossing_indices.append(i)

    return np.array(crossing_times), np.array(crossing_indices)


def main():
    if not os.path.isfile(data_folder):
        raise FileNotFoundError(
            f'Shank angular velocity CSV not found: {data_folder}\n'
            f'Run compute_shank_ang_vel_hrnet.py first.')

    df = pd.read_csv(data_folder)

    left_crossing_times, _ = find_negative_zero_crossings(
        df['time'].values, df['tibia_l_z'].values)
    right_crossing_times, _ = find_negative_zero_crossings(
        df['time'].values, df['tibia_r_z'].values)

    print(f'Found {len(left_crossing_times)} left shank crossings')
    print(f'Found {len(right_crossing_times)} right shank crossings')

    all_step_times = np.concatenate([left_crossing_times, right_crossing_times])
    all_step_sides = (
        ['left'] * len(left_crossing_times)
        + ['right'] * len(right_crossing_times))
    sort_indices = np.argsort(all_step_times)
    all_step_times_sorted = all_step_times[sort_indices]
    all_step_sides_sorted = [all_step_sides[i] for i in sort_indices]

    step_times_df = pd.DataFrame({
        'time': all_step_times_sorted,
        'side': all_step_sides_sorted,
    })
    left_step_times_df = pd.DataFrame({
        'time': left_crossing_times, 'side': 'left'})
    right_step_times_df = pd.DataFrame({
        'time': right_crossing_times, 'side': 'right'})

    output_dir = paths['outputs_dir']
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'step_times.csv')
    output_path_left = os.path.join(output_dir, 'step_times_left.csv')
    output_path_right = os.path.join(output_dir, 'step_times_right.csv')

    step_times_df.to_csv(output_path, index=False)
    left_step_times_df.to_csv(output_path_left, index=False)
    right_step_times_df.to_csv(output_path_right, index=False)

    print(f'\nStep times saved to:')
    print(f'  All:   {output_path}')
    print(f'  Left:  {output_path_left}')
    print(f'  Right: {output_path_right}')

    plt.figure(figsize=(14, 8))
    plt.plot(df['time'], df['tibia_l_z'], label='Left Shank Z', linewidth=2)
    plt.plot(df['time'], df['tibia_r_z'], label='Right Shank Z', linewidth=2)
    plt.scatter(
        left_crossing_times, np.zeros_like(left_crossing_times),
        color='blue', s=100, marker='v', zorder=5,
        label=f'Left zero crossings (n={len(left_crossing_times)})')
    plt.scatter(
        right_crossing_times, np.zeros_like(right_crossing_times),
        color='orange', s=100, marker='^', zorder=5,
        label=f'Right zero crossings (n={len(right_crossing_times)})')
    plt.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.5)
    plt.xlabel('Time (s)', fontsize=12)
    plt.ylabel('Angular Velocity (rad/s)', fontsize=12)
    plt.title(
        'Shank Sagittal Plane Angular Velocity with '
        'Negative-Going Zero Crossings',
        fontsize=14)
    plt.legend(fontsize=10)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plot_path = os.path.join(output_dir, 'step_times_visualization.png')
    plt.savefig(plot_path, dpi=300)
    plt.close()
    print(f'Plot saved to: {plot_path}')

    print('\n' + '=' * 60)
    print('STEP DETECTION SUMMARY')
    print('=' * 60)
    print(f'Left shank steps:  {len(left_crossing_times)}')
    print(f'Right shank steps: {len(right_crossing_times)}')
    print(f'Total steps:       {len(all_step_times_sorted)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
