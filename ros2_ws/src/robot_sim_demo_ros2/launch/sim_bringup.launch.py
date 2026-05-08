import os

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, EnvironmentVariable, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    package_share = get_package_share_directory("robot_sim_demo_ros2")
    package_share_parent = os.path.dirname(package_share)
    default_model = os.path.join(package_share, "urdf", "xbot.urdf.xacro")
    default_rviz = os.path.join(package_share, "rviz", "sim.rviz")
    default_world = os.path.join(package_share, "worlds", "museum.sdf")
    default_gui_config = os.path.join(package_share, "gui", "museum.gui.config")
    model_resource_path = os.path.join(package_share, "models")
    controller_manager_config = os.path.join(package_share, "config", "controller_manager.yaml")
    diff_drive_controller_config = os.path.join(package_share, "config", "diff_drive_controller.yaml")
    wheel_velocity_controller_config = os.path.join(package_share, "config", "wheel_velocity_controller.yaml")
    twist_mux_locks = os.path.join(package_share, "config", "twist_mux_locks.yaml")
    twist_mux_config = os.path.join(package_share, "config", "twist_mux_topics.yaml")
    gz_launch = os.path.join(get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py")
    gz_ros2_control_lib = os.path.join(get_package_prefix("gz_ros2_control"), "lib")
    robot_description = {
        "robot_description": Command(
            [
                "xacro ",
                LaunchConfiguration("model"),
                " use_gazebo:=",
                LaunchConfiguration("use_gazebo"),
                " enable_depth_camera:=",
                LaunchConfiguration("enable_depth_camera"),
                " controller_manager_config:=",
                controller_manager_config,
                " diff_drive_controller_config:=",
                diff_drive_controller_config,
            ]
        )
    }
    use_sim_time = {"use_sim_time": LaunchConfiguration("use_gazebo")}

    return LaunchDescription(
        [
            DeclareLaunchArgument("model", default_value=default_model),
            DeclareLaunchArgument("rviz_config", default_value=default_rviz),
            DeclareLaunchArgument("world", default_value=default_world),
            DeclareLaunchArgument("gui_config", default_value=default_gui_config),
            DeclareLaunchArgument("spawn_x", default_value="0.0"),
            DeclareLaunchArgument("spawn_y", default_value="0.0"),
            DeclareLaunchArgument("spawn_z", default_value="0.25"),
            DeclareLaunchArgument("spawn_yaw", default_value="0.0"),
            DeclareLaunchArgument("fake_laser_map_yaml", default_value=""),
            DeclareLaunchArgument("enable_fake_laser", default_value="true"),
            DeclareLaunchArgument("enable_depth_camera", default_value="false"),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            DeclareLaunchArgument("use_ros2_control", default_value="true"),
            DeclareLaunchArgument("use_gazebo", default_value="false"),
            DeclareLaunchArgument("gz_headless", default_value="true"),
            SetEnvironmentVariable(
                name="GZ_SIM_SYSTEM_PLUGIN_PATH",
                value=[gz_ros2_control_lib, os.pathsep, EnvironmentVariable("GZ_SIM_SYSTEM_PLUGIN_PATH", default_value="")],
            ),
            SetEnvironmentVariable(
                name="IGN_GAZEBO_SYSTEM_PLUGIN_PATH",
                value=[gz_ros2_control_lib, os.pathsep, EnvironmentVariable("IGN_GAZEBO_SYSTEM_PLUGIN_PATH", default_value="")],
            ),
            SetEnvironmentVariable(
                name="GZ_SIM_RESOURCE_PATH",
                value=[
                    model_resource_path,
                    os.pathsep,
                    package_share_parent,
                    os.pathsep,
                    package_share,
                    os.pathsep,
                    EnvironmentVariable("GZ_SIM_RESOURCE_PATH", default_value=""),
                ],
            ),
            SetEnvironmentVariable(
                name="IGN_GAZEBO_RESOURCE_PATH",
                value=[
                    model_resource_path,
                    os.pathsep,
                    package_share_parent,
                    os.pathsep,
                    package_share,
                    os.pathsep,
                    EnvironmentVariable("IGN_GAZEBO_RESOURCE_PATH", default_value=""),
                ],
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(gz_launch),
                launch_arguments={
                    "gz_args": PythonExpression(["'-r -s ", LaunchConfiguration("world"), "'"]),
                    "on_exit_shutdown": "true",
                }.items(),
                condition=IfCondition(
                    PythonExpression(
                        [
                            "'",
                            LaunchConfiguration("use_gazebo"),
                            "' == 'true' and '",
                            LaunchConfiguration("gz_headless"),
                            "' == 'true'",
                        ]
                    )
                ),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(gz_launch),
                launch_arguments={
                    "gz_args": PythonExpression(
                        [
                            "'-r --gui-config ",
                            LaunchConfiguration("gui_config"),
                            " ",
                            LaunchConfiguration("world"),
                            "'",
                        ]
                    ),
                    "on_exit_shutdown": "true",
                }.items(),
                condition=IfCondition(
                    PythonExpression(
                        [
                            "'",
                            LaunchConfiguration("use_gazebo"),
                            "' == 'true' and '",
                            LaunchConfiguration("gz_headless"),
                            "' != 'true'",
                        ]
                    )
                ),
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                parameters=[robot_description, use_sim_time],
                output="screen",
            ),
            Node(
                package="robot_sim_demo_ros2",
                executable="simple_base_sim",
                name="simple_base_sim",
                condition=IfCondition(
                    PythonExpression(
                        [
                            "'",
                            LaunchConfiguration("use_ros2_control"),
                            "' == 'false' and '",
                            LaunchConfiguration("use_gazebo"),
                            "' != 'true'",
                        ]
                    )
                ),
                output="screen",
            ),
            Node(
                package="controller_manager",
                executable="ros2_control_node",
                name="controller_manager",
                parameters=[robot_description, controller_manager_config],
                remappings=[
                    ("diff_drive_base_controller/cmd_vel_unstamped", "cmd_vel"),
                    ("diff_drive_base_controller/odom", "odom"),
                ],
                condition=IfCondition(
                    PythonExpression(
                        [
                            "'",
                            LaunchConfiguration("use_ros2_control"),
                            "' == 'true' and '",
                            LaunchConfiguration("use_gazebo"),
                            "' != 'true'",
                        ]
                    )
                ),
                output="screen",
            ),
            Node(
                package="robot_sim_demo_ros2",
                executable="ros2_control_runner",
                name="ros2_control_runner",
                parameters=[
                    {
                        "controller_name": "diff_drive_base_controller",
                        "controller_type": "diff_drive_controller/DiffDriveController",
                        "controller_config": diff_drive_controller_config,
                    }
                ],
                condition=IfCondition(
                    PythonExpression(
                        [
                            "'",
                            LaunchConfiguration("use_ros2_control"),
                            "' == 'true' and '",
                            LaunchConfiguration("use_gazebo"),
                            "' != 'true'",
                        ]
                    )
                ),
                output="screen",
            ),
            Node(
                package="robot_sim_demo_ros2",
                executable="ros2_control_runner",
                name="ros2_control_runner",
                parameters=[
                    {
                        "controller_name": "wheel_velocity_controller",
                        "controller_type": "velocity_controllers/JointGroupVelocityController",
                        "controller_config": wheel_velocity_controller_config,
                        "deactivate_controllers": ["diff_drive_base_controller"],
                    }
                ],
                condition=IfCondition(
                    PythonExpression(
                        [
                            "'",
                            LaunchConfiguration("use_ros2_control"),
                            "' == 'true' and '",
                            LaunchConfiguration("use_gazebo"),
                            "' == 'true'",
                        ]
                    )
                ),
                output="screen",
            ),
            Node(
                package="robot_sim_demo_ros2",
                executable="gazebo_interface_bridge",
                name="gazebo_interface_bridge",
                parameters=[
                    use_sim_time,
                    {
                        "initial_x": LaunchConfiguration("spawn_x"),
                        "initial_y": LaunchConfiguration("spawn_y"),
                        "initial_yaw": LaunchConfiguration("spawn_yaw"),
                    },
                ],
                condition=IfCondition(LaunchConfiguration("use_gazebo")),
                output="screen",
            ),
            TimerAction(
                period=2.0,
                actions=[
                    Node(
                        package="ros_gz_sim",
                        executable="create",
                        arguments=[
                            "-world",
                            "default",
                            "-topic",
                            "robot_description",
                            "-name",
                            "xbot",
                            "-x",
                            LaunchConfiguration("spawn_x"),
                            "-y",
                            LaunchConfiguration("spawn_y"),
                            "-z",
                            LaunchConfiguration("spawn_z"),
                            "-Y",
                            LaunchConfiguration("spawn_yaw"),
                        ],
                        output="screen",
                    )
                ],
                condition=IfCondition(LaunchConfiguration("use_gazebo")),
            ),
            Node(
                package="twist_mux",
                executable="twist_mux",
                name="twist_mux",
                parameters=[twist_mux_locks, twist_mux_config],
                remappings=[("/cmd_vel_out", "cmd_vel")],
                output="screen",
            ),
            Node(
                package="robot_sim_demo_ros2",
                executable="fake_laser",
                parameters=[use_sim_time, {"map_yaml": LaunchConfiguration("fake_laser_map_yaml")}],
                name="fake_laser",
                condition=IfCondition(LaunchConfiguration("enable_fake_laser")),
                output="screen",
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                arguments=["-d", LaunchConfiguration("rviz_config")],
                parameters=[use_sim_time],
                condition=IfCondition(LaunchConfiguration("use_rviz")),
                output="screen",
            ),
        ]
    )
