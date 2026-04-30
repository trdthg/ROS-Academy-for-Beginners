import math
import time

from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid, Odometry
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node


def count_known_cells(cells: list[int]) -> int:
    return sum(1 for value in cells if value >= 0)


def planar_distance(start: tuple[float, float], end: tuple[float, float]) -> float:
    return math.hypot(end[0] - start[0], end[1] - start[1])


def command_for_elapsed(elapsed_sec: float) -> tuple[float, float]:
    cycle_time = elapsed_sec % 8.0
    if cycle_time < 2.0:
        return (0.0, 0.6)
    if cycle_time < 4.5:
        return (0.25, 0.0)
    if cycle_time < 6.5:
        return (0.0, -0.6)
    return (0.25, 0.0)


class SlamMapCheckNode(Node):
    def __init__(self) -> None:
        super().__init__("slam_map_runner")
        self.command_publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.odom_subscription = self.create_subscription(Odometry, "/odom", self.handle_odom, 10)
        self.map_subscription = self.create_subscription(OccupancyGrid, "/map", self.handle_map, 10)

        self.start_pose = None
        self.latest_pose = None
        self.first_map_known_cells = None
        self.max_known_cells = 0
        self.map_updates = 0
        self.last_map_stamp = None

    def handle_odom(self, message: Odometry) -> None:
        pose = (
            float(message.pose.pose.position.x),
            float(message.pose.pose.position.y),
        )
        if self.start_pose is None:
            self.start_pose = pose
        self.latest_pose = pose

    def handle_map(self, message: OccupancyGrid) -> None:
        stamp = (message.header.stamp.sec, message.header.stamp.nanosec)
        if stamp != self.last_map_stamp:
            self.map_updates += 1
            self.last_map_stamp = stamp

        known_cells = count_known_cells(list(message.data))
        if self.first_map_known_cells is None:
            self.first_map_known_cells = known_cells
        self.max_known_cells = max(self.max_known_cells, known_cells)

    def ready(self) -> bool:
        return self.latest_pose is not None and self.first_map_known_cells is not None

    def odom_distance(self) -> float:
        if self.start_pose is None or self.latest_pose is None:
            return 0.0
        return planar_distance(self.start_pose, self.latest_pose)

    def publish_command(self, linear_x: float, angular_z: float) -> None:
        twist = Twist()
        twist.linear.x = linear_x
        twist.angular.z = angular_z
        self.command_publisher.publish(twist)

    def publish_stop(self) -> None:
        self.publish_command(0.0, 0.0)

    def succeeded(self) -> bool:
        if self.first_map_known_cells is None:
            return False
        return (
            self.map_updates >= 2
            and self.odom_distance() > 0.2
            and self.max_known_cells - self.first_map_known_cells > 100
        )


def main() -> None:
    rclpy.init()
    node = SlamMapCheckNode()
    executor = SingleThreadedExecutor()
    executor.add_node(node)

    overall_start = time.time()
    motion_start = None
    try:
        while time.time() - overall_start < 25.0:
            executor.spin_once(timeout_sec=0.1)
            if not node.ready():
                continue

            if motion_start is None:
                motion_start = time.time()

            linear_x, angular_z = command_for_elapsed(time.time() - motion_start)
            node.publish_command(linear_x, angular_z)

            if node.succeeded():
                node.publish_stop()
                print("slam-map-updated")
                return

        node.publish_stop()
        raise RuntimeError("slam_toolbox did not publish a growing map after driving the robot")
    finally:
        executor.remove_node(node)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
