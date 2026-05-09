# ROS2 RISC-V 最小控制端记录

## 目标

这份文档只记录一个最小目标：

1. 在 `riscv64` 板子上不追求完整 ROS2 Desktop。
2. 只构建最小控制端运行时。
3. 让板子能够运行 `teleop_twist_keyboard`，并向 `/cmd_vel_teleop` 发布 `Twist`。

当前定位：

- `x86_64` 主机负责 Gazebo / Nav2 / SLAM
- `riscv64` 板子负责控制输入
- 下一步通过局域网把板子的 `/cmd_vel_teleop` 发到主机上的仿真机器人

## 当前结论

在当前板子环境下：

- 系统为 `Bianbu 3.0.1`
- 架构为 `riscv64`
- 默认 Python 为 `3.13`
- 无官方 `ros-humble-*` apt 包
- `pixi` / RoboStack 也没有现成的 `linux-riscv64` ROS2 二进制环境

因此当前可行路线不是“安装 ROS2”，而是：

1. 从源码构建最小 ROS2 运行时
2. 只覆盖 `rclpy + geometry_msgs + teleop_twist_keyboard`
3. 不追求 `ros2 desktop`

## 从零源码编译记录

这一节记录在 `riscv64` 板子上实际走通的最小源码构建路径。

目标不是完整 ROS2，而是最小控制端：

- `rclpy`
- `geometry_msgs`
- `teleop_twist_keyboard`

### 1. 获取源码

当前实际使用了单独的 ROS2 源码树：

```bash
mkdir -p ~/repo
cd ~/repo
git clone https://github.com/ros2/ros2.git -b humble
cd ros2
vcs import src < ros2.repos
```

说明：

- 这里使用的是 ROS2 Humble 源码
- 不依赖系统预装 ROS2

### 2. 建立 Python 虚拟环境

```bash
cd ~/repo/ros2
python3 -m venv venv
source venv/bin/activate
pip install -U pip setuptools wheel
pip install vcstool colcon-common-extensions rosdep
```

### 3. `rosdep` 初始化

`rosdep init` 会写 `/etc/ros/rosdep/sources.list.d`，因此需要 root。

```bash
sudo mkdir -p /etc/ros/rosdep/sources.list.d
sudo rosdep init
```

如果 `sudo` 找不到 venv 里的 `rosdep`，可显式调用：

```bash
sudo ~/repo/ros2/venv/bin/rosdep init
```

### 4. 处理 Bianbu 发行版识别问题

当前板子系统：

- `ID=bianbu`
- `ID_LIKE=debian`

`rosdep` 默认无法识别该发行版，因此需要手工覆盖：

```bash
export ROS_OS_OVERRIDE=debian:bookworm
```

然后更新：

```bash
cd ~/repo/ros2
source venv/bin/activate
export ROS_OS_OVERRIDE=debian:bookworm
rosdep update
```

说明：

- 这里的 override 只是为了让 `rosdep` 和依赖解析继续工作
- 不代表这块板子真的等同于标准 Debian Bookworm

### 5. 避免 `colcon` 扫描 venv

实际踩过一个坑：`colcon` 会递归扫到 `venv/lib/python.../site-packages/numpy/...`，导致把第三方包测试目录当成工作区源码。

处理方式：

```bash
cd ~/repo/ros2
touch venv/COLCON_IGNORE
```

同时，后续构建统一使用：

```bash
--base-paths src
```

### 6. Python 侧依赖

源码构建过程中，当前实际补过的 Python 依赖包括：

```bash
pip install 'empy==3.3.4' numpy lark pyyaml packaging
```

作用：

- `empy==3.3.4`
  - 修复 `rosidl_adapter` 使用的旧模板 API
- `numpy`
  - 供 `rosidl_generator_py` 使用
- `lark`
  - 供 `rosidl_parser` 使用

### 7. 修复 `mimick_vendor`

ROS2 Humble 自带的 `mimick_vendor` 默认抓取的 `ros2/Mimick` 不支持 `riscv64`。

当前实际验证通过的替换目标：

- repo: `https://github.com/LucienMorey/Mimick.git`
- commit: `c45fa027153b4b197dae33d0dea84b4cd630ce7c`

可按下面方式修改：

```bash
cd ~/repo/ros2
file=$(find src -path '*/mimick_vendor/CMakeLists.txt' | head -n1)
sed -i 's#https://github.com/ros2/Mimick.git#https://github.com/LucienMorey/Mimick.git#' "$file"
sed -i 's#set(mimick_version \"de11f8377eb95f932a03707b583bf3d4ce5bd3e7\")#set(mimick_version \"c45fa027153b4b197dae33d0dea84b4cd630ce7c\")#' "$file"
```

检查：

```bash
grep -n 'GIT_REPOSITORY\|mimick_version' "$file"
```

### 8. 修复 `pybind11_vendor`

ROS2 Humble 自带的 `pybind11_vendor` 版本过旧，在当前 `Python 3.13` 上会导致 `rclpy` 构建失败。

当前实际验证通过的替换目标：

- `pybind11 v2.13.6`
- commit: `a2e59f0e7065404b44dfe92a28aca47ba1378dc4`

可按下面方式修改：

```bash
cd ~/repo/ros2
file=$(find src -path '*/pybind11_vendor/CMakeLists.txt' | head -n1)
cp "$file" "${file}.bak"
```

然后用下面脚本更新：

```bash
python3 - <<'PY'
from pathlib import Path
from subprocess import check_output

file_path = check_output(
    "find src -path '*/pybind11_vendor/CMakeLists.txt' | head -n1",
    shell=True,
    text=True,
).strip()
p = Path(file_path)
s = p.read_text()
s = s.replace("ExternalProject_Add(pybind11-2.9.1", "ExternalProject_Add(pybind11-2.13.6")
s = s.replace(
    "GIT_TAG ffa346860b306c9bbfb341aed9c14c067751feb8 # v2.9.1",
    "GIT_TAG a2e59f0e7065404b44dfe92a28aca47ba1378dc4 # v2.13.6",
)
lines = [line for line in s.splitlines() if "pybind11-2.9.1-fix-windows-debug.patch" not in line]
p.write_text("\n".join(lines) + "\n")
PY
```

检查：

```bash
grep -n 'ExternalProject_Add\|GIT_TAG\|PATCH_COMMAND' "$file"
```

### 9. 最小构建命令

```bash
cd ~/repo/ros2
source venv/bin/activate
export ROS_OS_OVERRIDE=debian:bookworm

colcon build --symlink-install \
  --base-paths src \
  --packages-up-to rclpy geometry_msgs teleop_twist_keyboard \
  --cmake-args -DBUILD_TESTING=OFF -DTRACETOOLS_DISABLED=ON
```

说明：

- `--base-paths src` 避免扫到 `venv`
- `--packages-up-to` 控制构建范围，只做最小控制端
- `-DBUILD_TESTING=OFF` 避免不必要的测试依赖
- `-DTRACETOOLS_DISABLED=ON` 关闭 tracing 相关路径

### 10. 构建完成后的验证

```bash
cd ~/repo/ros2
source venv/bin/activate
source install/local_setup.bash

python3 -c "import rclpy; print('rclpy ok')"
python3 -c "from geometry_msgs.msg import Twist; print('geometry_msgs ok')"
./install/teleop_twist_keyboard/lib/teleop_twist_keyboard/teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/cmd_vel_teleop
```

### 11. 这条路线的现实边界

当前结论很明确：

1. 这是一条“最小控制端”源码构建路线
2. 不是完整 ROS2 Desktop 安装方案
3. 不适合把 Gazebo / Nav2 / SLAM 也搬到 `riscv64`
4. 当前更合理的分工仍然是：
   - `x86_64` 主机负责仿真与导航
   - `riscv64` 板子负责控制输入

## 已验证通过的最小能力

当前已经在板子上验证通过：

1. `mimick_vendor` 可通过 fork 修复支持 `riscv64`
2. `pybind11_vendor` 升级后可兼容当前 `Python 3.13`
3. `rclpy` 可成功构建
4. `geometry_msgs` 可成功导入
5. `teleop_twist_keyboard` 可成功运行

## 环境前提

以下内容基于用户实际跑通环境整理：

- 源码目录：`~/repo/ros2`
- Python venv：`~/repo/ros2/venv`
- `rosdep` 使用：
  - `ROS_OS_OVERRIDE=debian:bookworm`
- `colcon` 构建时需要避免扫描 `venv/`

建议先执行：

```bash
cd ~/repo/ros2
source venv/bin/activate
export ROS_OS_OVERRIDE=debian:bookworm
touch venv/COLCON_IGNORE
```

## 关键补丁

### 1. `mimick_vendor`

ROS2 Humble 自带的 `mimick_vendor` 会拉取旧版 `ros2/Mimick`，其 CMake 明确拒绝 `riscv64`。

当前已验证可行的修复是改到：

- 仓库：`https://github.com/LucienMorey/Mimick.git`
- 分支对应固定提交：`c45fa027153b4b197dae33d0dea84b4cd630ce7c`

建议直接修改 `mimick_vendor/CMakeLists.txt` 中的：

- `GIT_REPOSITORY`
- `GIT_TAG`

不要依赖浮动 branch。

### 2. `pybind11_vendor`

ROS2 Humble 自带 `pybind11_vendor` 使用的 `pybind11` 版本过旧，在当前 `Python 3.13` 下会导致 `rclpy` 构建失败。

当前已验证可行的修复是把 `pybind11_vendor` 升到：

- `pybind11 v2.13.6`
- 提交：`a2e59f0e7065404b44dfe92a28aca47ba1378dc4`

同时去掉原先仅服务旧版本的 patch 行。

## Python 侧额外依赖

源码构建过程中，当前实际补过的 Python 依赖包括：

```bash
pip install 'empy==3.3.4' numpy lark pyyaml packaging
```

说明：

- `empy==3.3.4` 用于修复 `rosidl_adapter` 模板接口兼容问题
- `numpy` 用于 `rosidl_generator_py`
- `lark` 用于 `rosidl_parser`

## 最小构建命令

当前已验证通过的最小构建目标：

```bash
cd ~/repo/ros2
source venv/bin/activate
export ROS_OS_OVERRIDE=debian:bookworm

colcon build --symlink-install \
  --base-paths src \
  --packages-up-to rclpy geometry_msgs teleop_twist_keyboard \
  --cmake-args -DBUILD_TESTING=OFF -DTRACETOOLS_DISABLED=ON
```

说明：

- `--base-paths src` 很关键，避免 `colcon` 递归扫进 `venv/`
- 当前先不要求 `ros2cli`
- 当前目标只是最小控制端

## 运行验证

构建完成后，当前已验证可运行：

```bash
cd ~/repo/ros2
source venv/bin/activate
source install/local_setup.bash

python3 -c "import rclpy; print('rclpy ok')"
python3 -c "from geometry_msgs.msg import Twist; print('geometry_msgs ok')"
./install/teleop_twist_keyboard/lib/teleop_twist_keyboard/teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/cmd_vel_teleop
```

说明：

- 当前最稳妥的运行方式是直接执行安装后的脚本
- 不要求 `ros2 run`

## 当前限制

当前方案明确有这些限制：

1. 这不是完整 ROS2 环境
2. 这不是 ROS2 Desktop 替代品
3. 当前只保证最小 Python 控制链
4. 后续如果继续扩到更多包，仍可能遇到新的 `riscv64` 兼容问题

## 下一步：局域网控制 x86 仿真

下一步目标是：

1. 在 `x86_64` 主机上启动 Gazebo 仿真
2. 在 `x86_64` 主机上运行 ROS2 图
3. 在 `riscv64` 板子上运行 `teleop_twist_keyboard`
4. 让板子的 `/cmd_vel_teleop` 直接进入主机上的 `twist_mux`

建议验证顺序：

1. 先确认两台机器能互通 IP
2. 确认两边 ROS Domain 相同
3. 在主机上先能本地看到 `/cmd_vel_teleop`
4. 再切到板子发布
5. 最后验证仿真机器人能随板子键盘输入运动

如果 DDS 组播在局域网受限，再评估：

- 手工指定网卡
- 切换 RMW
- 或单独做一个桥接节点

## 已验证通过的联调结果

当前已经实际验证通过：

1. `x86_64` 主机运行 `pixi` 环境下的 Gazebo + Nav2
2. `riscv64` 板子运行源码构建出的 `teleop_twist_keyboard`
3. 板子通过局域网向 `x86_64` 主机发布 `/cmd_vel_teleop`
4. 主机上的 `twist_mux` 能接收该 topic
5. Gazebo 中的小车可以响应前进、后退、转向

这说明“`riscv64` 作为 ROS2 最小控制端，`x86_64` 作为仿真主机”的异构部署路线是成立的。

## 联调前提

联调前需满足：

1. 两台机器在同一局域网
2. 两边 `ROS_DOMAIN_ID` 一致
3. 两边 `RMW_IMPLEMENTATION` 一致
4. 两边都允许非 localhost 通信

建议统一使用：

```bash
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
```

## x86 主机侧步骤

### 1. 首次部署

在新的 `x86_64` 主机上，仅执行 `pixi install` 还不够，还需要先构建工作区：

```bash
cd ~/projects/ROS-Academy-for-Beginners
pixi install
pixi run build
```

否则 `navigation_sim_demo_ros2`、`robot_sim_demo_ros2` 这类工作区包不会被 `ros2` 发现。

### 2. 启动 Gazebo + Nav2

必须先设好 ROS 环境变量，再启动 demo。不要先启动 demo 再切换 `ROS_DOMAIN_ID`。

```bash
cd ~/projects/ROS-Academy-for-Beginners
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4

pixi run nav2-demo-gazebo
```

### 3. 本机确认 ROS 图已起来

另开一个终端：

```bash
cd ~/projects/ROS-Academy-for-Beginners
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4

pixi shell
source ros2_ws/install/setup.bash
ros2 daemon stop
ros2 daemon start
ros2 topic list
```

正常情况下，不应只看到：

- `/parameter_events`
- `/rosout`

而应至少能看到：

- `/cmd_vel_teleop`
- `/cmd_vel`
- `/odom`
- `/scan`
- `/tf`
- `/map`

### 4. 监听板子发来的控制指令

在主机上执行：

```bash
ros2 topic echo /cmd_vel_teleop
```

这个终端保持打开，用于确认板子侧消息是否到达主机。

## RISC-V 板子侧步骤

```bash
cd ~/repo/ros2
source venv/bin/activate
source install/local_setup.bash

export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4

./install/teleop_twist_keyboard/lib/teleop_twist_keyboard/teleop_twist_keyboard \
  --ros-args -r cmd_vel:=/cmd_vel_teleop
```

启动后可用：

- `i` 前进
- `,` 后退
- `j` 左转
- `l` 右转
- `k` 停止

## 联调成功标准

最小成功标准：

1. `x86_64` 主机上 `ros2 topic echo /cmd_vel_teleop` 可以收到板子消息
2. Gazebo 中的小车能响应键盘输入运动

## 常见问题

### 1. 新主机上包找不到

症状：

- `ros2 launch navigation_sim_demo_ros2 ...`
- 提示 `Package 'navigation_sim_demo_ros2' not found`

原因：

- 只执行了 `pixi install`
- 没有执行 `pixi run build`

处理：

```bash
pixi run build
```

### 2. `ros2 topic list` 只有 `/parameter_events` 和 `/rosout`

症状：

- Gazebo / Nav2 明明已经启动
- 新终端里 `ros2 topic list` 只有两个默认 topic

高概率原因：

- 启动 demo 时和查询时使用了不同的 `ROS_DOMAIN_ID`

这在实际联调中已经出现过：

- demo 先在 `ROS_DOMAIN_ID=0` 下启动
- 后续查询终端切成了 `ROS_DOMAIN_ID=42`
- 导致看不到正在运行的 ROS 图

处理：

1. 停掉当前 demo
2. 在正确的 `ROS_DOMAIN_ID` 下重新启动
3. 新终端也使用同一组环境变量

### 3. VMware 虚拟机在 NAT 网段，无法和局域网设备正常联调

症状：

- 虚拟机 IP 类似 `192.168.120.x`
- 家里或办公室局域网设备在 `192.168.31.x`

这通常说明虚拟机仍在 VMware NAT 网络里，而不是和局域网设备处于同一网段。

建议改成：

- `Bridged`

并尽量桥接到实际联网的物理网卡。

联调时，虚拟机最好直接拿到和局域网同网段的地址，例如：

- `192.168.31.x`

### 4. VMware 下 Gazebo GUI 全白，但按钮可见

症状：

- RViz 正常
- Gazebo GUI 窗口能打开
- 左下角 World Control 等按钮可见
- 3D 场景区域全白，看不到博物馆模型

当前已实际确认，这通常不是场景资源损坏，而是 VMware 图形加速能力不足。

在实际机器上，`glxinfo -B` 输出显示：

- `Accelerated: no`
- `OpenGL renderer string: SVGA3D; build: RELEASE; LLVM;`
- `Video memory: 1MB`

这说明虚拟机没有可用的硬件加速 3D 渲染能力，Gazebo 的 `ogre2` 3D 视图会白屏。

处理方式：

1. 优先确认 VMware 已开启 3D 加速
2. 如果仍然白屏，直接改用软件渲染启动 Gazebo

可先用单独地板场景测试：

```bash
cd ~/projects/ROS-Academy-for-Beginners
export LIBGL_ALWAYS_SOFTWARE=1
pixi run robot-sim-ground-test
```

如果这个命令能正常显示地板和 3D 视图，则说明问题确实在图形渲染路径，而不是场景文件本身。

随后可用软件渲染启动完整 demo：

```bash
cd ~/projects/ROS-Academy-for-Beginners
export LIBGL_ALWAYS_SOFTWARE=1
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4

pixi run nav2-demo-gazebo
```

说明：

- 软件渲染会更慢
- 但在 VMware 中比硬跑 `ogre2` 白屏更实用

### 4. 前后能动，左右偶发不转

当前联调中出现过一次“前后能动、左右暂时不转”，随后恢复正常。

初步判断更像是仿真瞬时卡顿、接触状态或出生位姿导致的偶发问题，而不是联调链路本身错误。

排查顺序建议：

```bash
ros2 topic echo /cmd_vel_teleop
ros2 topic echo /cmd_vel
ros2 topic echo /wheel_velocity_controller/commands
```

判断逻辑：

1. `/cmd_vel_teleop` 有角速度而 `/cmd_vel` 没有：看 `twist_mux`
2. `/cmd_vel` 有角速度而轮速命令没分开：看 `gazebo_interface_bridge`
3. 轮速命令已一正一负但车不转：看 Gazebo 物理接触、卡墙或出生位姿
