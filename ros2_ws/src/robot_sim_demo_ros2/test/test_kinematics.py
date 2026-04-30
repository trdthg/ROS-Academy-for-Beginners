import math
import unittest

from robot_sim_demo_ros2.kinematics import integrate_diff_drive, normalize_angle, wheel_angular_velocities


class KinematicsTest(unittest.TestCase):
    def test_normalize_angle_wraps(self):
        self.assertAlmostEqual(normalize_angle(3.0 * math.pi), math.pi)

    def test_integrate_diff_drive_moves_forward(self):
        x, y, yaw = integrate_diff_drive(0.0, 0.0, 0.0, 0.5, 0.0, 2.0)
        self.assertAlmostEqual(x, 1.0)
        self.assertAlmostEqual(y, 0.0)
        self.assertAlmostEqual(yaw, 0.0)

    def test_wheel_angular_velocities_split_turning(self):
        left, right = wheel_angular_velocities(0.3, 0.2, 0.46, 0.095)
        self.assertLess(left, right)
