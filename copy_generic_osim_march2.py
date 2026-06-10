#!/usr/bin/env python3
"""
Copy LaiUhlrich2022_generic.osim from subject66 to every subject in March_2.

Source:
  .../March_2/subject66/OpenSimData/OpenPose_default/3-cameras/Model/
      LaiUhlrich2022_generic.osim

Destination (per subject):
  .../March_2/subject{N}/OpenSimData/OpenPose_default/3-cameras/Model/
      LaiUhlrich2022_generic.osim

Usage:
    python copy_generic_osim_march2.py --dry-run
    python copy_generic_osim_march2.py
    python copy_generic_osim_march2.py --include-subject 66
"""

import argparse
import os
import re
import shutil

DEFAULT_MARCH_2 = (
    '/Users/steudelk/Library/CloudStorage/GoogleDrive-steudelk@stanford.edu'
    '/Shared drives/Stanford Football/March_2'
)
MODEL_REL = os.path.join(
    'OpenSimData', 'OpenPose_default', '3-cameras', 'Model')
FILENAME = 'LaiUhlrich2022_generic.osim'
SOURCE_SUBJECT = 66

SUBJECT_RE = re.compile(r'^subject(\d+)$', re.IGNORECASE)


def list_subject_dirs(march_2_dir):
    subjects = []
    for name in os.listdir(march_2_dir):
        match = SUBJECT_RE.match(name)
        if match:
            subjects.append(int(match.group(1)))
    return sorted(subjects)


def main():
    parser = argparse.ArgumentParser(
        description='Copy LaiUhlrich2022_generic.osim to all March_2 subjects.')
    parser.add_argument(
        '--march-2-dir', default=DEFAULT_MARCH_2,
        help='Path to the March_2 collection folder.')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be copied without writing files.')
    parser.add_argument(
        '--include-subject', type=int, default=SOURCE_SUBJECT, metavar='N',
        help=f'Subject number to copy from (default: {SOURCE_SUBJECT}).')
    parser.add_argument(
        '--skip-source', action='store_true', default=True,
        help='Skip copying onto the source subject folder (default: true).')
    parser.add_argument(
        '--no-skip-source', action='store_false', dest='skip_source',
        help='Also copy onto the source subject folder.')
    parser.add_argument(
        '--create-missing-dirs', action='store_true',
        help='Create Model/ if a subject folder is missing it.')
    args = parser.parse_args()

    march_2 = os.path.abspath(args.march_2_dir)
    if not os.path.isdir(march_2):
        raise SystemExit(f'March_2 folder not found:\n  {march_2}')

    source_dir = os.path.join(
        march_2, f'subject{args.include_subject}', MODEL_REL)
    source_file = os.path.join(source_dir, FILENAME)
    if not os.path.isfile(source_file):
        raise SystemExit(f'Source file not found:\n  {source_file}')

    copied = []
    skipped = []
    missing_dirs = []

    for subject_num in list_subject_dirs(march_2):
        if args.skip_source and subject_num == args.include_subject:
            skipped.append((subject_num, 'source subject'))
            continue

        dest_dir = os.path.join(march_2, f'subject{subject_num}', MODEL_REL)
        dest_file = os.path.join(dest_dir, FILENAME)

        if not os.path.isdir(dest_dir):
            if args.create_missing_dirs:
                if args.dry_run:
                    print(f'[dry-run] would create: {dest_dir}')
                else:
                    os.makedirs(dest_dir, exist_ok=True)
            else:
                missing_dirs.append(subject_num)
                continue

        if args.dry_run:
            action = 'overwrite' if os.path.isfile(dest_file) else 'copy'
            print(f'[dry-run] {action}: subject{subject_num}')
            print(f'          -> {dest_file}')
        else:
            shutil.copy2(source_file, dest_file)
            print(f'Copied: subject{subject_num}')
            print(f'     -> {dest_file}')
        copied.append(subject_num)

    print()
    print('=' * 60)
    print('Summary')
    print('=' * 60)
    print(f'  Source:       {source_file}')
    print(f'  {"Would copy" if args.dry_run else "Copied"}:   {len(copied)} subject(s)')
    if skipped:
        print(f'  Skipped:      {len(skipped)}')
        for num, reason in skipped:
            print(f'    - subject{num} ({reason})')
    if missing_dirs:
        print(f'  Missing dir:  {len(missing_dirs)}')
        for num in missing_dirs:
            print(f'    - subject{num}')
        print('  Re-run with --create-missing-dirs to create missing Model folders.')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
