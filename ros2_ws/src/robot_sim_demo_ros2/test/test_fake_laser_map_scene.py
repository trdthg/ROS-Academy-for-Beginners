import tempfile
import textwrap
import unittest
from pathlib import Path

from robot_sim_demo_ros2.fake_laser import OccupancyMapScene


class OccupancyMapSceneTest(unittest.TestCase):
    def test_cast_ray_uses_map_geometry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            image_path = tmp_path / "test_map.pgm"
            yaml_path = tmp_path / "test_map.yaml"

            image_path.write_bytes(
                b"P5\n"
                b"5 5\n"
                b"255\n"
                + bytes(
                    [
                        0, 0, 0, 0, 0,
                        0, 255, 255, 255, 0,
                        0, 255, 0, 255, 0,
                        0, 255, 255, 255, 0,
                        0, 0, 0, 0, 0,
                    ]
                )
            )
            yaml_path.write_text(
                textwrap.dedent(
                    """
                    image: test_map.pgm
                    resolution: 1.0
                    origin: [0.0, 0.0, 0.0]
                    negate: 0
                    occupied_thresh: 0.65
                    free_thresh: 0.196
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            scene = OccupancyMapScene(str(yaml_path))

            self.assertFalse(scene.is_occupied(1.5, 1.5))
            self.assertTrue(scene.is_occupied(2.5, 2.5))
            self.assertAlmostEqual(scene.cast_ray(1.5, 2.5, 0.0, 5.0), 0.5, delta=0.51)
            self.assertAlmostEqual(scene.cast_ray(1.5, 1.5, 1.57, 5.0), 2.5, delta=0.51)
