#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${REPO_ROOT}/ros2_ws/log/gazebo_regression"

mkdir -p "${LOG_DIR}"

CURRENT_PID=""
CURRENT_LOG=""

log() {
  printf '[gazebo-regression] %s\n' "$*"
}

dump_current_log() {
  if [[ -n "${CURRENT_LOG}" && -f "${CURRENT_LOG}" ]]; then
    log "Last lines from ${CURRENT_LOG}:"
    tail -n 60 "${CURRENT_LOG}" || true
  fi
}

cleanup_stale_processes() {
  local patterns=(
    "ign gazebo .*${REPO_ROOT}/ros2_ws/install/share/robot_sim_demo_ros2/worlds/empty.sdf"
    "${REPO_ROOT}/ros2_ws/install/lib/robot_sim_demo_ros2/gazebo_interface_bridge"
    "${REPO_ROOT}/ros2_ws/install/lib/robot_sim_demo_ros2/fake_laser"
    "${REPO_ROOT}/ros2_ws/install/lib/robot_sim_demo_ros2/ros2_control_runner"
    "${REPO_ROOT}/ros2_ws/install/lib/navigation_sim_demo_ros2/nav2_lifecycle_runner"
    "/nav2_map_server/map_server"
    "/nav2_amcl/amcl"
    "/nav2_controller/controller_server"
    "/nav2_planner/planner_server"
    "/nav2_behaviors/behavior_server"
    "/nav2_bt_navigator/bt_navigator"
    "/nav2_waypoint_follower/waypoint_follower"
    "/nav2_velocity_smoother/velocity_smoother"
    "/nav2_smoother/smoother_server"
    "/slam_toolbox/async_slam_toolbox_node"
  )

  for pattern in "${patterns[@]}"; do
    pkill -INT -f "${pattern}" 2>/dev/null || true
  done
  sleep 2
  for pattern in "${patterns[@]}"; do
    pkill -TERM -f "${pattern}" 2>/dev/null || true
  done
  sleep 1
}

wait_for_demo_exit() {
  if [[ -n "${CURRENT_PID}" ]]; then
    wait "${CURRENT_PID}" 2>/dev/null || true
    CURRENT_PID=""
    CURRENT_LOG=""
  fi
}

stop_current_demo() {
  if [[ -n "${CURRENT_PID}" ]]; then
    kill -INT -- "-${CURRENT_PID}" 2>/dev/null || true
    wait_for_demo_exit
    sleep 2
  fi
}

trap stop_current_demo EXIT

run_cmd() {
  log "Running: $*"
  "$@"
}

run_checked() {
  log "Running: $*"
  if ! "$@"; then
    dump_current_log
    return 1
  fi
}

start_demo() {
  local name="$1"
  shift

  CURRENT_LOG="${LOG_DIR}/${name}.log"
  : > "${CURRENT_LOG}"

  log "Starting ${name}"
  setsid "$@" >"${CURRENT_LOG}" 2>&1 &
  CURRENT_PID=$!
}

wait_for_log() {
  local pattern="$1"
  local timeout_sec="$2"
  local deadline=$((SECONDS + timeout_sec))

  while (( SECONDS < deadline )); do
    if grep -q "${pattern}" "${CURRENT_LOG}"; then
      return 0
    fi
    if ! kill -0 "${CURRENT_PID}" 2>/dev/null; then
      dump_current_log
      return 1
    fi
    sleep 1
  done

  dump_current_log
  return 1
}

wait_for_topic() {
  local topic_name="$1"
  local topic_type="$2"
  local timeout_sec="$3"

  if ! timeout "${timeout_sec}" ros2 topic echo --once "${topic_name}" "${topic_type}" >/dev/null; then
    dump_current_log
    return 1
  fi
}

main() {
  cd "${REPO_ROOT}"

  cleanup_stale_processes
  run_cmd pixi run build
  run_cmd bash -lc "cd '${REPO_ROOT}/ros2_ws' && pixi run colcon test --merge-install --event-handlers console_direct+ --return-code-on-test-failure --packages-select robot_sim_demo_ros2 navigation_sim_demo_ros2 slam_sim_demo_ros2"

  start_demo "robot_sim_gazebo_headless" pixi run robot-sim-demo-gazebo-headless
  wait_for_topic "/odom" "nav_msgs/msg/Odometry" 20s
  wait_for_topic "/scan" "sensor_msgs/msg/LaserScan" 20s
  stop_current_demo

  start_demo "nav2_gazebo_headless" pixi run nav2-demo-gazebo-headless
  wait_for_log "nav2-stack-active" 60
  run_checked pixi run nav2-goal-check-gazebo
  stop_current_demo

  start_demo "slam_gazebo_headless" pixi run slam-demo-gazebo-headless
  wait_for_log "Registering sensor" 30
  sleep 2
  run_checked pixi run slam-map-check-gazebo
  run_checked pixi run slam-save-reload-check-gazebo
  stop_current_demo

  log "Gazebo regression passed"
}

main "$@"
