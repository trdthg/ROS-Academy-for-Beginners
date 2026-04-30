# ROS2 Linux 二阶段实施清单

## 目标

Windows + Pixi 已经完成第一阶段基础迁移，当前目标切换为：

1. 在 Linux 上补齐仿真、导航、SLAM 这批重生态功能。
2. 不再坚持 ROS1 旧栈原样迁移，优先替换为 ROS2 主流方案。
3. 保留教学价值，而不是保留每一个旧包名或旧算法实现。

## 推荐平台

推荐优先使用：

- Ubuntu 22.04
- ROS 2 Humble

原因：

- 最容易承接当前已经完成的 `ros2_ws/`
- 上游文档、依赖、教程最成熟
- 后续如需切到 `Jazzy`，可以在 Linux 线稳定后再做

## 二阶段主线范围

下面这些包进入 Linux 二阶段主线：

| 原 ROS1 包 | Linux 二阶段方案 |
| :--- | :--- |
| `tf_follower` | 改成 `tf2_ros + rclpy` 跟随控制 |
| `navigation_sim_demo` | 改成 `Nav2` 教学版 |
| `slam_sim_demo` | 改成 `slam_toolbox` 主线，`cartographer` 可选 |
| `robot_sim_demo` | 改成新版 Gazebo + `ros2_control` + `twist_mux` |

## 可选项

下面两项先列为可选，不作为二阶段主线 gate：

| 原 ROS1 包 | 可选替代路线 |
| :--- | :--- |
| `rtabmap_demo` | `RTAB-Map ROS2` |
| `orbslam2_demo` | `RTAB-Map ROS2` 或 `ORB-SLAM3` 实验线 |

说明：

- `orbslam2_demo` 不再原样迁移 `ORB_SLAM2`
- 如果后续要保留 ORB 特征法视觉 SLAM 主题，再单独评估 `ORB-SLAM3`

## 旧栈到新栈替换关系

| ROS1 / 旧方案 | ROS2 / 新方案 |
| :--- | :--- |
| `tf` | `tf2_ros` |
| `move_base` | `Nav2` |
| `gmapping` / `hector_mapping` / `slam_karto` | `slam_toolbox` |
| `gazebo_ros` / `gazebo_ros_control` | `ros_gz` / `ros2_control` |
| `yocs_cmd_vel_mux` | `twist_mux` |
| XML `roslaunch` | Python `launch.py` |
| ROS1 参数服务器 | ROS2 节点参数 |

## 执行顺序

建议按下面顺序推进：

1. 先迁 `tf_follower`
2. 再迁 `navigation_sim_demo`
3. 再迁 `slam_sim_demo`
4. 最后重建 `robot_sim_demo`
5. `rtabmap_demo` 和 `orbslam2_demo` 放到主线稳定后再评估

原因：

- `tf_follower` 代码最小，能先验证 Linux ROS2 线的后续开发节奏
- `navigation` 和 `slam` 的教学价值高于仿真底座重构
- `robot_sim_demo` 最重，放到最后更稳

当前实施偏移（2026-04-29）：

- 为了尽快打通 Nav2 和 SLAM 的真实输入链路，代码实现上已经先拆出一个最小 `robot_sim_demo_ros2`
- 这个最小底座现在已经承担公共仿真接口，并稳定提供 `/cmd_vel`、`/odom`、`/scan`、`/tf`
- `navigation_sim_demo_ros2` 和 `slam_sim_demo_ros2` 都已经基于这套最小底座工作
- 文档里的“最后重建 `robot_sim_demo`”仍然成立，但该阶段现在收敛为：
  - 先把当前最小底座升级到 `ros2_control + twist_mux`
  - 再把这条已跑通的控制与传感器链接到新版 Gazebo / `ros_gz`
  - 而不是等到那时才第一次开始做仿真接口

## 分阶段任务

### 阶段 A：Linux 基线

目标：建立 Linux 下的第二阶段开发环境。

执行项：

1. 新建 Linux 环境说明文档
2. 在 Linux 上拉起 `ros2_ws/`
3. 先让当前已迁移 ROS2 包在 Linux 下完成一次 `build + test`
4. 明确 Linux 侧依赖安装方式：`apt + rosdep + colcon`

通过标准：

- Linux 下能成功构建当前 `ros2_ws/`
- 第一阶段包不回归

当前状态（2026-04-29）：

- 已为 `pixi.toml` 增加 `linux-64` 平台，并补充 `scripts/pixi-ros2-activate.sh`
- 在当前 Linux 主机上已完成一次 `pixi install`
- `pixi run build` 已通过，当前 `ros2_ws/` 的 16 个 ROS2 包全部构建成功
- `pixi run test` 已通过，现有 Python smoke tests 在 Linux 下可正常执行
- `pixi run test-result` 仍显示 `0 tests`，这是当前 `unittest + console_direct` 输出方式导致的统计限制，不作为 gate

### 阶段 B：`tf_follower`

目标：把跟随逻辑从 ROS1 `tf` 改成 ROS2 `tf2`。

范围：

- 先迁纯控制逻辑
- 先不强依赖 Gazebo

执行项：

1. 新建 `tf_follower_ros2` 或并入 `ros2_ws/src`
2. 用 `tf2_ros.Buffer` / `TransformListener`
3. 发布 `geometry_msgs/msg/Twist`
4. 做最小 smoke test

通过标准：

- 能在两帧之间读取 TF
- 能连续输出跟随控制
- 节点停止时能正确发零速

当前状态（2026-04-29）：

- 已新增 `ros2_ws/src/tf_follower_ros2`
- 已将 ROS1 `py_tf_follower.py` 迁为 `rclpy + tf2_ros` 版本
- 已补最小 launch 入口与纯 Python 控制逻辑测试
- 已补动态假 TF broadcaster demo，可在不接 Gazebo 的情况下观察 `/mybot_cmd_vel` 持续变化
- 当前范围仍是“纯跟随控制逻辑”，尚未重新接入 Gazebo / `robot_sim_demo`

### 阶段 C：`navigation_sim_demo -> Nav2`

目标：把 ROS1 导航演示重写成 ROS2 Nav2 教学版。

执行项：

1. 梳理旧 demo 中真正需要保留的教学目标
2. 用 Nav2 重建：
   - map server
   - localization
   - planner/controller
   - bringup launch
3. 整理新的参数文件和 RViz 配置
4. 做一次完整导航链验证

通过标准：

- 已知地图可加载
- 初始位姿可设置
- 2D Goal 能执行
- 导航结果在 RViz 中可观察

当前状态（2026-04-29）：

- 已新增 `ros2_ws/src/navigation_sim_demo_ros2`
- 已将旧 `slam_sim_demo/maps/Software_Museum.{yaml,pgm}` 复制进新包，作为已知地图输入
- 已通过 Pixi 增加 Nav2 依赖：
  - `ros-humble-nav2-bringup`
  - `ros-humble-nav2-map-server`
  - `ros-humble-nav2-amcl`
  - `ros-humble-nav2-rviz-plugins`
- 已新增 `nav2_demo.launch.py`
  - 自动拉起 `robot_sim_demo_ros2`
  - 直接拉起 `nav2_map_server + nav2_amcl + Nav2 navigation stack`
  - 使用 `navigation_sim_demo_ros2/nav2_lifecycle_runner.py` 自管 lifecycle 顺序
  - 已补 `use_gazebo` / `gz_headless` 开关，可切到新版 Gazebo 路径
  - 可选启动导航 RViz
- `pixi run nav2-demo-headless` 已验证：
  - 地图可加载
  - 初始位姿可注入 AMCL
  - 自定义 lifecycle bringup 会输出 `nav2-stack-active`
- `pixi run nav2-goal-check` 已验证：
  - `BasicNavigator` 可发送 `NavigateToPose`
  - 机器人 `/odom` 会在目标发送后发生变化
  - 当前闭环检查会输出 `navigation-motion-detected`
- `pixi run nav2-demo-gazebo-headless` 已验证：
  - Gazebo 场景下地图加载、AMCL 初始位姿注入、自定义 lifecycle bringup 都可完成
  - 后台会输出 `nav2-stack-active`
- `pixi run nav2-goal-check-gazebo` 已验证：
  - Gazebo 场景下 `BasicNavigator` 可正常发出目标
  - 机器人会产生可观测位移，当前闭环检查输出 `navigation-motion-detected`

当前缺口：

- 主要链路已经可用，但启动初期仍可能看到少量 AMCL 初始位姿时间外推告警
- `nav2-goal-check` 在检测到位移后会主动取消 goal，因此后台仍可能出现一次 Nav2 cancel / halt 相关日志
- 目前验证的是“目标发送后确实发生导航位移”，还没有补更完整的自动化验收，例如最终位姿误差门限

### 阶段 D：`slam_sim_demo -> slam_toolbox`

目标：把旧 SLAM 演示收敛为 ROS2 下可维护的一条主线。

主线：

- `slam_toolbox`

可选补充：

- `cartographer`

执行项：

1. 保留 2D 建图教学目标
2. 重做 launch、RViz、参数
3. 验证在线建图、保存地图、重载地图
4. 如有必要，再补 `cartographer` 对照版

通过标准：

- LaserScan / TF / odom 链正常
- 地图可持续增长
- 地图可保存并复用

当前状态（2026-04-29）：

- 已新增 `ros2_ws/src/slam_sim_demo_ros2`
- 已采用 `slam_toolbox` 的 `online_async_launch.py` 作为主线
- 已新增 `slam_demo.launch.py`
  - 自动拉起 `robot_sim_demo_ros2`
  - 拉起 `async_slam_toolbox_node`
  - 已补 `use_gazebo` / `gz_headless` 开关，可切到新版 Gazebo 路径
  - 可选启动新的 SLAM RViz 配置
- 已新增 `slam_toolbox_params.yaml`
  - 对当前最小仿真的 `/scan`、`/odom`、`base_footprint`、`odom`、`map` 帧命名完成适配
  - 降低了 `minimum_travel_distance` / `minimum_travel_heading`，让教学 demo 更快出现地图更新
- 已新增 `slam_map_runner.py`
  - 自动发布一段 `/cmd_vel` 运动序列
  - 监听 `/map`
  - 检查地图已从初始状态继续增长
- 已新增 `slam_save_reload_runner.py`
  - 调用 `nav2_map_server/map_saver_cli` 从 `/map` 保存 `yaml + pgm`
  - 再临时拉起 `map_server` 重载刚保存的 YAML
  - 检查可从 `/reloaded_map` 收到重载后的 OccupancyGrid
- 已验证：
  - `pixi run slam-demo-headless` 可正常拉起 `slam_toolbox`
  - `pixi run slam-map-check` 当前会输出 `slam-map-updated`
  - `pixi run slam-demo-gazebo-headless` 可在 Gazebo 场景下正常拉起 `slam_toolbox`
  - `pixi run slam-map-check-gazebo` 当前会输出 `slam-map-updated`
  - `pixi run slam-save-reload-check` 当前会输出 `slam-map-saved-and-reloaded`
  - `pixi run slam-save-reload-check-gazebo` 当前会输出 `slam-map-saved-and-reloaded`

当前缺口：

- 还没有评估是否需要再补一条 `cartographer` 对照线

### 阶段 E：`robot_sim_demo` 仿真底座

目标：给导航和 SLAM 提供 Linux ROS2 下的仿真底座。

执行项：

1. 评估是否继续使用当前模型和场景资源
2. 把控制链换成 `ros2_control`
3. 把速度复用换成 `twist_mux`
4. 把 Gazebo Classic launch 改成新版 Gazebo / `ros_gz`
5. 补机器人传感器与控制链验证

通过标准：

- 机器人能生成 `/tf`、`/odom`、`/scan`
- 能接受 `/cmd_vel`
- 能为 Nav2 和 `slam_toolbox` 提供稳定输入

当前状态（2026-04-29）：

- 已先落地 `ros2_ws/src/robot_sim_demo_ros2` 作为最小仿真底座
- 控制链默认已切到 `ros2_control + twist_mux`：
  - `sim_bringup.launch.py` 默认拉起 `ros2_control_node`、`ros2_control_runner`、`twist_mux`
  - `diff_drive_base_controller` 负责底盘速度输入与 `/odom`
  - `cmd_vel_teleop` 和 `cmd_vel_nav_smoothed` 会在 mux 内汇总后输出到底盘控制器
- `simple_base_sim.py` 仍保留为回退路径，可通过 `use_ros2_control:=false` 启动
- 已打通新版 Gazebo / `ros_gz` 路径：
  - Gazebo 模式下改用 `wheel_velocity_controller`
  - `gazebo_interface_bridge.py` 负责 `/cmd_vel -> 左右轮速度命令`
  - `joint_states -> /odom + /tf` 里程计链路由桥接节点统一生成
- `fake_laser.py` 继续负责合成 `/scan`
  - Gazebo 路径下已改为不跟随 sim-time timer，避免 `/scan` 不稳定导致 Nav2 无法推进
- 这套最小底座已经被 `navigation_sim_demo_ros2` 和 `slam_sim_demo_ros2` 共用
- 已验证：
  - `pixi run robot-sim-demo-headless` 下 `ros2_control` 控制器可成功激活，`/cmd_vel_teleop -> /odom` 链路正常
  - `pixi run robot-sim-demo-gazebo-headless` 下 `ros_gz + ros2_control + wheel_velocity_controller + 自定义 bridge` 可正常工作
  - Gazebo 路径保持 `/cmd_vel`、`/odom`、`/scan`、`/tf` 接口契约不变
  - `pixi run nav2-demo-headless + pixi run nav2-goal-check` 在默认 `ros2_control` 路径下通过，输出 `navigation-motion-detected`
  - `pixi run nav2-demo-gazebo-headless + pixi run nav2-goal-check-gazebo` 在 Gazebo 路径下通过，输出 `navigation-motion-detected`
  - `pixi run slam-demo-headless + pixi run slam-map-check` 在默认 `ros2_control` 路径下通过，输出 `slam-map-updated`
  - `pixi run slam-demo-gazebo-headless + pixi run slam-map-check-gazebo` 在 Gazebo 路径下通过，输出 `slam-map-updated`
  - `pixi run slam-save-reload-check` 在同一路径下通过，输出 `slam-map-saved-and-reloaded`
  - `pixi run slam-demo-gazebo-headless + pixi run slam-save-reload-check-gazebo` 在 Gazebo 路径下通过，输出 `slam-map-saved-and-reloaded`
- 当前 `Ctrl-C` 退出路径也已修正，不再因为重复 `rclpy.shutdown()` 在 launch 收尾时报错
- Gazebo GUI 资源路径问题已修正，机器人模型可正常显示
- 已补单独的地板诊断入口 `pixi run robot-sim-ground-test`
  - 只加载 `ISCAS_groundplane`，用于隔离排查地板纹理 / 材质问题
- 当前 Gazebo 场景约定已拆分：
  - GUI 演示默认使用 `museum.sdf`
  - headless 回归固定使用 `empty.sdf`
  - museum GUI 的机器人出生位姿单独覆盖为 `spawn_x:=5.0 spawn_y:=0.0 spawn_yaw:=-2.0`
- `museum.sdf` 当前保留了一层 floor overlay 作为兼容修复，确保馆内地板纹理在 Gazebo GUI 下可见
- Gazebo GUI 仍可能打印 `IgnGazebo` QML panel 相关报错；当前判断为界面插件缺失，不阻塞仿真与控制链

后续收口范围：

- 保留当前 `ros2_control + twist_mux` 默认接口契约
- 基于同一接口继续补 Gazebo 路径下更完整的回归与教学说明

## 风险控制

### 不再保留的旧教学对照

下面这些旧路线不建议作为 Linux 二阶段必须保留项：

- `move_base`
- `gmapping`
- `hector_mapping`
- `slam_karto`
- `gazebo_ros_control`
- `ORB_SLAM2`

### 需要提前接受的事实

1. 二阶段不是“升级”，而是“重写重组”。
2. 新 demo 的 launch、参数、目录结构会和 ROS1 版明显不同。
3. 最后保留下来的教学目标会比原仓库更少，但会更稳定。

## 验收门槛

Linux 二阶段主线完成的最低验收标准：

1. Linux 下可从零安装依赖
2. `ros2_ws/` 能 build
3. 每个迁移包至少有一条可复现 demo 路径
4. 每个迁移包至少有一个 smoke test 或 launch test
5. 不再依赖 ROS1 运行时
6. 触及 `robot_sim_demo_ros2`、`navigation_sim_demo_ros2`、`slam_sim_demo_ros2` 主链路的改动，需通过 `pixi run phase2-acceptance`

当前固定验收命令（2026-04-29）：

- `pixi run phase2-acceptance`
- 目前等价于 `pixi run gazebo-regression`
- 这条命令串行覆盖 Gazebo headless 下的 robot sim、Nav2、SLAM 主线回归

## 建议里程碑

建议拆成三个里程碑：

### M1

- Linux 基线完成
- `tf_follower` 迁移完成

### M2

- `navigation_sim_demo` 的 Nav2 版完成
- `slam_sim_demo` 的 `slam_toolbox` 版完成

### M3

- `robot_sim_demo` 新仿真底座完成
- 再决定是否开启 `RTAB-Map` 或 `ORB-SLAM3` 可选线
