#!/usr/bin/env bash

export ROS_LOG_DIR="${PIXI_PROJECT_ROOT}/ros2_ws/log/ros"
mkdir -p "${ROS_LOG_DIR}"
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4

ROS2_WS_SETUP="${PIXI_PROJECT_ROOT}/ros2_ws/install/setup.bash"
if [ -f "${ROS2_WS_SETUP}" ]; then
  # Source the workspace overlay when it exists so pixi tasks see built packages.
  # shellcheck disable=SC1090
  . "${ROS2_WS_SETUP}"
fi
