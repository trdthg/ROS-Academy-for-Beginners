import math
from pathlib import Path

import yaml

from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

from .fake_world import cast_ray, scene_segments


def quaternion_to_yaw(z: float, w: float) -> float:
    return math.atan2(2.0 * w * z, 1.0 - 2.0 * z * z)


def _read_non_comment_tokens(handle, count: int) -> list[bytes]:
    tokens: list[bytes] = []
    while len(tokens) < count:
        line = handle.readline()
        if not line:
            raise ValueError("Unexpected end of file while reading PGM header")
        stripped = line.strip()
        if not stripped or stripped.startswith(b"#"):
            continue
        tokens.extend(stripped.split())
    return tokens


def load_pgm_image(path: Path) -> tuple[int, int, int, list[int]]:
    with path.open("rb") as handle:
        magic = handle.readline().strip()
        if magic not in {b"P2", b"P5"}:
            raise ValueError(f"Unsupported PGM format: {magic!r}")

        width, height, max_value = map(int, _read_non_comment_tokens(handle, 3))
        pixel_count = width * height
        if magic == b"P5":
            raw = handle.read(pixel_count)
            if len(raw) != pixel_count:
                raise ValueError(f"Expected {pixel_count} bytes in {path}, got {len(raw)}")
            pixels = list(raw)
        else:
            data = handle.read().split()
            if len(data) < pixel_count:
                raise ValueError(f"Expected {pixel_count} pixels in {path}, got {len(data)}")
            pixels = [int(value) for value in data[:pixel_count]]

    return width, height, max_value, pixels


class OccupancyMapScene:
    def __init__(self, map_yaml_path: str) -> None:
        yaml_path = Path(map_yaml_path).expanduser().resolve()
        with yaml_path.open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)

        image_path = Path(str(config["image"]))
        if not image_path.is_absolute():
            image_path = yaml_path.parent / image_path

        self.width, self.height, self.max_value, self.pixels = load_pgm_image(image_path)
        self.resolution = float(config["resolution"])
        origin = config.get("origin", [0.0, 0.0, 0.0])
        self.origin_x = float(origin[0])
        self.origin_y = float(origin[1])
        self.negate = bool(int(config.get("negate", 0)))
        self.occupied_thresh = float(config.get("occupied_thresh", 0.65))
        self.free_thresh = float(config.get("free_thresh", 0.196))
        self.step_size = max(self.resolution * 0.5, 0.01)

    def _world_to_cell(self, x: float, y: float) -> tuple[int, int] | None:
        mx = int((x - self.origin_x) / self.resolution)
        my = int((y - self.origin_y) / self.resolution)
        if mx < 0 or mx >= self.width or my < 0 or my >= self.height:
            return None
        row = self.height - 1 - my
        return row, mx

    def _occupancy_probability(self, pixel_value: int) -> float:
        normalized = float(pixel_value) / float(self.max_value)
        if self.negate:
            return normalized
        return 1.0 - normalized

    def is_occupied(self, x: float, y: float) -> bool:
        cell = self._world_to_cell(x, y)
        if cell is None:
            return True

        row, col = cell
        occupancy = self._occupancy_probability(self.pixels[row * self.width + col])
        if occupancy < self.free_thresh:
            return False
        if occupancy >= self.occupied_thresh:
            return True
        return True

    def cast_ray(self, origin_x: float, origin_y: float, angle: float, max_range: float) -> float:
        distance = 0.0
        while distance < max_range:
            sample_x = origin_x + math.cos(angle) * distance
            sample_y = origin_y + math.sin(angle) * distance
            if self.is_occupied(sample_x, sample_y):
                return distance
            distance += self.step_size
        return max_range


class FakeLaserNode(Node):
    def __init__(self) -> None:
        super().__init__("fake_laser")
        self.declare_parameter("scan_topic", "/scan")
        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("laser_frame", "laser")
        self.declare_parameter("room_min_x", -5.0)
        self.declare_parameter("room_max_x", 5.0)
        self.declare_parameter("room_min_y", -5.0)
        self.declare_parameter("room_max_y", 5.0)
        self.declare_parameter("obstacle_min_x", 1.5)
        self.declare_parameter("obstacle_max_x", 2.5)
        self.declare_parameter("obstacle_min_y", -1.0)
        self.declare_parameter("obstacle_max_y", 1.0)
        self.declare_parameter("laser_offset_x", 0.114)
        self.declare_parameter("laser_offset_y", 0.0)
        self.declare_parameter("angle_min", -2.357)
        self.declare_parameter("angle_max", 2.357)
        self.declare_parameter("sample_count", 181)
        self.declare_parameter("range_min", 0.05)
        self.declare_parameter("range_max", 8.0)
        self.declare_parameter("update_rate_hz", 10.0)
        self.declare_parameter("map_yaml", "")

        self.scan_topic = str(self.get_parameter("scan_topic").value)
        self.odom_topic = str(self.get_parameter("odom_topic").value)
        self.laser_frame = str(self.get_parameter("laser_frame").value)
        self.angle_min = float(self.get_parameter("angle_min").value)
        self.angle_max = float(self.get_parameter("angle_max").value)
        self.sample_count = max(int(self.get_parameter("sample_count").value), 2)
        self.range_min = float(self.get_parameter("range_min").value)
        self.range_max = float(self.get_parameter("range_max").value)
        update_rate_hz = max(float(self.get_parameter("update_rate_hz").value), 1.0)
        self.laser_offset_x = float(self.get_parameter("laser_offset_x").value)
        self.laser_offset_y = float(self.get_parameter("laser_offset_y").value)
        room = (
            float(self.get_parameter("room_min_x").value),
            float(self.get_parameter("room_max_x").value),
            float(self.get_parameter("room_min_y").value),
            float(self.get_parameter("room_max_y").value),
        )
        obstacle = (
            float(self.get_parameter("obstacle_min_x").value),
            float(self.get_parameter("obstacle_max_x").value),
            float(self.get_parameter("obstacle_min_y").value),
            float(self.get_parameter("obstacle_max_y").value),
        )
        map_yaml = str(self.get_parameter("map_yaml").value).strip()
        self.map_scene = OccupancyMapScene(map_yaml) if map_yaml else None
        self.segments = scene_segments(room, [obstacle]) if self.map_scene is None else []
        self.pose_x = 0.0
        self.pose_y = 0.0
        self.pose_yaw = 0.0
        self.latest_odom_stamp = None
        self.logged_first_odom = False
        self.logged_first_scan = False

        if self.map_scene is None:
            self.get_logger().info("fake_laser using built-in rectangular room scene")
        else:
            self.get_logger().info(f"fake_laser using occupancy map scene: {map_yaml}")

        self.scan_publisher = self.create_publisher(LaserScan, self.scan_topic, 10)
        self.odom_subscription = self.create_subscription(Odometry, self.odom_topic, self.handle_odom, 10)
        self.timer = self.create_timer(1.0 / update_rate_hz, self.publish_scan)

    def handle_odom(self, message: Odometry) -> None:
        self.pose_x = float(message.pose.pose.position.x)
        self.pose_y = float(message.pose.pose.position.y)
        self.pose_yaw = quaternion_to_yaw(
            float(message.pose.pose.orientation.z),
            float(message.pose.pose.orientation.w),
        )
        self.latest_odom_stamp = message.header.stamp
        if not self.logged_first_odom:
            self.logged_first_odom = True
            self.get_logger().info(
                f"fake_laser received odom pose x={self.pose_x:.3f} y={self.pose_y:.3f} yaw={self.pose_yaw:.3f}"
            )
        self.publish_scan()

    def publish_scan(self) -> None:
        if self.latest_odom_stamp is None:
            return

        laser_x = self.pose_x + math.cos(self.pose_yaw) * self.laser_offset_x - math.sin(self.pose_yaw) * self.laser_offset_y
        laser_y = self.pose_y + math.sin(self.pose_yaw) * self.laser_offset_x + math.cos(self.pose_yaw) * self.laser_offset_y

        scan = LaserScan()
        scan.header.stamp = self.latest_odom_stamp
        scan.header.frame_id = self.laser_frame
        scan.angle_min = self.angle_min
        scan.angle_max = self.angle_max
        scan.angle_increment = (self.angle_max - self.angle_min) / float(self.sample_count - 1)
        scan.range_min = self.range_min
        scan.range_max = self.range_max
        scan.time_increment = 0.0
        scan.scan_time = self.timer.timer_period_ns / 1e9
        scan.ranges = []

        for index in range(self.sample_count):
            angle = self.pose_yaw + self.angle_min + scan.angle_increment * index
            if self.map_scene is None:
                distance = cast_ray((laser_x, laser_y), angle, self.range_max, self.segments)
            else:
                distance = self.map_scene.cast_ray(laser_x, laser_y, angle, self.range_max)
            scan.ranges.append(max(self.range_min, distance))

        self.scan_publisher.publish(scan)
        if not self.logged_first_scan:
            self.logged_first_scan = True
            self.get_logger().info(
                f"fake_laser published first scan with {len(scan.ranges)} beams from x={laser_x:.3f} y={laser_y:.3f}"
            )


def main() -> None:
    rclpy.init()
    node = FakeLaserNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
