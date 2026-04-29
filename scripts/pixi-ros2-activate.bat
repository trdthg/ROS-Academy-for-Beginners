@echo off

set "ROS_LOG_DIR=%PIXI_PROJECT_ROOT%\ros2_ws\log\ros"
mkdir "%ROS_LOG_DIR%" >nul 2>nul
set "FASTDDS_BUILTIN_TRANSPORTS=UDPv4"

set "ROS2_WS_SETUP=%PIXI_PROJECT_ROOT%\ros2_ws\install\setup.bat"
if exist "%ROS2_WS_SETUP%" (
  call "%ROS2_WS_SETUP%"
)
