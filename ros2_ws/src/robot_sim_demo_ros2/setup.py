from glob import glob
from pathlib import Path

from setuptools import setup

package_name = "robot_sim_demo_ros2"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (
            "share/" + package_name + "/launch",
            [
                "launch/sim_bringup.launch.py",
            ],
        ),
        (
            "share/" + package_name + "/urdf",
            [
                "urdf/materials.xacro",
                "urdf/xbot.ros2_control.xacro",
                "urdf/xbot.urdf.xacro",
            ],
        ),
        (
            "share/" + package_name + "/config",
            [
                "config/controller_manager.yaml",
                "config/diff_drive_controller.yaml",
                "config/twist_mux_locks.yaml",
                "config/twist_mux_topics.yaml",
                "config/wheel_velocity_controller.yaml",
            ],
        ),
        (
            "share/" + package_name + "/rviz",
            [
                "rviz/sim.rviz",
            ],
        ),
        (
            "share/" + package_name + "/gui",
            glob("gui/*.config"),
        ),
        (
            "share/" + package_name + "/worlds",
            glob("worlds/*.sdf"),
        ),
        (
            "share/" + package_name + "/meshes",
            glob("meshes/*"),
        ),
        *[
            (
                "share/" + package_name + "/" + str(Path(path).parent),
                [path],
            )
            for path in glob("models/**/*", recursive=True)
            if Path(path).is_file()
        ],
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ROS Academy",
    maintainer_email="anchuanxu@todo.todo",
    description="Minimal ROS 2 simulation base split from the ROS 1 robot_sim_demo package.",
    license="BSD",
    entry_points={
        "console_scripts": [
            "simple_base_sim = robot_sim_demo_ros2.simple_base_sim:main",
            "fake_laser = robot_sim_demo_ros2.fake_laser:main",
            "gazebo_interface_bridge = robot_sim_demo_ros2.gazebo_interface_bridge:main",
            "ros2_control_runner = robot_sim_demo_ros2.ros2_control_runner:main",
        ],
    },
)
