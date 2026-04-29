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

## 回归策略

每迁完一个包，至少执行：

1. `pixi run build`
2. `pixi run test`
3. 该包对应的 CLI 验证
4. 至少一条跨语言联调路径

不要等所有包都迁完再统一测试。

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
