# <center>《机器人操作系统入门》课程代码示例</center>

---

## 前言
欢迎来到中国大学 MOOC---[**《机器人操作系统入门》**](https://www.icourse163.org/)课程，本 ROS 软件包是课程的代码示例，课程中使用的例子均出自本代码包。除了代码包，课程还提供[讲义](https://sychaichangkun.gitbooks.io/ros-tutorial-icourse163/content/)，欢迎各位朋友下载、学习和分享。

本示例包含了 XBot 机器人和中科院软件博物馆仿真、ROS 通信示例程序、导航与 SLAM 功能演示，在每个软件包下都有相应的功能介绍。

![Gazebo 仿真效果](./robot_sim_demo.gif)

如果你遇到任何问题，可以在 Github 上方的 issues 栏目中提问，我们课程团队会耐心回答。本示例将**长期维护**，**不断更新**，如果你认可我们的工作，请点击右上角的**star**按钮，您的鼓励是我们的动力。


---
## 示例介绍
本仓库为 ROS 入门教程的代码示例，包括以下 ROS 软件包：

| 软件包 | 内容 |
| :--- | :----: |
| **robot_sim_demo** | 机器人仿真程序，大部分示例会用到这个软件包 |
| **topic_demo** | topic 通信，自定义 msg，包括 C++ 和 python 两个版本实现 |
| **service_demo** | service 通信，自定义 srv，分别以 C++ 和 python 两种语言实现 |
| **action_demo** | action 通信，自定义 action，C++ 和 python 两种语言实现 |
| **param_demo** | param 操作，分别以 C++ 和 python 两种语言实现 |
| **msgs_demo** | 演示 msg、srv、action 文件的格式规范 |
| **tf_demo** | tf 相关 API 操作演示，tf 示例包括 C++ 和 python 两个版本 |
| **name_demo** | 演示全局命名空间和局部命名空间下参数的提取 |
| **tf_follower** | 制作 mybot 机器人 实现 mybot 跟随 xbot 的功能 |
| **urdf_demo** |  创建机器人 urdf 模型，在 RViz 中显示  |
| **navigation_sim_demo** | 导航演示工具包，包括 AMCL, Odometry Navigation 等演示 |
| **slam_sim_demo** | 同步定位与建图演示，包括 Gmapping, Karto, Hector 等 SLAM 演示 |
| **robot_orbslam2_demo** | ORB_SLAM2 的演示 |
| **ros_academy_for_beginners** | Metapacakge 示例，依赖了本仓库所有的 pacakge |


---

## 下载和编译

1. 克隆或下载 ROS-Academy-for-Beginners 教学包到工作空间的`/src`目录下，例如 `~/catkin_ws/src`
```sh
$ cd ~/catkin_ws/src
$ git clone https://github.com/DroidAITech/ROS-Academy-for-Beginners.git
```

2. 安装教学包所需的依赖
```sh
$ cd ~/catkin_ws
$ rosdep install --from-paths src --ignore-src --rosdistro=kinetic -y
```

3. 编译并刷新环境
```sh
$ catkin_make
$ source ~/catkin_ws/devel/setup.bash
```

4. 运行示例

---
## 运行须知

1. 建议在**本地 Ubuntu 16.04**下运行仿真程序。目前 Gazebo 模拟器的**兼容性**是一大问题，在虚拟机或配置较低的电脑上可能无法运行。**如果你的显卡是 N 卡，建议安装 Ubuntu 下的显卡驱动**。

2. 运行 Gazebo 仿真程序`robot_sim_demo`前，请将 Gazebo 升级到 7.x 版本以上（**推荐 7.9 版本**）。

  查看 Gazebo 版本方法
  ```sh
  $ gazebo -v   #确认 7.0 以上，推荐 7.9
  ```

  升级方法

  ```sh
  $ sudo sh -c 'echo "deb http://packages.osrfoundation.org/gazebo/ubuntu-stable `lsb_release -cs` main" > /etc/apt/sources.list.d/gazebo-stable.list'
  $ wget http://packages.osrfoundation.org/gazebo.key -O - | sudo apt-key add -
  $ sudo apt-get update
  $ sudo apt-get install gazebo7
  ```

3. 确保所有依赖都已安装，如`gazebo_ros`, `gmapping`, `slam_karto`, `amcl`。



---
## Copyright

![Logo](./joint_logo.png)
