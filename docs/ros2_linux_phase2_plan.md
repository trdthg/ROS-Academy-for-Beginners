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
