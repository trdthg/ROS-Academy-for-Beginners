import math
import time

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from nav2_simple_commander.robot_navigator import BasicNavigator
from nav_msgs.msg import Odometry
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter


def yaw_to_quaternion(yaw: float) -> tuple[float, float, float, float]:
    half_yaw = yaw * 0.5
    return (0.0, 0.0, math.sin(half_yaw), math.cos(half_yaw))


def planar_distance(x0: float, y0: float, x1: float, y1: float) -> float:
    return math.hypot(x1 - x0, y1 - y0)


def build_pose(frame_id: str, x: float, y: float, yaw: float) -> PoseStamped:
    pose = PoseStamped()
    pose.header.frame_id = frame_id
    pose.pose.position.x = x
    pose.pose.position.y = y
    quat = yaw_to_quaternion(yaw)
    pose.pose.orientation.z = quat[2]
    pose.pose.orientation.w = quat[3]
    return pose


class OdomWatcher(Node):
    def __init__(self) -> None:
        super().__init__("nav_goal_odom_watcher")
        self.latest = None
        self.subscription = self.create_subscription(Odometry, "/odom", self.callback, 10)

    def callback(self, message: Odometry) -> None:
        self.latest = message


def stamp_pose(node: Node, pose: PoseStamped) -> PoseStamped:
    pose.header.stamp = node.get_clock().now().to_msg()
    return pose


def main() -> None:
    rclpy.init()
    navigator = BasicNavigator()
    odom_watcher = OdomWatcher()
    use_sim_time = bool(odom_watcher.get_parameter("use_sim_time").value)
    navigator.set_parameters([Parameter("use_sim_time", value=use_sim_time)])
    navigate_action = ActionClient(navigator, NavigateToPose, "navigate_to_pose")
    executor = SingleThreadedExecutor()
    executor.add_node(navigator)
    executor.add_node(odom_watcher)

    try:
        start_pose = stamp_pose(navigator, build_pose("map", 5.0, 0.0, -2.0))
        goal_pose = stamp_pose(odom_watcher, build_pose("map", 3.0, -1.0, -2.0))
        navigator.setInitialPose(start_pose)
        navigator.waitUntilNav2Active()
        if not navigate_action.wait_for_server(timeout_sec=10.0):
            raise RuntimeError("NavigateToPose action server did not become ready")

        goal = NavigateToPose.Goal()
        goal.pose = goal_pose
        goal_future = navigate_action.send_goal_async(goal, feedback_callback=None)
        rclpy.spin_until_future_complete(navigator, goal_future, timeout_sec=5.0)
        goal_handle = goal_future.result()
        if goal_handle is None or not goal_handle.accepted:
            raise RuntimeError("NavigateToPose goal was rejected")

        start_time = time.time()
        start_odom_position = None
        while time.time() - start_time < 8.0:
            executor.spin_once(timeout_sec=0.1)
            if odom_watcher.latest is None:
                continue
            latest_x = float(odom_watcher.latest.pose.pose.position.x)
            latest_y = float(odom_watcher.latest.pose.pose.position.y)
            if start_odom_position is None:
                start_odom_position = (latest_x, latest_y)
                continue
            if planar_distance(start_odom_position[0], start_odom_position[1], latest_x, latest_y) > 0.05:
                cancel_future = goal_handle.cancel_goal_async()
                rclpy.spin_until_future_complete(navigator, cancel_future, timeout_sec=3.0)
                print("navigation-motion-detected")
                return

        cancel_future = goal_handle.cancel_goal_async()
        rclpy.spin_until_future_complete(navigator, cancel_future, timeout_sec=3.0)
        raise RuntimeError("Robot odometry did not change after sending NavigateToPose goal")
    finally:
        executor.remove_node(navigator)
        executor.remove_node(odom_watcher)
        odom_watcher.destroy_node()
        navigator.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
