"""
Test spline-based derivative calculation on real motion capture data
Compares spline method vs. finite difference for computing velocities and accelerations
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.interpolate as interpolate
from scipy import signal
import opensim as osim


class SimpleKinematics:
    """Compute coordinate derivatives using cubic splines"""
    
    def __init__(self, time, positions):
        """
        Parameters
        ----------
        time : array
            Time points
        positions : array
            Position data (n_timepoints x n_coordinates)
        """
        self.time = time
        self.Qs = positions
        self.Qds = np.zeros_like(positions)
        self.Qdds = np.zeros_like(positions)
        
        self._compute_derivatives()
    
    def _compute_derivatives(self):
        """Compute velocities and accelerations using spline derivatives"""
        for i in range(self.Qs.shape[1]):
            spline = interpolate.InterpolatedUnivariateSpline(
                self.time, self.Qs[:, i], k=3)
            
            splineD1 = spline.derivative(n=1)
            self.Qds[:, i] = splineD1(self.time)
            
            splineD2 = spline.derivative(n=2)
            self.Qdds[:, i] = splineD2(self.time)


def load_mot_file(mot_path):
    """Load OpenSim .mot file and extract time and coordinate data"""
    
    table = osim.TimeSeriesTable(mot_path)
    time = np.array(table.getIndependentColumn())
    labels = list(table.getColumnLabels())
    data = table.getMatrix().to_numpy()
    
    df = pd.DataFrame(data, columns=labels)
    df.insert(0, 'time', time)
    
    return df, time, labels


def compute_finite_difference(time, positions):
    """Compute derivatives using simple finite difference"""
    dt = np.mean(np.diff(time))
    velocity = np.gradient(positions, dt, axis=0)
    acceleration = np.gradient(velocity, dt, axis=0)
    return velocity, acceleration


def apply_lowpass_filter(time, data, cutoff_freq):
    """Apply Butterworth low-pass filter"""
    dt = np.mean(np.diff(time))
    fs = 1.0 / dt
    nyquist = fs / 2
    
    if cutoff_freq >= nyquist:
        print(f"Warning: Cutoff frequency {cutoff_freq} Hz >= Nyquist frequency {nyquist} Hz")
        return data
    
    w = cutoff_freq / nyquist
    b, a = signal.butter(4, w, 'low')
    
    filtered_data = np.zeros_like(data)
    for i in range(data.shape[1]):
        filtered_data[:, i] = signal.filtfilt(b, a, data[:, i])
    
    return filtered_data


def test_motion_file(mot_path, output_dir=None, selected_coords=None, cutoff_freq=10):
    """
    Test spline vs finite difference on actual motion data
    
    Parameters
    ----------
    mot_path : str
        Path to .mot file
    output_dir : str, optional
        Directory to save plots
    selected_coords : list, optional
        List of coordinate names to plot. If None, plots first 6.
    cutoff_freq : float
        Low-pass filter cutoff frequency in Hz
    """
    
    print("=" * 80)
    print(f"TESTING MOTION FILE: {os.path.basename(mot_path)}")
    print("=" * 80)
    
    # Load motion data
    print("\nLoading motion data...")
    df, time, coord_labels = load_mot_file(mot_path)
    
    positions_rad = df[coord_labels].to_numpy()
    
    # Identify rotational vs translational coordinates
    rot_indices = [i for i, label in enumerate(coord_labels) 
                   if 'pelvis_t' not in label]
    trans_indices = [i for i, label in enumerate(coord_labels) 
                     if 'pelvis_t' in label]
    
    # Convert to degrees for rotational coordinates
    positions = positions_rad.copy()
    positions[:, rot_indices] = np.rad2deg(positions[:, rot_indices])
    
    print(f"\nData info:")
    print(f"  Duration: {time[-1] - time[0]:.2f} seconds")
    print(f"  Samples: {len(time)}")
    print(f"  Sampling rate: {1/np.mean(np.diff(time)):.1f} Hz")
    print(f"  Coordinates: {len(coord_labels)}")
    print(f"    Rotational: {len(rot_indices)}")
    print(f"    Translational: {len(trans_indices)}")
    
    # Method 1: Spline derivatives
    print("\nComputing derivatives with splines...")
    kin_spline = SimpleKinematics(time, positions)
    vel_spline = kin_spline.Qds
    acc_spline = kin_spline.Qdds
    
    # Method 2: Finite difference (unfiltered)
    print("Computing derivatives with finite difference (unfiltered)...")
    vel_fd_raw, acc_fd_raw = compute_finite_difference(time, positions)
    
    # Method 3: Finite difference + low-pass filter
    print(f"Computing derivatives with finite difference + {cutoff_freq} Hz filter...")
    vel_fd_filt = apply_lowpass_filter(time, vel_fd_raw, cutoff_freq)
    acc_fd_filt = apply_lowpass_filter(time, acc_fd_raw, cutoff_freq)
    
    # Calculate RMS differences
    print("\n" + "-" * 80)
    print("RMS DIFFERENCES (comparing to spline method):")
    print("-" * 80)
    
    rms_vel_raw = np.sqrt(np.mean((vel_spline - vel_fd_raw)**2, axis=0))
    rms_vel_filt = np.sqrt(np.mean((vel_spline - vel_fd_filt)**2, axis=0))
    rms_acc_raw = np.sqrt(np.mean((acc_spline - acc_fd_raw)**2, axis=0))
    rms_acc_filt = np.sqrt(np.mean((acc_spline - acc_fd_filt)**2, axis=0))
    
    print(f"\n{'Coordinate':<25} {'Vel (FD raw)':<15} {'Vel (FD filt)':<15} {'Acc (FD raw)':<15} {'Acc (FD filt)':<15}")
    print("-" * 95)
    for i, label in enumerate(coord_labels[:10]):  # Show first 10
        print(f"{label:<25} {rms_vel_raw[i]:<15.3f} {rms_vel_filt[i]:<15.3f} {rms_acc_raw[i]:<15.3f} {rms_acc_filt[i]:<15.3f}")
    
    if len(coord_labels) > 10:
        print(f"... and {len(coord_labels) - 10} more coordinates")
    
    # Select coordinates to plot
    if selected_coords is None:
        plot_coords = coord_labels[:min(6, len(coord_labels))]
    else:
        plot_coords = [c for c in selected_coords if c in coord_labels]
    
    if len(plot_coords) == 0:
        print("\nNo coordinates to plot!")
        return
    
    print(f"\nPlotting {len(plot_coords)} coordinates: {plot_coords}")
    
    # Create plots
    n_coords = len(plot_coords)
    fig, axes = plt.subplots(n_coords, 3, figsize=(18, 4*n_coords))
    
    if n_coords == 1:
        axes = axes.reshape(1, -1)
    
    for i, coord_name in enumerate(plot_coords):
        coord_idx = coord_labels.index(coord_name)
        
        # Position
        axes[i, 0].plot(time, positions[:, coord_idx], 'b-', linewidth=2)
        axes[i, 0].set_ylabel('Position\n(deg or m)', fontsize=10)
        axes[i, 0].set_title(f'{coord_name} - Position', fontsize=11)
        axes[i, 0].grid(True, alpha=0.3)
        
        # Velocity
        axes[i, 1].plot(time, vel_fd_raw[:, coord_idx], '-', alpha=0.3, 
                       label='FD (raw)', color='gray')
        axes[i, 1].plot(time, vel_fd_filt[:, coord_idx], '-', alpha=0.6,
                       label=f'FD (filt {cutoff_freq}Hz)', color='orange')
        axes[i, 1].plot(time, vel_spline[:, coord_idx], '-', linewidth=2,
                       label='Spline', color='red')
        axes[i, 1].set_ylabel('Velocity\n(deg/s or m/s)', fontsize=10)
        axes[i, 1].set_title(f'{coord_name} - Velocity', fontsize=11)
        axes[i, 1].legend(loc='best', fontsize=8)
        axes[i, 1].grid(True, alpha=0.3)
        
        # Acceleration
        axes[i, 2].plot(time, acc_fd_raw[:, coord_idx], '-', alpha=0.3,
                       label='FD (raw)', color='gray')
        axes[i, 2].plot(time, acc_fd_filt[:, coord_idx], '-', alpha=0.6,
                       label=f'FD (filt {cutoff_freq}Hz)', color='orange')
        axes[i, 2].plot(time, acc_spline[:, coord_idx], '-', linewidth=2,
                       label='Spline', color='green')
        axes[i, 2].set_ylabel('Acceleration\n(deg/s² or m/s²)', fontsize=10)
        axes[i, 2].set_title(f'{coord_name} - Acceleration', fontsize=11)
        axes[i, 2].legend(loc='best', fontsize=8)
        axes[i, 2].grid(True, alpha=0.3)
        
        if i == n_coords - 1:
            axes[i, 0].set_xlabel('Time (s)', fontsize=10)
            axes[i, 1].set_xlabel('Time (s)', fontsize=10)
            axes[i, 2].set_xlabel('Time (s)', fontsize=10)
    
    plt.tight_layout()
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        trial_name = os.path.splitext(os.path.basename(mot_path))[0]
        save_path = os.path.join(output_dir, f'spline_test_{trial_name}.png')
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\nPlot saved to: {save_path}")
    
    plt.show()
    
    return {
        'time': time,
        'coord_labels': coord_labels,
        'positions': positions,
        'velocity_spline': vel_spline,
        'velocity_fd_filtered': vel_fd_filt,
        'acceleration_spline': acc_spline,
        'acceleration_fd_filtered': acc_fd_filt,
    }


if __name__ == "__main__":
    
    # Your configuration
    subject_num = 2
    date = 'March_2'
    session_num = '7'
    type_ = 'sprint'
    
    session_id = os.path.normpath(
        f'G:\\Shared drives\\Stanford Football\\{date}\\subject{subject_num}\\OpenSimData\\OpenPose_default\\3-cameras'
    )
    
    trial_name = f'ID{subject_num}_S{session_num}_{type_}_LSTM_filtered'
    mot_path = os.path.join(session_id, 'Kinematics', f'{trial_name}.mot')
    
    if not os.path.exists(mot_path):
        import glob
        candidates = glob.glob(
            os.path.join(session_id, '**', f'{trial_name}.mot'), 
            recursive=True
        )
        if candidates:
            mot_path = candidates[0]
            print(f"Found motion file: {mot_path}")
        else:
            raise FileNotFoundError(f"Could not find {trial_name}.mot")
    
    # Output directory for plots
    output_dir = os.path.join(session_id, 'Kinematics', 'Outputs', 'SplineTests')
    
    # Coordinates of interest (commonly used in gait/sprint analysis)
    selected_coords = [
        'hip_flexion_r', 'hip_flexion_l',
        'knee_angle_r', 'knee_angle_l',
        'ankle_angle_r', 'ankle_angle_l',
        'pelvis_tilt', 'pelvis_list', 'pelvis_rotation'
    ]
    
    # Run the test
    results = test_motion_file(
        mot_path=mot_path,
        output_dir=output_dir,
        selected_coords=selected_coords,
        cutoff_freq=10  # Same as in your original code
    )
    
    # Additional analysis: Compare specific coordinates
    print("\n" + "=" * 80)
    print("DETAILED COMPARISON FOR KEY COORDINATES")
    print("=" * 80)
    
    key_coords = ['hip_flexion_r', 'knee_angle_r', 'ankle_angle_r']
    
    for coord in key_coords:
        if coord in results['coord_labels']:
            idx = results['coord_labels'].index(coord)
            print(f"\n{coord}:")
            print(f"  Position range: {results['positions'][:, idx].min():.2f} to {results['positions'][:, idx].max():.2f} deg")
            print(f"  Velocity range (spline): {results['velocity_spline'][:, idx].min():.2f} to {results['velocity_spline'][:, idx].max():.2f} deg/s")