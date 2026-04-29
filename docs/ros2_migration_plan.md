# ROS2 迁移方案

## 目标

这个仓库是一个典型的 ROS1 教学仓库，包含：

- 自定义 `msg/srv/action`
- `rospy` / `roscpp` 通信示例
- `tf` 示例
- ROS1 XML launch
- Gazebo Classic 仿真
- ROS1 导航与 SLAM 生态

这类仓库不适合一次性整体切换到 ROS2。更稳妥的方式是：

1. 先把环境和构建链切到 ROS2。
2. 先迁移通信、接口、参数、TF、URDF 这类基础教学包。
3. 最后再处理仿真、导航、SLAM 这些依赖旧生态最重的包。

当前仓库保留 ROS1 代码原位不动，ROS2 版本建议逐步放入 `ros2_ws/src/`。

## 为什么先用并行工作区

当前根目录所有包都是 ROS1 `catkin` 包，直接在原地改成 ROS2 会有三个问题：

1. `colcon` 与 `ament_*` 会和现有 `catkin` 布局混在一起。
2. 迁移过程中很难逐包验证，容易全部同时坏掉。
3. 教学仓库本身还需要保留 ROS1 示例作为对照。

所以这里先建立：

- Pixi 环境：项目根目录下 `.pixi/`
- ROS2 工作区：`ros2_ws/`

这样你可以在同一个仓库里同时保留 ROS1 原始材料和 ROS2 迁移版本。

## Windows + Pixi 的建议基线

建议首批使用：

- Pixi
- RoboStack `robostack-humble`
- `colcon`
- `ament_cmake` / `ament_python`

原因：

- Pixi 官方 ROS2 教程直接给的是 `robostack-humble`。
- Pixi 官方文档明确说明 ROS 安装会进入工作区下的 `.pixi` 目录。
- Windows 下官方示例使用 `install/setup.bat` 作为激活脚本。
- Pixi 环境里不支持 `rosdep`，依赖需要通过 `pixi add` 管理。

## 包级迁移优先级

### 第一批：建议马上迁移

这些包基本不依赖 Gazebo / 导航 / 旧 SLAM 栈，最适合先打通：

| ROS1 包 | ROS2 建议 |
| :--- | :--- |
| `msgs_demo` | 改成 `msgs_demo_interfaces`，只负责 `msg/srv/action` |
| `topic_demo` | 改成 `topic_demo_cpp` + `topic_demo_py` |
| `service_demo` | 改成 `service_demo_cpp` + `service_demo_py` |
| `action_demo` | 改成 `action_demo_cpp` + `action_demo_py` |
| `param_demo` | 改成 ROS2 参数示例 |
| `name_demo` | 改成 ROS2 命名空间与参数示例 |
| `tf_demo` | 迁到 `tf2_ros` / `tf2_geometry_msgs` |

### 第二批：可以在基础功能稳定后迁移

| ROS1 包 | ROS2 建议 |
| :--- | :--- |
| `urdf_demo` | 迁到 `robot_state_publisher` + `joint_state_publisher_gui` + `rviz2` |
| `ros_academy_for_beginners` | 取消 metapackage 角色，改成文档和 workspace 组织 |

### 第三批：不建议作为 Windows 首批目标

这些包高度依赖 ROS1 旧生态，建议最后处理，甚至单独在 Linux/WSL2 做：

| ROS1 包 | 风险 |
| :--- | :--- |
| `robot_sim_demo` | 依赖 Gazebo Classic、`gazebo_ros_control`、`yocs_cmd_vel_mux` |
| `tf_follower` | 依赖 Gazebo 仿真和 TF 跟随控制 |
| `navigation_sim_demo` | 需要从 `move_base` 迁到 Nav2 |
| `slam_sim_demo` | `gmapping` / `hector` / `karto` 在 ROS2 路线不统一 |
| `rtabmap_demo` | 取决于 `rtabmap_ros` 在 Win + RoboStack 的可用性 |
| `orbslam2_demo` | ORB_SLAM2 本身老旧，Windows 迁移成本高 |

## 关键技术替换关系

| ROS1 | ROS2 |
| :--- | :--- |
| `catkin_make` | `colcon build` |
| `catkin` | `ament_cmake` / `ament_python` |
| `roscpp` | `rclcpp` |
| `rospy` | `rclpy` |
| `actionlib` | ROS2 Action |
| `tf` | `tf2_ros` / `tf2_geometry_msgs` |
| XML `.launch` | Python `launch.py` |
| 全局参数服务器 | 节点内声明参数 |
| `move_base` | Nav2 |
| `gmapping/hector/karto` | 优先评估 `slam_toolbox` |
| Gazebo Classic | 优先评估新版 Gazebo 与 `ros_gz` |

## 这个仓库里的实际迁移阻塞点

除了 API 差异，这个仓库本身还有一些老代码问题，迁移时要顺手修：

1. 多个 Python 脚本是 Python 2 写法，例如 `print` 语句和旧式异常捕获。
2. `action_demo/src/dishes_Server.py` 里存在缩进错误和 `roslib.load_manifest` 旧写法。
3. 多个包直接依赖 ROS1 特有包，如 `move_base`、`amcl`、`gmapping`、`gazebo_ros_control`。
4. `tf_demo` 大量使用 `tf` C++ API，ROS2 里需要整体替换为 `tf2` 体系。

## 建议迁移顺序

### 阶段 0：环境与目录

1. 用 Pixi 固定 Windows 本地 ROS2 环境。
2. 在 `ros2_ws/src/` 新建 ROS2 包，不直接覆盖 ROS1 原目录。
3. 先跑通 `pixi run turtlesim`、`pixi run build`、`pixi run test` 基础链路。

### 阶段 1：接口包

1. 新建 `msgs_demo_interfaces`。
2. 把 `msg/`、`srv/`、`action/` 迁到 ROS2 接口定义。
3. 用 `rosidl_generate_interfaces()` 生成接口。
4. 先让接口包单独编译通过。

### 阶段 2：通信示例

1. 迁移 `topic_demo`。
2. 迁移 `service_demo`。
3. 迁移 `action_demo`。
4. 每迁一个包都补最小可运行测试。

### 阶段 3：参数和 TF

1. 迁移 `param_demo`，改为显式声明参数。
2. 迁移 `name_demo`，验证命名空间与参数覆盖。
3. 迁移 `tf_demo`，优先保留 broadcaster / listener / 坐标变换示例。

### 阶段 4：URDF / RViz

1. 迁移 `urdf_demo` 中纯描述与 RViz 展示部分。
2. 暂时不把 Gazebo 联动作为必做项。

### 阶段 5：导航 / SLAM / 仿真

1. 重新评估 Windows 是否仍然是目标平台。
2. 如果要完整迁移仿真与导航，优先切到 Linux 或 WSL2。
3. 再处理 Nav2、SLAM Toolbox、RTAB-Map 或新版 Gazebo。

Linux 二阶段详细实施清单见：

- `docs/ros2_linux_phase2_plan.md`

## 结论

这个仓库可以迁到 ROS2，但不应该理解为“原地一键升级”。

对你当前的 Windows + Pixi 场景，最现实的落地方式是：

1. 用 Pixi 管住本地 ROS2 环境。
2. 在 `ros2_ws/src/` 做并行迁移。
3. 先迁 `msgs/topic/service/action/param/tf/name/urdf`。
4. 暂时把 Gazebo、导航、SLAM 放到后面的 Linux 优先阶段。
