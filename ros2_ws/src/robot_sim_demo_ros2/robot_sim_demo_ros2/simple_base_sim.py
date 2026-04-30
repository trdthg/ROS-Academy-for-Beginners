from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.duration import Duration
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from tf2_ros import TransformBroadcaster

from .kinematics import integrate_diff_drive, wheel_angular_velocities


def yaw_to_quaternion(yaw: float) -> tuple[float, float, float, float]:
    half_yaw = yaw * 0.5
    return (0.0, 0.0, math.sin(half_yaw), math.cos(half_yaw))


class SimpleBaseSimNode(Node):
    def __init__(self) -> None:
        super().__init__("simple_base_sim")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("joint_states_topic", "/joint_states")
        self.declare_parameter("odom_frame", "odom")
        self.declare_parameter("base_frame", "base_footprint")
        self.declare_parameter("wheel_radius", 0.095)
        self.declare_parameter("wheel_separation", 0.46)
        self.declare_parameter("update_rate_hz", 30.0)
        self.declare_parameter("cmd_vel_timeout_sec", 0.5)

        self.cmd_vel_topic = str(self.get_parameter("cmd_vel_topic").value)
        self.odom_topic = str(self.get_parameter("odom_topic").value)
        self.joint_states_topic = str(self.get_parameter("joint_states_topic").value)
        self.odom_frame = str(self.get_parameter("odom_frame").value)
        self.base_frame = str(self.get_parameter("base_frame").value)
        self.wheel_radius = float(self.get_parameter("wheel_radius").value)
        self.wheel_separation = float(self.get_parameter("wheel_separation").value)
        self.update_rate_hz = max(float(self.get_parameter("update_rate_hz").value), 1.0)
        self.cmd_vel_timeout = Duration(seconds=float(self.get_parameter("cmd_vel_timeout_sec").value))

        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.linear_velocity = 0.0
        self.angular_velocity = 0.0
        self.left_wheel_angle = 0.0
        self.right_wheel_angle = 0.0
        self.last_command_time = self.get_clock().now()
        self.last_update_time = self.get_clock().now()

        self.odom_publisher = self.create_publisher(Odometry, self.odom_topic, 10)
        self.joint_state_publisher = self.create_publisher(JointState, self.joint_states_topic, 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.cmd_subscription = self.create_subscription(Twist, self.cmd_vel_topic, self.handle_cmd_vel, 10)
        self.timer = self.create_timer(1.0 / self.update_rate_hz, self.update)

    def handle_cmd_vel(self, message: Twist) -> None:
        self.linear_velocity = float(message.linear.x)
        self.angular_velocity = float(message.angular.z)
        self.last_command_time = self.get_clock().now()

    def update(self) -> None:
        now = self.get_clock().now()
        dt = (now - self.last_update_time).nanoseconds / 1e9
        self.last_update_time = now
        if dt <= 0.0:
            return

        if now - self.last_command_time > self.cmd_vel_timeout:
            self.linear_velocity = 0.0
            self.angular_velocity = 0.0

        self.x, self.y, self.yaw = integrate_diff_drive(
            x=self.x,
            y=self.y,
            yaw=self.yaw,
            linear_velocity=self.linear_velocity,
            angular_velocity=self.angular_velocity,
            dt=dt,
        )
        left_wheel_velocity, right_wheel_velocity = wheel_angular_velocities(
            linear_velocity=self.linear_velocity,
            angular_velocity=self.angular_velocity,
            wheel_separation=self.wheel_separation,
            wheel_radius=self.wheel_radius,
        )
        self.left_wheel_angle += left_wheel_velocity * dt
        self.right_wheel_angle += right_wheel_velocity * dt

        self.publish_odometry(now)
        self.publish_joint_states(now, left_wheel_velocity, right_wheel_velocity)

    def publish_odometry(self, stamp) -> None:
        odom = Odometry()
        odom.header.stamp = stamp.to_msg()
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        quat = yaw_to_quaternion(self.yaw)
        odom.pose.pose.orientation.z = quat[2]
        odom.pose.pose.orientation.w = quat[3]
        odom.twist.twist.linear.x = self.linear_velocity
        odom.twist.twist.angular.z = self.angular_velocity
        self.odom_publisher.publish(odom)

        transform = TransformStamped()
        transform.header.stamp = odom.header.stamp
        transform.header.frame_id = self.odom_frame
        transform.child_frame_id = self.base_frame
        transform.transform.translation.x = self.x
        transform.transform.translation.y = self.y
        transform.transform.rotation.z = quat[2]
        transform.transform.rotation.w = quat[3]
        self.tf_broadcaster.sendTransform(transform)

    def publish_joint_states(self, stamp, left_wheel_velocity: float, right_wheel_velocity: float) -> None:
        joint_state = JointState()
        joint_state.header.stamp = stamp.to_msg()
        joint_state.name = [
            "left_wheel_hinge",
            "right_wheel_hinge",
            "base_to_yaw_platform",
            "yaw_to_pitch_platform",
        ]
        joint_state.position = [
            self.left_wheel_angle,
            self.right_wheel_angle,
            0.0,
            0.0,
        ]
        joint_state.velocity = [
            left_wheel_velocity,
            right_wheel_velocity,
            0.0,
            0.0,
        ]
        self.joint_state_publisher.publish(joint_state)


def main() -> None:
    rclpy.init()
    node = SimpleBaseSimNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
