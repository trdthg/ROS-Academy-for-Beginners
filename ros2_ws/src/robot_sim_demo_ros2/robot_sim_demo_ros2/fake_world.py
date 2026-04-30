from typing import Iterable, List, Sequence, Tuple
import math

Point2D = Tuple[float, float]
Segment2D = Tuple[Point2D, Point2D]
Rectangle2D = Tuple[float, float, float, float]


def rectangle_segments(rect: Rectangle2D) -> List[Segment2D]:
    min_x, max_x, min_y, max_y = rect
    return [
        ((min_x, min_y), (max_x, min_y)),
        ((max_x, min_y), (max_x, max_y)),
        ((max_x, max_y), (min_x, max_y)),
        ((min_x, max_y), (min_x, min_y)),
    ]


def scene_segments(room: Rectangle2D, obstacles: Sequence[Rectangle2D]) -> List[Segment2D]:
    segments = rectangle_segments(room)
    for obstacle in obstacles:
        segments.extend(rectangle_segments(obstacle))
    return segments


def ray_segment_distance(origin: Point2D, direction: Point2D, segment: Segment2D) -> float | None:
    (ox, oy) = origin
    (dx, dy) = direction
    (sx1, sy1), (sx2, sy2) = segment
    ex = sx2 - sx1
    ey = sy2 - sy1
    denominator = dx * ey - dy * ex
    if abs(denominator) < 1e-9:
        return None

    rx = sx1 - ox
    ry = sy1 - oy
    t = (rx * ey - ry * ex) / denominator
    u = (rx * dy - ry * dx) / denominator
    if t >= 0.0 and 0.0 <= u <= 1.0:
        return t
    return None


def cast_ray(
    origin: Point2D,
    angle: float,
    max_range: float,
    segments: Iterable[Segment2D],
) -> float:
    direction = (math.cos(angle), math.sin(angle))
    best = max_range
    for segment in segments:
        distance = ray_segment_distance(origin, direction, segment)
        if distance is not None and distance < best:
            best = distance
    return best
