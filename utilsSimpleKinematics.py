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

# Your SimpleKinematics class
class SimpleKinematics:
    def __init__(self, time, positions):
        """
        time: array of time points
        positions: array of position data (could be joint angles)
        """
        self.time = time
        self.Qs = positions  # Position data
        self.Qds = np.zeros_like(positions)   # Velocity (to be computed)
        self.Qdds = np.zeros_like(positions)  # Acceleration (to be computed)
        
        # Compute derivatives using splines
        self._compute_derivatives()
    
    def _compute_derivatives(self):
        # Loop through each coordinate (column)
        for i in range(self.Qs.shape[1]):
            # Create a cubic spline for this coordinate
            spline = interpolate.InterpolatedUnivariateSpline(
                self.time, self.Qs[:, i], k=3)
            
            # First derivative (velocity)
            splineD1 = spline.derivative(n=1)
            self.Qds[:, i] = splineD1(self.time)
            
            # Second derivative (acceleration)
            splineD2 = spline.derivative(n=2)
            self.Qdds[:, i] = splineD2(self.time)

