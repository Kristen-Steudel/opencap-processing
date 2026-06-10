"""Convert bilevel optimization .sto kinematics to pipeline-ready .mot files."""

import os


def bilevel_sto_to_mot(results_dir, trial_stem, sto_suffix='_bilevel_solution_filtered'):
    """Convert a bilevel .sto file to a clean .mot in results/Kinematics/.

    Parameters
    ----------
    results_dir : str
        process-opencap-sprinting results directory.
    trial_stem : str
        Trial prefix, e.g. ``ID2_S7_sprint``.
    sto_suffix : str
        Suffix before ``.sto`` (default: filtered bilevel solution).

    Returns
    -------
    str
        Path to the written .mot file.
    """
    import opensim as osim

    sto_path = os.path.join(results_dir, f'{trial_stem}{sto_suffix}.sto')
    if not os.path.isfile(sto_path):
        raise FileNotFoundError(f'Bilevel STO not found: {sto_path}')

    mot_dir = os.path.join(results_dir, 'Kinematics')
    mot_path = os.path.join(mot_dir, f'{trial_stem}.mot')
    os.makedirs(mot_dir, exist_ok=True)

    table = osim.TimeSeriesTable(sto_path)
    time = table.getIndependentColumn()

    clean_labels = []
    clean_data = []

    for label in table.getColumnLabels():
        label_str = str(label)
        if '/speed' in label_str:
            continue

        coord_name = (
            label_str.split('/')[-2] if '/value' in label_str else label_str)

        if coord_name not in clean_labels:
            clean_labels.append(coord_name)
            clean_data.append(table.getDependentColumn(label).to_numpy())

    matrix = osim.Matrix(len(time), len(clean_labels))
    for j in range(len(clean_labels)):
        for i in range(len(time)):
            matrix.set(i, j, clean_data[j][i])

    new_table = osim.TimeSeriesTable(time, matrix, clean_labels)
    new_table.addTableMetaDataString('inDegrees', 'no')
    osim.STOFileAdapter().write(new_table, mot_path)

    print(f'Created: {mot_path}')
    return mot_path


def ensure_bilevel_mot(results_dir, trial_stem, sto_path=None):
    """Convert STO to MOT when the .mot is missing or older than the STO."""
    if sto_path is None:
        sto_path = os.path.join(
            results_dir, f'{trial_stem}_bilevel_solution_filtered.sto')

    mot_path = os.path.join(results_dir, 'Kinematics', f'{trial_stem}.mot')
    if os.path.isfile(mot_path):
        if not os.path.isfile(sto_path):
            return mot_path
        if os.path.getmtime(mot_path) >= os.path.getmtime(sto_path):
            return mot_path

    return bilevel_sto_to_mot(results_dir, trial_stem)
