import threading
import time
import unittest

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

from robot_sim_demo_ros2.fake_laser import FakeLaserNode
from robot_sim_demo_ros2.simple_base_sim import SimpleBaseSimNode


class CommandPublisher(Node):
    def __init__(self) -> None:
        super().__init__("command_publisher_test")
        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.timer = self.create_timer(0.05, self.publish_command)

    def publish_command(self) -> None:
        twist = Twist()
        twist.linear.x = 0.3
        twist.angular.z = 0.2
        self.publisher.publish(twist)


class OdomCollector(Node):
    def __init__(self) -> None:
        super().__init__("odom_collector_test")
        self.messages = []
        self.subscription = self.create_subscription(Odometry, "/odom", self.callback, 10)

    def callback(self, message: Odometry) -> None:
        self.messages.append(message)


class ScanCollector(Node):
    def __init__(self) -> None:
        super().__init__("scan_collector_test")
        self.messages = []
        self.subscription = self.create_subscription(LaserScan, "/scan", self.callback, 10)

    def callback(self, message: LaserScan) -> None:
        self.messages.append(message)


class RobotSimIntegrationTest(unittest.TestCase):
    def test_sim_base_publishes_odom_and_scan(self):
        rclpy.init()
        sim_node = SimpleBaseSimNode()
        laser_node = FakeLaserNode()
        command_node = CommandPublisher()
        odom_collector = OdomCollector()
        scan_collector = ScanCollector()

        executor = MultiThreadedExecutor()
        for node in [sim_node, laser_node, command_node, odom_collector, scan_collector]:
            executor.add_node(node)

        spin_thread = threading.Thread(target=executor.spin, daemon=True)
        spin_thread.start()
        deadline = time.time() + 3.0
        try:
            while time.time() < deadline:
                latest_odom = odom_collector.messages[-1] if odom_collector.messages else None
                latest_scan = scan_collector.messages[-1] if scan_collector.messages else None
                if (
                    latest_odom is not None
                    and latest_scan is not None
                    and latest_odom.pose.pose.position.x > 0.02
                    and len(latest_scan.ranges) > 10
                ):
                    break
                time.sleep(0.05)

            self.assertTrue(odom_collector.messages, "Expected /odom messages from simple_base_sim")
            self.assertTrue(scan_collector.messages, "Expected /scan messages from fake_laser")
            self.assertGreater(odom_collector.messages[-1].pose.pose.position.x, 0.02)
            self.assertGreater(len(scan_collector.messages[-1].ranges), 10)
        finally:
            executor.shutdown()
            spin_thread.join(timeout=1.0)
            for node in [sim_node, laser_node, command_node, odom_collector, scan_collector]:
                node.destroy_node()
            rclpy.shutdown()
