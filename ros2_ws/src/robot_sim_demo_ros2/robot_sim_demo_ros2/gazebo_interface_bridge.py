import math

import rclpy
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray
from tf2_ros import TransformBroadcaster

from .kinematics import integrate_diff_drive, wheel_angular_velocities


def yaw_to_quaternion(yaw: float) -> tuple[float, float, float, float]:
    half_yaw = yaw * 0.5
    return (0.0, 0.0, math.sin(half_yaw), math.cos(half_yaw))


class GazeboInterfaceBridge(Node):
    def __init__(self) -> None:
        super().__init__("gazebo_interface_bridge")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("wheel_command_topic", "/wheel_velocity_controller/commands")
        self.declare_parameter("joint_states_topic", "/joint_states")
        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("odom_frame", "odom")
        self.declare_parameter("base_frame", "base_footprint")
        self.declare_parameter("left_wheel_joint", "left_wheel_hinge")
        self.declare_parameter("right_wheel_joint", "right_wheel_hinge")
        self.declare_parameter("wheel_radius", 0.095)
        self.declare_parameter("wheel_separation", 0.46)
        self.declare_parameter("cmd_vel_timeout_sec", 0.5)
        self.declare_parameter("initial_x", 0.0)
        self.declare_parameter("initial_y", 0.0)
        self.declare_parameter("initial_yaw", 0.0)

        self.cmd_vel_topic = str(self.get_parameter("cmd_vel_topic").value)
        self.wheel_command_topic = str(self.get_parameter("wheel_command_topic").value)
        self.joint_states_topic = str(self.get_parameter("joint_states_topic").value)
        self.odom_topic = str(self.get_parameter("odom_topic").value)
        self.odom_frame = str(self.get_parameter("odom_frame").value)
        self.base_frame = str(self.get_parameter("base_frame").value)
        self.left_wheel_joint = str(self.get_parameter("left_wheel_joint").value)
        self.right_wheel_joint = str(self.get_parameter("right_wheel_joint").value)
        self.wheel_radius = float(self.get_parameter("wheel_radius").value)
        self.wheel_separation = float(self.get_parameter("wheel_separation").value)
        self.cmd_vel_timeout = Duration(seconds=float(self.get_parameter("cmd_vel_timeout_sec").value))

        self.command_linear_velocity = 0.0
        self.command_angular_velocity = 0.0
        self.last_command_time = self.get_clock().now()

        self.left_wheel_index: int | None = None
        self.right_wheel_index: int | None = None
        self.last_left_wheel_position: float | None = None
        self.last_right_wheel_position: float | None = None
        self.last_joint_state_time = None

        self.x = float(self.get_parameter("initial_x").value)
        self.y = float(self.get_parameter("initial_y").value)
        self.yaw = float(self.get_parameter("initial_yaw").value)

        self.cmd_publisher = self.create_publisher(Float64MultiArray, self.wheel_command_topic, 10)
        self.odom_publisher = self.create_publisher(Odometry, self.odom_topic, 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.create_subscription(Twist, self.cmd_vel_topic, self.forward_cmd_vel, 10)
        self.create_subscription(
            JointState,
            self.joint_states_topic,
            self.handle_joint_states,
            10,
        )

    def forward_cmd_vel(self, message: Twist) -> None:
        self.command_linear_velocity = float(message.linear.x)
        self.command_angular_velocity = float(message.angular.z)
        self.last_command_time = self.get_clock().now()
        self.publish_wheel_command()

    def publish_wheel_command(self) -> None:
        linear_velocity = self.command_linear_velocity
        angular_velocity = self.command_angular_velocity
        if self.get_clock().now() - self.last_command_time > self.cmd_vel_timeout:
            linear_velocity = 0.0
            angular_velocity = 0.0

        left_velocity, right_velocity = wheel_angular_velocities(
            linear_velocity=linear_velocity,
            angular_velocity=angular_velocity,
            wheel_separation=self.wheel_separation,
            wheel_radius=self.wheel_radius,
        )
        message = Float64MultiArray()
        message.data = [left_velocity, right_velocity]
        self.cmd_publisher.publish(message)

    def handle_joint_states(self, message: JointState) -> None:
        if self.left_wheel_index is None or self.right_wheel_index is None:
            self.resolve_joint_indexes(message.name)

        if self.left_wheel_index is None or self.right_wheel_index is None:
            return

        if max(self.left_wheel_index, self.right_wheel_index) >= len(message.position):
            return

        stamp = Time.from_msg(message.header.stamp)
        left_position = float(message.position[self.left_wheel_index])
        right_position = float(message.position[self.right_wheel_index])

        if self.last_joint_state_time is None:
            self.last_joint_state_time = stamp
            self.last_left_wheel_position = left_position
            self.last_right_wheel_position = right_position
            self.publish_wheel_command()
            return

        dt = (stamp - self.last_joint_state_time).nanoseconds / 1e9
        if dt <= 0.0:
            return

        delta_left = left_position - self.last_left_wheel_position
        delta_right = right_position - self.last_right_wheel_position
        linear_velocity = self.wheel_radius * (delta_left + delta_right) / (2.0 * dt)
        angular_velocity = self.wheel_radius * (delta_right - delta_left) / (self.wheel_separation * dt)
        self.x, self.y, self.yaw = integrate_diff_drive(
            x=self.x,
            y=self.y,
            yaw=self.yaw,
            linear_velocity=linear_velocity,
            angular_velocity=angular_velocity,
            dt=dt,
        )

        self.last_joint_state_time = stamp
        self.last_left_wheel_position = left_position
        self.last_right_wheel_position = right_position
        self.publish_odometry(stamp, linear_velocity, angular_velocity)
        self.publish_wheel_command()

    def resolve_joint_indexes(self, joint_names: list[str]) -> None:
        name_to_index = {name: index for index, name in enumerate(joint_names)}
        self.left_wheel_index = name_to_index.get(self.left_wheel_joint)
        self.right_wheel_index = name_to_index.get(self.right_wheel_joint)

    def publish_odometry(self, stamp, linear_velocity: float, angular_velocity: float) -> None:
        quaternion = yaw_to_quaternion(self.yaw)
        odom = Odometry()
        odom.header.stamp = stamp.to_msg()
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.z = quaternion[2]
        odom.pose.pose.orientation.w = quaternion[3]
        odom.twist.twist.linear.x = linear_velocity
        odom.twist.twist.angular.z = angular_velocity
        self.odom_publisher.publish(odom)

        transform = TransformStamped()
        transform.header.stamp = odom.header.stamp
        transform.header.frame_id = self.odom_frame
        transform.child_frame_id = self.base_frame
        transform.transform.translation.x = self.x
        transform.transform.translation.y = self.y
        transform.transform.rotation.z = quaternion[2]
        transform.transform.rotation.w = quaternion[3]
        self.tf_broadcaster.sendTransform(transform)


def main() -> None:
    rclpy.init()
    node = GazeboInterfaceBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
