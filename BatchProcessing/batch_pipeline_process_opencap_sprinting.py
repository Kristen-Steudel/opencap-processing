"""
Deprecated entry point — use process_opencap_sprinting/batch_pipeline.py instead.

This wrapper forwards to the self-contained sprinting batch folder so the
main BatchProcessing/ workflow and batch_configs/ are never touched.
"""

import os
import runpy
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_TARGET = os.path.join(_HERE, 'process_opencap_sprinting', 'batch_pipeline.py')

if __name__ == '__main__':
    sys.argv[0] = _TARGET
    runpy.run_path(_TARGET, run_name='__main__')
