# ROS2 迁移测试计划

## 测试目标

确保迁移不是“能编译就算完成”，而是至少满足以下四类目标：

1. Pixi 环境在 Windows 当前仓库下可重复创建。
2. ROS2 接口包生成正确，C++ 和 Python 都能使用。
3. 基础通信示例在 ROS2 下行为正确。
4. 每一批迁移包都有明确的入口、退出条件和回归检查。

## 测试分层

### T0 环境层

目标：确认 Pixi + ROS2 + colcon 链路稳定。

执行项：

1. `pixi install`
2. `pixi run pkg-list`
3. `pixi run build`
4. `pixi run test`
5. `pixi run test-result`

通过标准：

- `.pixi/envs/default` 已生成
- `ros2 pkg list` 能正常输出
- `colcon build` 在空或已迁移工作区内成功结束
- `colcon test` 无失败用例

说明：

- 当前首批 Python smoke test 走的是 `unittest` 控制台输出
- 因此 `pixi run test` 是否成功，比 `pixi run test-result` 的统计数字更关键

Linux 当前基线结果（2026-04-29）：

- 在 Linux 上补充 `pixi` 的 `linux-64` 平台后，`pixi install` 可成功完成
- `pixi run build` 通过
- `pixi run test` 通过
- `pixi run test-result` 仍显示 `0 tests`，当前应继续以 `pixi run test` 的退出码作为通过标准

### T1 接口层

目标：优先验证 `msgs_demo_interfaces` 的 `msg/srv/action` 迁移正确。

执行项：

1. 构建接口包。
2. 用 `ros2 interface list` 检查接口是否可见。
3. 用 `ros2 interface show <interface>` 检查字段定义。
4. Python 侧导入生成模块。
5. C++ 侧链接生成头文件并完成最小编译。

建议命令：

```powershell
pixi run build
pixi run interface-list
pixi run msg-point-show
pixi run srv-add-two-ints-show
pixi run action-move-base-show
```

通过标准：

- 所有迁移的 `msg/srv/action` 均可被 ROS2 CLI 发现
- Python 节点可以 `import`
- C++ 节点可以成功链接并编译

### T2 Topic 层

目标：验证 `topic_demo` 从 `rospy/roscpp` 到 `rclpy/rclcpp` 的迁移。

执行项：

1. 启动 `talker`。
2. 启动 `listener`。
3. 用 `ros2 topic list` 确认 topic 已出现。
4. 用 `ros2 topic echo` 检查消息内容。
5. 分别验证 C++ 和 Python 版本互通。

通过标准：

- topic 名称、消息类型、频率符合预期
- C++ publisher -> Python subscriber 成功
- Python publisher -> C++ subscriber 成功
- 节点退出后资源能正常释放

### T3 Service 层

目标：验证 `service_demo` 在 ROS2 下请求/响应链路正确。

执行项：

1. 启动 service server。
2. 启动 service client。
3. 用 `ros2 service list` 和 `ros2 service type` 检查服务元信息。
4. 用 CLI 直接发起一次请求。
5. 验证 C++/Python 交叉调用。

通过标准：

- 服务可发现
- 请求字段和响应字段正确
- 超时与错误日志可读
- C++ 与 Python 实现可互调

### T4 Action 层

目标：验证 `action_demo` 从 `actionlib` 迁到 ROS2 Action 后的反馈、结果、取消语义。

执行项：

1. 启动 action server。
2. 启动 action client。
3. 使用 `ros2 action list` 检查 action 可见性。
4. 发送正常 goal，验证 feedback 和 result。
5. 发送取消请求，验证 cancel 行为。

通过标准：

- action server/client 能建立连接
- feedback 正常发布
- result 正确返回
- cancel 语义与实现一致

### T5 参数与命名空间层

目标：验证 `param_demo` 和 `name_demo` 的 ROS2 化改造是否正确。

执行项：

1. 节点启动时声明参数。
2. 用 YAML 覆盖参数。
3. 用 CLI 动态读写参数。
4. 在不同 namespace 下重复启动节点。
5. 验证参数覆盖优先级与命名隔离。

通过标准：

- 未声明参数时行为符合预期
- 默认值与覆盖值正确
- namespace 之间不串参数
- 日志里能明确看到最终生效值

### T6 TF 层

目标：验证 `tf_demo` 从 `tf` 到 `tf2` 的迁移。

执行项：

1. 启动 broadcaster。
2. 启动 listener。
3. 用 `tf2_tools` 或 CLI 检查 frame tree。
4. 验证静态变换和动态变换。
5. 验证坐标换算结果是否和 ROS1 教学含义一致。

通过标准：

- frame tree 完整
- 时间戳正确
- 坐标变换结果数值合理
- broadcaster/listener 在重启后恢复正常

`tf_follower_ros2` 当前补充验证（2026-04-29）：

- 已有纯控制逻辑单元测试，覆盖停车阈值、ROS1 控制形状保持、速度限幅
- 已有最小集成测试，使用假 TF broadcaster 驱动 `tf_follower_ros2`
- 集成测试已验证节点会向 `/mybot_cmd_vel` 发布非零 `Twist`

### T7 Launch 层

目标：验证 ROS1 XML launch 改成 ROS2 Python launch 后仍然能正确拉起节点。

执行项：

1. 单节点 launch。
2. 多节点 launch。
3. 参数传递。
4. namespace 注入。
5. remap 规则验证。

通过标准：

- launch 能正常启动并退出
- 参数、命名空间、remap 生效
- 不依赖手工 source 自定义脚本

`navigation_sim_demo_ros2` 当前补充验证（2026-04-29）：

- `pixi run nav2-demo-headless` 可拉起：
  - `robot_sim_demo_ros2`
  - `nav2_map_server`
  - `nav2_amcl`
  - `controller_server / planner_server / bt_navigator` 等 Nav2 主链路
  - 自定义 `nav2_lifecycle_runner`
- `pixi run nav2-demo-gazebo-headless` 也可拉起同一套 Nav2 主链路，并在 Gazebo 路径下输出 `nav2-stack-active`
- 地图加载与 AMCL 初始位姿注入已确认生效
- `pixi run nav2-goal-check` 已确认可发出 `NavigateToPose`，并检测到 `/odom` 位移
- `pixi run nav2-goal-check-gazebo` 已确认 Gazebo 路径下同样可检测到 `/odom` 位移，并输出 `navigation-motion-detected`
- 当前已不再依赖 `nav2_lifecycle_manager` 自动 bringup，而是由 `nav2_lifecycle_runner` 顺序推进 lifecycle 状态
- `NavigateToPose` 目标发送已改成直接走原生 `ActionClient`，`BasicNavigator` 的 “unexpected goal response” 告警已不再出现
- 自动测试当前覆盖地图资产与参数文件存在性；更严格的终点误差验证仍待后续补充

### T8 URDF / RViz 层

目标：验证 `urdf_demo` 的描述文件和可视化链路。

执行项：

1. 启动 `robot_state_publisher`。
2. 启动 `joint_state_publisher_gui`。
3. 启动 `rviz2`。
4. 验证 TF tree、模型显示、关节联动。

通过标准：

- 模型可加载
- TF tree 正确
- 关节拖动后模型响应正常

说明：
- `pixi run urdf-link-joint` 这组模型的固定坐标系应为 `base_link`
- `pixi run urdf-xacro` 这组模型的固定坐标系应为 `mybot_link`
- 如果 RViz 里又出现 “No transform from ... to [base_link]” 这类告警，通常表示加载了错误的 RViz 配置，而不是 URDF 本身坏了

`robot_sim_demo_ros2` 当前补充验证（2026-04-29）：

- `pixi run robot-sim-demo-headless` 可拉起最小仿真底座
- 当前 launch 默认走 `ros2_control + twist_mux`
- `ros2_control_runner` 会自动激活 `joint_state_broadcaster` 和 `diff_drive_base_controller`
- 已验证 `/cmd_vel_teleop` 会经 `twist_mux` 送到底盘控制器，并驱动 `/odom` 变化
- 默认路径可发布 `/odom`、`/tf`、`/joint_states`
- `fake_laser` 可发布 `/scan`
- 保留 `use_ros2_control:=false` 回退到 `simple_base_sim`
- 自动集成测试已验证 `/cmd_vel` 输入后，里程计位置会变化且激光消息可持续输出
- `pixi run robot-sim-demo-gazebo-headless` 已验证新版 Gazebo 路径：
  - `ros2_control_runner` 会自动激活 `joint_state_broadcaster` 与 `wheel_velocity_controller`
  - `gazebo_interface_bridge.py` 负责 `/cmd_vel -> 左右轮速度`
  - `joint_states` 会被桥接为 `/odom` 与 `/tf`
  - `fake_laser` 在该路径下仍可稳定发布 `/scan`
- `pixi run robot-sim-demo-gazebo` 已确认机器人模型资源可正常加载显示
- `pixi run robot-sim-ground-test` 可单独验证 `ISCAS_groundplane` 纹理链路，不受 museum mesh 干扰
- 目前 Gazebo 路径已拆分为两类：
  - GUI 展示默认走 `museum.sdf`
  - headless 回归固定走 `empty.sdf`
- GUI 模式仍可能出现 `IgnGazebo` QML panel 缺失报错；当前判断为非阻塞问题，不影响控制与导航验证

### T9 Linux 仿真导航 / SLAM 补充验证

目标：确认 Linux 二阶段新增的最小仿真底座已经足以支撑 Nav2 与 `slam_toolbox`。

执行项：

1. 启动 `pixi run robot-sim-demo-headless`，确认基础 `/odom`、`/scan`、`/tf` 链存在。
2. 启动 `pixi run robot-sim-demo-gazebo-headless`，确认 Gazebo 路径下同样存在 `/odom`、`/scan`、`/tf`。
3. 启动 `pixi run nav2-demo-headless`，再执行 `pixi run nav2-goal-check`。
4. 启动 `pixi run nav2-demo-gazebo-headless`，再执行 `pixi run nav2-goal-check-gazebo`。
5. 启动 `pixi run slam-demo-headless`，再执行 `pixi run slam-map-check`。
6. 启动 `pixi run slam-demo-gazebo-headless`，再执行 `pixi run slam-map-check-gazebo`。
7. 在 `slam-demo-headless` 运行中执行 `pixi run slam-save-reload-check`。
8. 在 `slam-demo-gazebo-headless` 运行中执行 `pixi run slam-save-reload-check-gazebo`。
9. 用 `Ctrl-C` 停止长跑 demo，确认 launch 收尾不出现重复 `rclpy.shutdown()` 异常。

通过标准（2026-04-29 当前结果）：

- `pixi run robot-sim-demo-gazebo-headless` 下 Gazebo 控制链可正常工作，`/cmd_vel -> /odom` 链路成立
- `pixi run nav2-goal-check` 在默认 `ros2_control` 路径下输出 `navigation-motion-detected`
- `pixi run nav2-demo-gazebo-headless` 可完成 bringup，并输出 `nav2-stack-active`
- `pixi run nav2-goal-check-gazebo` 在 Gazebo 路径下输出 `navigation-motion-detected`
- Gazebo 路径中的 `/scan` 已被 Nav2 激活与运动结果间接验证
- `pixi run slam-map-check` 在默认 `ros2_control` 路径下输出 `slam-map-updated`
- `pixi run slam-map-check-gazebo` 在 Gazebo 路径下输出 `slam-map-updated`
- `pixi run slam-save-reload-check` 在默认 `ros2_control` 路径下输出 `slam-map-saved-and-reloaded`
- `pixi run slam-save-reload-check-gazebo` 在 Gazebo 路径下输出 `slam-map-saved-and-reloaded`
- `slam-demo-headless` / `nav2-demo-headless` 可被 `Ctrl-C` 干净停止

统一入口：

- `pixi run gazebo-regression` 会串行执行：
  - `pixi run build`
  - `robot_sim_demo_ros2` Gazebo `/odom`、`/scan` smoke check
  - `nav2-demo-gazebo-headless + nav2-goal-check-gazebo`
  - `slam-demo-gazebo-headless + slam-map-check-gazebo + slam-save-reload-check-gazebo`
- `pixi run phase2-acceptance` 目前等价于 `pixi run gazebo-regression`
- 对 `robot_sim_demo_ros2`、`navigation_sim_demo_ros2`、`slam_sim_demo_ros2` 的 Linux 二阶段主线改动，当前统一以这条命令作为固定验收门槛

## 回归策略

每迁完一个包，至少执行：

1. `pixi run build`
2. `pixi run test`
3. 该包对应的 CLI 验证
4. 至少一条跨语言联调路径

不要等所有包都迁完再统一测试。

补充约束（2026-04-29 当前执行方式）：

1. 只要改动触及 `robot_sim_demo_ros2`、`navigation_sim_demo_ros2`、`slam_sim_demo_ros2` 的 Gazebo / Nav2 / SLAM 主链路，就必须额外执行 `pixi run phase2-acceptance`
2. 未通过 `pixi run phase2-acceptance` 的提交，不应视为 Linux 二阶段主线通过

## 自动化建议

建议逐步补下面三类测试：

1. `ament_lint_auto` 静态检查
2. `pytest` / `ament_cmake_gtest` 单元测试
3. `launch_testing` 集成测试

优先级建议：

1. 先给接口包和通信包补最小集成测试
2. 再给参数、TF、launch 补回归测试
3. 最后再考虑仿真和导航链路

## 验收门槛

### Windows 首批验收

只有下面这些包需要纳入首批通过范围：

- `msgs_demo_interfaces`
- `topic_demo`
- `service_demo`
- `action_demo`
- `param_demo`
- `name_demo`
- `tf_demo`
- `urdf_demo` 的 RViz 部分

验收标准：

- 在 Windows + Pixi 下可安装环境
- 在 `ros2_ws/` 下可构建
- 自动测试无失败
- 基础 CLI 与联调场景全部通过

### 二阶段验收

下面这些包不建议作为当前 Windows 首批 gate：

- `robot_sim_demo`
- `tf_follower`
- `navigation_sim_demo`
- `slam_sim_demo`
- `rtabmap_demo`
- `orbslam2_demo`

这些包建议在后续单独建立 Linux/WSL2 测试基线后再验收。
