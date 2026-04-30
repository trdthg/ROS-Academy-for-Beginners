import unittest
from pathlib import Path

from robot_sim_demo_ros2 import (
    fake_laser,
    fake_world,
    gazebo_interface_bridge,
    kinematics,
    simple_base_sim,
)


class RobotSimSmokeTest(unittest.TestCase):
    def test_modules_import(self):
        self.assertIsNotNone(fake_laser)
        self.assertIsNotNone(fake_world)
        self.assertIsNotNone(gazebo_interface_bridge)
        self.assertIsNotNone(kinematics)
        self.assertIsNotNone(simple_base_sim)

    def test_assets_exist(self):
        package_root = Path(__file__).resolve().parents[1]
        self.assertTrue((package_root / "launch" / "sim_bringup.launch.py").is_file())
        self.assertTrue((package_root / "config" / "controller_manager.yaml").is_file())
        self.assertTrue((package_root / "config" / "diff_drive_controller.yaml").is_file())
        self.assertTrue((package_root / "config" / "twist_mux_locks.yaml").is_file())
        self.assertTrue((package_root / "config" / "twist_mux_topics.yaml").is_file())
        self.assertTrue((package_root / "config" / "wheel_velocity_controller.yaml").is_file())
        self.assertTrue((package_root / "urdf" / "xbot.ros2_control.xacro").is_file())
        self.assertTrue((package_root / "urdf" / "xbot.urdf.xacro").is_file())
        self.assertTrue((package_root / "worlds" / "empty.sdf").is_file())
        self.assertTrue((package_root / "meshes" / "base_link.dae").is_file())
        self.assertTrue((package_root / "meshes" / "wheel.dae").is_file())
        self.assertTrue((package_root / "rviz" / "sim.rviz").is_file())
        self.assertTrue((package_root / "gui" / "ground.gui.config").is_file())
        self.assertTrue((package_root / "gui" / "museum.gui.config").is_file())
        self.assertTrue((package_root / "worlds" / "museum.sdf").is_file())
        self.assertTrue((package_root / "worlds" / "ground_test.sdf").is_file())
        self.assertTrue((package_root / "models" / "ISCAS_Museum" / "model.sdf").is_file())
        self.assertTrue((package_root / "models" / "ISCAS_groundplane" / "model.sdf").is_file())
        self.assertTrue((package_root / "models" / "ISCAS_groundplane" / "meshes" / "ground_plane.obj").is_file())
        self.assertTrue((package_root / "models" / "ISCAS_groundplane" / "meshes" / "ground_plane.mtl").is_file())
        self.assertTrue((package_root / "models" / "ISCAS_groundplane" / "meshes" / "ground_plane.dae").is_file())
        self.assertTrue((package_root / "models" / "ISCAS_groundplane" / "materials" / "textures" / "flat_heightmap.pgm").is_file())
