import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    slam_pkg_share = get_package_share_directory("slam_sim_demo_ros2")
    slam_toolbox_share = get_package_share_directory("slam_toolbox")
    robot_sim_share = get_package_share_directory("robot_sim_demo_ros2")

    default_params = os.path.join(slam_pkg_share, "params", "slam_toolbox_params.yaml")
    default_rviz = os.path.join(slam_pkg_share, "rviz", "slam.rviz")
    default_world = os.path.join(robot_sim_share, "worlds", "museum.sdf")
    robot_sim_launch = os.path.join(robot_sim_share, "launch", "sim_bringup.launch.py")
    slam_toolbox_launch = os.path.join(slam_toolbox_share, "launch", "online_async_launch.py")

    slam_params_file = LaunchConfiguration("slam_params_file")
    rviz_config = LaunchConfiguration("rviz_config")
    use_rviz = LaunchConfiguration("use_rviz")
    use_gazebo = LaunchConfiguration("use_gazebo")
    gz_headless = LaunchConfiguration("gz_headless")
    world = LaunchConfiguration("world")
    use_sim_time = LaunchConfiguration("use_sim_time")
    scan_topic = LaunchConfiguration("scan_topic")
    spawn_x = LaunchConfiguration("spawn_x")
    spawn_y = LaunchConfiguration("spawn_y")
    spawn_z = LaunchConfiguration("spawn_z")
    spawn_yaw = LaunchConfiguration("spawn_yaw")

    return LaunchDescription(
        [
            DeclareLaunchArgument("slam_params_file", default_value=default_params),
            DeclareLaunchArgument("rviz_config", default_value=default_rviz),
            DeclareLaunchArgument("world", default_value=default_world),
            DeclareLaunchArgument("scan_topic", default_value="/scan"),
            DeclareLaunchArgument("spawn_x", default_value="5.0"),
            DeclareLaunchArgument("spawn_y", default_value="0.0"),
            DeclareLaunchArgument("spawn_z", default_value="0.25"),
            DeclareLaunchArgument("spawn_yaw", default_value="-2.0"),
            DeclareLaunchArgument("use_rviz", default_value="true"),
            DeclareLaunchArgument("use_gazebo", default_value="true"),
            DeclareLaunchArgument("gz_headless", default_value="false"),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            GroupAction(
                scoped=True,
                actions=[
                    IncludeLaunchDescription(
                        PythonLaunchDescriptionSource(robot_sim_launch),
                        launch_arguments={
                            "use_rviz": "false",
                            "use_gazebo": use_gazebo,
                            "gz_headless": gz_headless,
                            "world": world,
                            "spawn_x": spawn_x,
                            "spawn_y": spawn_y,
                            "spawn_z": spawn_z,
                            "spawn_yaw": spawn_yaw,
                            "enable_fake_laser": "false",
                            "enable_depth_camera": "true",
                        }.items(),
                    )
                ],
            ),
            Node(
                package="ros_gz_bridge",
                executable="parameter_bridge",
                arguments=[
                    "/rgbd_camera/image@sensor_msgs/msg/Image@gz.msgs.Image",
                    "/rgbd_camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo",
                    "/rgbd_camera/depth_image@sensor_msgs/msg/Image@gz.msgs.Image",
                    "/rgbd_camera/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked",
                ],
                output="screen",
            ),
            Node(
                package="depthimage_to_laserscan",
                executable="depthimage_to_laserscan_node",
                name="depthimage_to_laserscan",
                parameters=[
                    {
                        "use_sim_time": use_sim_time,
                        "scan_time": 1.0 / 15.0,
                        "range_min": 0.2,
                        "range_max": 8.0,
                        "scan_height": 20,
                        "output_frame": "camera_link_optical",
                    }
                ],
                remappings=[
                    ("depth", "/rgbd_camera/depth_image"),
                    ("depth_camera_info", "/rgbd_camera/camera_info"),
                    ("scan", scan_topic),
                ],
                output="screen",
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(slam_toolbox_launch),
                launch_arguments={
                    "slam_params_file": slam_params_file,
                    "use_sim_time": use_sim_time,
                }.items(),
            ),
            Node(
                package="rviz2",
                executable="rviz2",
                arguments=["-d", rviz_config],
                condition=IfCondition(use_rviz),
                output="screen",
            ),
        ]
    )
