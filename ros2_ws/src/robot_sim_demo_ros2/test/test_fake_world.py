import math
import unittest

from robot_sim_demo_ros2.fake_world import cast_ray, scene_segments


class FakeWorldTest(unittest.TestCase):
    def test_cast_ray_hits_room_wall(self):
        segments = scene_segments((-5.0, 5.0, -5.0, 5.0), [])
        distance = cast_ray((0.0, 0.0), 0.0, 8.0, segments)
        self.assertAlmostEqual(distance, 5.0)

    def test_cast_ray_hits_obstacle_before_wall(self):
        segments = scene_segments((-5.0, 5.0, -5.0, 5.0), [(1.5, 2.5, -1.0, 1.0)])
        distance = cast_ray((0.0, 0.0), 0.0, 8.0, segments)
        self.assertAlmostEqual(distance, 1.5)

    def test_cast_ray_diagonal_stays_bounded(self):
        segments = scene_segments((-5.0, 5.0, -5.0, 5.0), [])
        distance = cast_ray((0.0, 0.0), math.pi / 4.0, 8.0, segments)
        self.assertGreater(distance, 7.0)
