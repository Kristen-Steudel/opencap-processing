"""
Simplified HRNet fly pipeline (February_23).

For each subject:
  1. Shank angular velocity from mmpose kinematics
  2. Foot contacts from negative-going zero crossings
  3. Reed stride velocities (filter by position)

Reads Drive kinematics; writes only to AccelStepVelocities/.

Usage:
    python simplified_pipeline_hrnet.py
    python simplified_pipeline_hrnet.py --subject 13
    python simplified_pipeline_hrnet.py --dry-run
"""

import argparse
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import opensim as osim
import pandas as pd
from scipy.signal import butter, filtfilt

import utilsKinematics

# ----- settings -----
SUBJECTS = [8, 13, 16, 25, 34, 36, 54]
FIRST_STRIDE_TIME = {  # First identified stride time HRNet → black dashed line
    8: 4.893, 13: 5.002, 16: 5.265, 19: 6.19,
    25: 4.05, 34: 3.948, 36: 4.209, 54: 4.855,
}
DATA_DIR = (
    '/Users/steudelk/Library/CloudStorage/GoogleDrive-steudelk@stanford.edu'
    '/Shared drives/Stanford Football/February_23'
)
OUT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'AccelStepVelocities')
DIST_THRESHOLD = -12.0  # keep strides with avg pelvis_x > this


def paths(subj):
    stem = f'ID{subj}_S6_fly'
    tag = f'{stem}_LSTM_hip_flexion_adjusted'
    subj_dir = os.path.join(DATA_DIR, f'subject{subj}')
    out = os.path.join(OUT_ROOT, f'subject{subj}', stem)
    kin = os.path.join(
        subj_dir, 'OpenSimData', 'mmpose_0.8', 'Kinematics', f'{tag}.mot')
    model = os.path.join(
        subj_dir, 'OpenSimData', 'mmpose_0.8', 'Model', 'LaiUhlrich2022_scaled.osim')
    return dict(
        stem=stem, tag=tag, out=out, kin=kin, model=model, subj_dir=subj_dir,
        shank=os.path.join(out, f'shank_ang_vel_{tag}.csv'),
        steps=os.path.join(out, 'step_times.csv'),
        stride_dir=os.path.join(out, 'stride_velocities'),
        go=FIRST_STRIDE_TIME.get(subj),
    )


def lowpass(data, cutoff, fs, order=4):
    b, a = butter(order, cutoff / (0.5 * fs), btype='low')
    return filtfilt(b, a, data)


def neg_zero_crossings(t, y):
    times = []
    for i in range(len(y) - 1):
        if y[i] > 0 and y[i + 1] <= 0:
            if y[i + 1] != y[i]:
                times.append(t[i] - y[i] * (t[i + 1] - t[i]) / (y[i + 1] - y[i]))
            else:
                times.append(t[i])
    return np.asarray(times)


def mark_go(ax, go):
    if go is not None:
        ax.axvline(go, color='k', ls='--', lw=1.5, label=f'First stride ({go:.3f} s)')


def process(subj):
    p = paths(subj)
    os.makedirs(p['out'], exist_ok=True)
    print(f"\n{'=' * 60}\nsubject{subj}  {p['stem']}\n{'=' * 60}")

    # 1) shank angular velocity
    kin = utilsKinematics.kinematics(
        p['subj_dir'], p['tag'], modelName=p['model'],
        lowpass_cutoff_frequency_for_coordinate_values=-1)
    ang = kin.get_body_angular_velocity(
        body_names=['tibia_l', 'tibia_r'], lowpass_cutoff_frequency=3,
        expressed_in='ground')
    ang.to_csv(p['shank'])
    print(f"Shank ang vel → {p['shank']}")

    # 2) foot contacts
    left = neg_zero_crossings(ang['time'].values, ang['tibia_l_z'].values)
    right = neg_zero_crossings(ang['time'].values, ang['tibia_r_z'].values)
    sides = ['left'] * len(left) + ['right'] * len(right)
    order = np.argsort(np.concatenate([left, right]))
    steps = pd.DataFrame({
        'time': np.concatenate([left, right])[order],
        'side': [sides[i] for i in order],
    })
    steps.to_csv(p['steps'], index=False)
    pd.DataFrame({'time': left, 'side': 'left'}).to_csv(
        os.path.join(p['out'], 'step_times_left.csv'), index=False)
    pd.DataFrame({'time': right, 'side': 'right'}).to_csv(
        os.path.join(p['out'], 'step_times_right.csv'), index=False)
    print(f"Steps: {len(left)} L + {len(right)} R = {len(steps)} → {p['steps']}")

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(ang['time'], ang['tibia_l_z'], label='Left Z')
    ax.plot(ang['time'], ang['tibia_r_z'], label='Right Z')
    ax.scatter(left, np.zeros_like(left), c='C0', marker='v', s=60, zorder=5)
    ax.scatter(right, np.zeros_like(right), c='C1', marker='^', s=60, zorder=5)
    ax.axhline(0, color='k', lw=0.5, alpha=0.5)
    mark_go(ax, p['go'])
    ax.set(xlabel='Time (s)', ylabel='Ang vel (rad/s)',
           title=f'subject{subj} shank ang vel + contacts')
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(p['out'], 'step_times_visualization.png'), dpi=200)
    plt.close(fig)

    # 3) Reed stride velocities
    table = osim.TimeSeriesTable(p['kin'])
    t = np.asarray(table.getIndependentColumn())
    pelvis_x = table.getDependentColumn('pelvis_tx').to_numpy()
    fs = 1.0 / np.mean(np.diff(t))
    pelvis_x_filt = lowpass(pelvis_x, cutoff=2, fs=fs)

    rows, series = [], []
    for contact_i in range(len(steps) - 1):
        # One stride = interval between consecutive foot contacts
        start_time = steps.iloc[contact_i]['time']
        end_time = steps.iloc[contact_i + 1]['time']
        start_side = steps.iloc[contact_i]['side']
        end_side = steps.iloc[contact_i + 1]['side']

        # Indices of this step/stride within the full-run arrays (t, pelvis_x_filt)
        start_idx_step = int(np.argmin(np.abs(t - start_time)))
        end_idx_step = int(np.argmin(np.abs(t - end_time)))
        if end_idx_step <= start_idx_step:
            end_idx_step = start_idx_step + 1

        stride_position = pelvis_x_filt[start_idx_step:end_idx_step + 1]
        stride_time = t[start_idx_step:end_idx_step + 1]
        stride_inst_vel = (
            np.gradient(stride_position, stride_time)
            if len(stride_time) > 1 else np.array([0.0]))

        stride_number = contact_i + 1  # 1 = furthest from camera
        displacement = pelvis_x_filt[end_idx_step] - pelvis_x_filt[start_idx_step]
        duration = end_time - start_time
        avg_velocity = displacement / duration  # Reed: Δx / Δt

        rows.append({
            'stride_number': stride_number,
            'start_time': start_time,
            'end_time': end_time,
            'start_side': start_side,
            'end_side': end_side,
            'stride_duration': duration,
            'displacement': displacement,
            'avg_velocity': avg_velocity,
            'avg_position': float(np.mean(stride_position)),
            'start_position': pelvis_x_filt[start_idx_step],
            'end_position': pelvis_x_filt[end_idx_step],
        })
        series.append((
            stride_number,
            stride_time - start_time,  # time relative to stride start
            stride_position,
            stride_inst_vel,
        ))

    summary = pd.DataFrame(rows)
    os.makedirs(p['stride_dir'], exist_ok=True)
    summary.to_csv(os.path.join(p['stride_dir'], 'stride_velocity_summary.csv'), index=False)

    valid = summary[summary['avg_position'] > DIST_THRESHOLD].copy()
    valid.to_csv(
        os.path.join(p['stride_dir'], 'stride_velocity_summary_filtered.csv'), index=False)
    keep = set(valid['stride_number'])
    print(f"Strides: {len(summary)} total, {len(valid)} kept (pos > {DIST_THRESHOLD} m)")

    # Near-camera mean speeds (last strides are closest to camera)
    mean_2_3 = mean_3_4 = None
    if len(summary) >= 3:
        speed2 = abs(summary.iloc[-2]['avg_velocity'])
        speed3 = abs(summary.iloc[-3]['avg_velocity'])
        mean_2_3 = 0.5 * (speed2 + speed3)
        n2, n3 = int(summary.iloc[-2]['stride_number']), int(summary.iloc[-3]['stride_number'])
        print(
            f"2nd+3rd to last: strides {n3}+{n2} "
            f"({speed3:.3f}, {speed2:.3f} m/s) → mean={mean_2_3:.3f} m/s"
        )
    if len(summary) >= 4:
        speed3 = abs(summary.iloc[-3]['avg_velocity'])
        speed4 = abs(summary.iloc[-4]['avg_velocity'])
        mean_3_4 = 0.5 * (speed3 + speed4)
        n3, n4 = int(summary.iloc[-3]['stride_number']), int(summary.iloc[-4]['stride_number'])
        print(
            f"3rd+4th to last: strides {n4}+{n3} "
            f"({speed4:.3f}, {speed3:.3f} m/s) → mean={mean_3_4:.3f} m/s"
        )

    for n, tt, pos, vel in series:
        if n not in keep:
            continue
        pd.DataFrame({'time': tt, 'position': pos, 'velocity': vel}).to_csv(
            os.path.join(p['stride_dir'], f'stride_{n:03d}_velocity.csv'), index=False)

    # quality plot
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=False)
    axes[0].plot(t, pelvis_x_filt, color='C0')
    axes[0].axhline(DIST_THRESHOLD, color='orange', ls='--', label=f'threshold {DIST_THRESHOLD} m')
    for _, r in summary.iterrows():
        c = 'green' if r['stride_number'] in keep else 'red'
        axes[0].axvspan(r['start_time'], r['end_time'], color=c, alpha=0.2)
    mark_go(axes[0], p['go'])
    axes[0].set(ylabel='Pelvis x (m)', title=f'subject{subj} Reed stride quality')
    axes[0].legend(); axes[0].grid(alpha=0.3)

    axes[1].plot(t, np.gradient(pelvis_x_filt, t), color='C0')
    for _, r in summary.iterrows():
        c = 'green' if r['stride_number'] in keep else 'red'
        axes[1].axvspan(r['start_time'], r['end_time'], color=c, alpha=0.2)
    mark_go(axes[1], p['go'])
    axes[1].set(xlabel='Time (s)', ylabel='Vel (m/s)')
    axes[1].legend(); axes[1].grid(alpha=0.3)

    colors = ['green' if n in keep else 'red' for n in summary['stride_number']]
    axes[2].bar(summary['stride_number'], np.abs(summary['avg_velocity']),
                color=colors, edgecolor='k', alpha=0.7)
    axes[2].set(xlabel='Stride # (1 = furthest from camera)', ylabel='Speed (m/s)')
    axes[2].grid(axis='y', alpha=0.3)

    # Annotate near-camera mean speeds on the bar chart
    note_lines = []
    if mean_2_3 is not None:
        note_lines.append(f'Mean speed 2nd+3rd to last: {mean_2_3:.2f} m/s')
    if mean_3_4 is not None:
        note_lines.append(f'Mean speed 3rd+4th to last: {mean_3_4:.2f} m/s')
    if note_lines:
        axes[2].text(
            0.02, 0.95, '\n'.join(note_lines),
            transform=axes[2].transAxes, va='top', ha='left', fontsize=10,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.85, edgecolor='0.5'))

    fig.tight_layout()
    fig.savefig(os.path.join(p['stride_dir'], 'stride_quality_analysis.png'), dpi=200)
    plt.close(fig)
    print(f"Outputs → {p['out']}")


def main():
    parser = argparse.ArgumentParser(description='Simplified HRNet fly pipeline')
    parser.add_argument('--subject', type=int, action='append')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    subjects = args.subject or SUBJECTS

    for s in subjects:
        p = paths(s)
        ok = os.path.isfile(p['kin']) and os.path.isfile(p['model'])
        print(f"subject{s}: {'READY' if ok else 'MISSING'}  {p['kin']}")
        if args.dry_run or not ok:
            continue
        process(s)


if __name__ == '__main__':
    main()
