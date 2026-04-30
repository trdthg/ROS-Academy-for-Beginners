from pathlib import Path
import time

from ament_index_python.packages import get_package_share_directory
from controller_manager import configure_controller, list_controllers, load_controller, switch_controllers
from rcl_interfaces.srv import SetParameters
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
import yaml


def controller_states_by_name(controller_list) -> dict[str, str]:
    return {controller.name: controller.state for controller in controller_list.controller}


class Ros2ControlRunner(Node):
    def __init__(self) -> None:
        super().__init__("ros2_control_runner")
        package_share = Path(get_package_share_directory("robot_sim_demo_ros2"))
        default_config = package_share / "config" / "diff_drive_controller.yaml"

        self.declare_parameter("controller_manager", "/controller_manager")
        self.declare_parameter("controller_name", "diff_drive_base_controller")
        self.declare_parameter("controller_type", "")
        self.declare_parameter("controller_config", str(default_config))
        self.declare_parameter("bringup_timeout_sec", 20.0)
        self.declare_parameter("deactivate_controllers", Parameter.Type.STRING_ARRAY)
        self.controller_manager = str(self.get_parameter("controller_manager").value)
        self.controller_name = str(self.get_parameter("controller_name").value)
        self.controller_type = str(self.get_parameter("controller_type").value)
        self.controller_config = Path(str(self.get_parameter("controller_config").value))
        self.bringup_timeout_sec = float(self.get_parameter("bringup_timeout_sec").value)
        self.deactivate_controllers = [
            str(name) for name in self.get_parameter("deactivate_controllers").value
        ]
        self.parameter_client = self.create_client(
            SetParameters,
            f"{self.controller_manager}/set_parameters",
        )

    def wait_for_parameter_services(self, timeout_sec: float) -> None:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if self.parameter_client.wait_for_service(timeout_sec=0.5):
                return
        raise RuntimeError(f"Timed out waiting for parameter services of {self.controller_manager}")

    def wait_for_controller_services(self, timeout_sec: float) -> None:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            try:
                list_controllers(self, self.controller_manager, service_timeout=0.5, call_timeout=2.0)
                return
            except Exception:
                time.sleep(0.2)
        raise RuntimeError(f"Timed out waiting for controller services of {self.controller_manager}")

    def load_controller_parameters(self) -> list[Parameter]:
        yaml.safe_load(self.controller_config.read_text())
        parameters = [
            Parameter(
                name=f"{self.controller_name}.params_file",
                value=[str(self.controller_config)],
            )
        ]
        if self.controller_type:
            parameters.append(
                Parameter(
                    name=f"{self.controller_name}.type",
                    value=self.controller_type,
                )
            )
        return parameters

    def set_controller_parameters(self) -> None:
        request = SetParameters.Request()
        request.parameters = [
            parameter.to_parameter_msg() for parameter in self.load_controller_parameters()
        ]
        future = self.parameter_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
        response = future.result()
        if response is None:
            raise RuntimeError(f"Failed to set parameters for controller {self.controller_name}")
        failures = [result.reason for result in response.results if not result.successful]
        if failures:
            raise RuntimeError(
                f"Failed to set parameters for controller {self.controller_name}: {failures}"
            )

    def ensure_controller_loaded(self, controller_name: str) -> None:
        states = controller_states_by_name(list_controllers(self, self.controller_manager))
        if controller_name in states:
            return
        result = load_controller(self, self.controller_manager, controller_name)
        if not result.ok:
            raise RuntimeError(f"Failed to load controller {controller_name}")

    def ensure_controller_configured(self, controller_name: str) -> None:
        states = controller_states_by_name(list_controllers(self, self.controller_manager))
        if states.get(controller_name) in {"inactive", "active"}:
            return
        result = configure_controller(self, self.controller_manager, controller_name)
        if not result.ok:
            raise RuntimeError(f"Failed to configure controller {controller_name}")

    def activate_controllers(self, controller_names: list[str]) -> None:
        states = controller_states_by_name(list_controllers(self, self.controller_manager))
        to_activate = [name for name in controller_names if states.get(name) != "active"]
        if not to_activate:
            return
        result = switch_controllers(
            self,
            self.controller_manager,
            deactivate_controllers=[],
            activate_controllers=to_activate,
            strict=True,
            activate_asap=True,
            timeout=5.0,
            call_timeout=5.0,
        )
        if not result.ok:
            raise RuntimeError(f"Failed to activate controllers {to_activate}")

    def deactivate_loaded_controllers(self, controller_names: list[str]) -> None:
        states = controller_states_by_name(list_controllers(self, self.controller_manager))
        to_deactivate = [name for name in controller_names if states.get(name) == "active"]
        if not to_deactivate:
            return
        result = switch_controllers(
            self,
            self.controller_manager,
            deactivate_controllers=to_deactivate,
            activate_controllers=[],
            strict=True,
            activate_asap=True,
            timeout=5.0,
            call_timeout=5.0,
        )
        if not result.ok:
            raise RuntimeError(f"Failed to deactivate controllers {to_deactivate}")

    def bringup(self) -> None:
        self.wait_for_parameter_services(timeout_sec=15.0)
        self.wait_for_controller_services(timeout_sec=15.0)
        deadline = time.monotonic() + self.bringup_timeout_sec
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                self.set_controller_parameters()
                self.ensure_controller_loaded("joint_state_broadcaster")
                self.ensure_controller_loaded(self.controller_name)
                self.ensure_controller_configured("joint_state_broadcaster")
                self.ensure_controller_configured(self.controller_name)
                self.deactivate_loaded_controllers(self.deactivate_controllers)
                self.activate_controllers(["joint_state_broadcaster", self.controller_name])
                self.get_logger().info(f"ros2_control controllers are active: {self.controller_name}")
                print(f"ros2-control-ready:{self.controller_name}")
                return
            except Exception as error:
                last_error = error
                time.sleep(0.5)
        raise RuntimeError(
            f"Failed to bring up controller {self.controller_name} within "
            f"{self.bringup_timeout_sec} seconds: {last_error}"
        )


def main() -> None:
    rclpy.init()
    node = Ros2ControlRunner()
    try:
        node.bringup()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
