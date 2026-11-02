"""
Step 2 (HRNet): compute shank angular velocity only.

Reads mmpose_0.8 kinematics + scaled model from Drive.
Writes shank_ang_vel_*.csv under local AccelStepVelocities/.
"""

import importlib
import os
import sys

import matplotlib
matplotlib.use('Agg')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

cfg = importlib.import_module(
    os.environ.get('PIPELINE_CONFIG', 'pipeline_config_hrnet'))
paths = cfg.PATHS

import utilsKinematics


def main():
    mot_path = paths['kinematics_input']
    model_path = paths['model_path']
    trial_name = paths['trial_name']
    outputs_dir = paths['outputs_dir']
    out_csv = paths['shank_angular_velocity_csv']

    if not os.path.isfile(mot_path):
        raise FileNotFoundError(f'Kinematics .mot not found: {mot_path}')
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f'Scaled model not found: {model_path}')

    os.makedirs(outputs_dir, exist_ok=True)

    # Search from subject_dir so utilsKinematics finds mmpose_0.8/Kinematics/*.mot
    session_dir = paths['subject_dir']
    print(f'Trial:  {trial_name}')
    print(f'Motion: {mot_path}')
    print(f'Model:  {model_path}')

    kin = utilsKinematics.kinematics(
        session_dir,
        trial_name,
        modelName=model_path,
        lowpass_cutoff_frequency_for_coordinate_values=-1,
    )
    print(f'Loaded motion: {kin.motionPath}')
    print(f'Loaded model:  {kin.modelPath}')

    # Match example_cleaned: both shanks, 3 Hz, expressed in ground
    ang_vel = kin.get_body_angular_velocity(
        body_names=['tibia_l', 'tibia_r'],
        lowpass_cutoff_frequency=3,
        expressed_in='ground',
    )

    ang_vel.to_csv(out_csv)
    print(f'Saved shank angular velocity: {out_csv}')
    print(f'Columns: {list(ang_vel.columns)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
