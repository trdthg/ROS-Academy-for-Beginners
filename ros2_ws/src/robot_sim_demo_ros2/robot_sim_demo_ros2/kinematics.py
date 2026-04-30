import math
from typing import Tuple


def normalize_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def integrate_diff_drive(
    x: float,
    y: float,
    yaw: float,
    linear_velocity: float,
    angular_velocity: float,
    dt: float,
) -> Tuple[float, float, float]:
    new_x = x + linear_velocity * math.cos(yaw) * dt
    new_y = y + linear_velocity * math.sin(yaw) * dt
    new_yaw = normalize_angle(yaw + angular_velocity * dt)
    return (new_x, new_y, new_yaw)


def wheel_angular_velocities(
    linear_velocity: float,
    angular_velocity: float,
    wheel_separation: float,
    wheel_radius: float,
) -> Tuple[float, float]:
    left = (linear_velocity - angular_velocity * wheel_separation / 2.0) / wheel_radius
    right = (linear_velocity + angular_velocity * wheel_separation / 2.0) / wheel_radius
    return (left, right)
