"""
Cross-platform service manager for AI Runner.

Handles installation, configuration, and control of AI Runner as a
background service/daemon across Linux (systemd), macOS (LaunchAgent),
and Windows (NSSM/Task Scheduler).
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Optional
from enum import Enum

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class ServicePlatform(Enum):
    """Supported platforms for service installation."""

    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


class ServiceState(Enum):
    """Service states."""

    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ServiceManager:
    """
    Manages AI Runner background service across platforms.

    Provides unified interface for:
    - Service installation/uninstallation
    - Service control (start, stop, restart)
    - Service status checking
    - Configuration management
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize service manager.

        Args:
            config_path: Path to daemon configuration file (daemon.yaml)
        """
        self.logger = logger.getLogger(__name__)
        self.platform = self._detect_platform()
        self.config_path = config_path or self._default_config_path()

        # Platform-specific handlers
        self._handlers = {
            ServicePlatform.LINUX: LinuxSystemdHandler(),
            ServicePlatform.MACOS: MacOSLaunchAgentHandler(),
            ServicePlatform.WINDOWS: WindowsServiceHandler(),
        }

    def _detect_platform(self) -> ServicePlatform:
        """Detect the current platform."""
        system = platform.system().lower()
        if system == "linux":
            return ServicePlatform.LINUX
        elif system == "darwin":
            return ServicePlatform.MACOS
        elif system == "windows":
            return ServicePlatform.WINDOWS
        else:
            self.logger.warning(f"Unknown platform: {system}")
            return ServicePlatform.UNKNOWN

    def _default_config_path(self) -> Path:
        """Get default configuration path."""
        if self.platform == ServicePlatform.WINDOWS:
            config_dir = Path(os.environ.get("APPDATA", "")) / "airunner"
        else:
            config_dir = Path.home() / ".config" / "airunner"

        return config_dir / "daemon.yaml"

    def install(self, **kwargs) -> bool:
        """
        Install AI Runner as a service.

        Args:
            **kwargs: Platform-specific installation options

        Returns:
            True if installation successful, False otherwise
        """
        if self.platform == ServicePlatform.UNKNOWN:
            self.logger.error("Cannot install service on unknown platform")
            return False

        handler = self._handlers.get(self.platform)
        if not handler:
            self.logger.error(f"No handler for platform: {self.platform}")
            return False

        try:
            return handler.install(self.config_path, **kwargs)
        except Exception as e:
            self.logger.error(f"Failed to install service: {e}")
            return False

    def uninstall(self) -> bool:
        """
        Uninstall AI Runner service.

        Returns:
            True if uninstallation successful, False otherwise
        """
        if self.platform == ServicePlatform.UNKNOWN:
            self.logger.error("Cannot uninstall service on unknown platform")
            return False

        handler = self._handlers.get(self.platform)
        if not handler:
            self.logger.error(f"No handler for platform: {self.platform}")
            return False

        try:
            # Stop service before uninstalling
            self.stop()
            return handler.uninstall()
        except Exception as e:
            self.logger.error(f"Failed to uninstall service: {e}")
            return False

    def start(self) -> bool:
        """
        Start the AI Runner service.

        Returns:
            True if service started successfully, False otherwise
        """
        handler = self._handlers.get(self.platform)
        if not handler:
            return False

        try:
            return handler.start()
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            return False

    def stop(self) -> bool:
        """
        Stop the AI Runner service.

        Returns:
            True if service stopped successfully, False otherwise
        """
        handler = self._handlers.get(self.platform)
        if not handler:
            return False

        try:
            return handler.stop()
        except Exception as e:
            self.logger.error(f"Failed to stop service: {e}")
            return False

    def restart(self) -> bool:
        """
        Restart the AI Runner service.

        Returns:
            True if service restarted successfully, False otherwise
        """
        return self.stop() and self.start()

    def status(self) -> ServiceState:
        """
        Check service status.

        Returns:
            Current service state
        """
        handler = self._handlers.get(self.platform)
        if not handler:
            return ServiceState.UNKNOWN

        try:
            return handler.status()
        except Exception as e:
            self.logger.error(f"Failed to check service status: {e}")
            return ServiceState.UNKNOWN

    def is_installed(self) -> bool:
        """
        Check if service is installed.

        Returns:
            True if service is installed, False otherwise
        """
        handler = self._handlers.get(self.platform)
        if not handler:
            return False

        try:
            return handler.is_installed()
        except Exception as e:
            self.logger.error(f"Failed to check installation status: {e}")
            return False


class ServiceHandlerBase:
    """Base class for platform-specific service handlers."""

    def __init__(self):
        self.logger = logger.getLogger(self.__class__.__name__)

    def install(self, config_path: Path, **kwargs) -> bool:
        """Install service on this platform."""
        raise NotImplementedError

    def uninstall(self) -> bool:
        """Uninstall service from this platform."""
        raise NotImplementedError

    def start(self) -> bool:
        """Start the service."""
        raise NotImplementedError

    def stop(self) -> bool:
        """Stop the service."""
        raise NotImplementedError

    def status(self) -> ServiceState:
        """Get service status."""
        raise NotImplementedError

    def is_installed(self) -> bool:
        """Check if service is installed."""
        raise NotImplementedError


class LinuxSystemdHandler(ServiceHandlerBase):
    """Handler for Linux systemd user services."""

    SERVICE_NAME = "airunner"

    def __init__(self):
        super().__init__()
        self.service_file = (
            Path.home()
            / ".config"
            / "systemd"
            / "user"
            / f"{self.SERVICE_NAME}.service"
        )

    def install(self, config_path: Path, **kwargs) -> bool:
        """Install systemd user service."""
        # Get Python executable and airunner-daemon path
        python_exe = sys.executable
        daemon_script = Path(python_exe).parent / "airunner-daemon"

        if not daemon_script.exists():
            # Fallback to module execution
            daemon_cmd = f"{python_exe} -m airunner.services.daemon"
        else:
            daemon_cmd = str(daemon_script)

        # Create service file content
        service_content = f"""[Unit]
Description=AI Runner Background Service
After=network.target

[Service]
Type=simple
ExecStart={daemon_cmd} --config {config_path}
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""

        try:
            # Create systemd user directory if it doesn't exist
            self.service_file.parent.mkdir(parents=True, exist_ok=True)

            # Write service file
            self.service_file.write_text(service_content)
            self.logger.info(f"Created service file: {self.service_file}")

            # Reload systemd daemon
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True,
                capture_output=True,
            )

            # Enable service (auto-start on login)
            if kwargs.get("enable", True):
                subprocess.run(
                    ["systemctl", "--user", "enable", self.SERVICE_NAME],
                    check=True,
                    capture_output=True,
                )
                self.logger.info(f"Enabled {self.SERVICE_NAME} service")

            return True

        except Exception as e:
            self.logger.error(f"Failed to install systemd service: {e}")
            return False

    def uninstall(self) -> bool:
        """Uninstall systemd user service."""
        try:
            # Disable and stop service
            subprocess.run(
                ["systemctl", "--user", "disable", self.SERVICE_NAME],
                capture_output=True,
            )
            subprocess.run(
                ["systemctl", "--user", "stop", self.SERVICE_NAME],
                capture_output=True,
            )

            # Remove service file
            if self.service_file.exists():
                self.service_file.unlink()
                self.logger.info(f"Removed service file: {self.service_file}")

            # Reload systemd
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"], capture_output=True
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to uninstall systemd service: {e}")
            return False

    def start(self) -> bool:
        """Start systemd service."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "start", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            return False

    def stop(self) -> bool:
        """Stop systemd service."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "stop", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Failed to stop service: {e}")
            return False

    def status(self) -> ServiceState:
        """Get systemd service status."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )

            status_str = result.stdout.strip()
            if status_str == "active":
                return ServiceState.RUNNING
            elif status_str == "inactive":
                return ServiceState.STOPPED
            elif status_str == "failed":
                return ServiceState.FAILED
            else:
                return ServiceState.UNKNOWN

        except Exception as e:
            self.logger.error(f"Failed to get service status: {e}")
            return ServiceState.UNKNOWN

    def is_installed(self) -> bool:
        """Check if systemd service is installed."""
        return self.service_file.exists()


class MacOSLaunchAgentHandler(ServiceHandlerBase):
    """Handler for macOS LaunchAgent."""

    SERVICE_NAME = "com.capsize-games.airunner"

    def __init__(self):
        super().__init__()
        self.plist_file = (
            Path.home()
            / "Library"
            / "LaunchAgents"
            / f"{self.SERVICE_NAME}.plist"
        )

    def install(self, config_path: Path, **kwargs) -> bool:
        """Install LaunchAgent plist."""
        python_exe = sys.executable
        daemon_script = Path(python_exe).parent / "airunner-daemon"

        if not daemon_script.exists():
            daemon_cmd = [python_exe, "-m", "airunner.services.daemon"]
        else:
            daemon_cmd = [str(daemon_script)]

        # Add config path
        daemon_cmd.extend(["--config", str(config_path)])

        # Create plist content
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{self.SERVICE_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        {''.join(f'<string>{arg}</string>' for arg in daemon_cmd)}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>{Path.home()}/Library/Logs/airunner.log</string>
    <key>StandardErrorPath</key>
    <string>{Path.home()}/Library/Logs/airunner.error.log</string>
</dict>
</plist>
"""

        try:
            # Create LaunchAgents directory if it doesn't exist
            self.plist_file.parent.mkdir(parents=True, exist_ok=True)

            # Write plist file
            self.plist_file.write_text(plist_content)
            self.logger.info(f"Created plist file: {self.plist_file}")

            # Load the agent
            if kwargs.get("load", True):
                subprocess.run(
                    ["launchctl", "load", str(self.plist_file)],
                    check=True,
                    capture_output=True,
                )
                self.logger.info(f"Loaded {self.SERVICE_NAME} LaunchAgent")

            return True

        except Exception as e:
            self.logger.error(f"Failed to install LaunchAgent: {e}")
            return False

    def uninstall(self) -> bool:
        """Uninstall LaunchAgent."""
        try:
            # Unload the agent
            subprocess.run(
                ["launchctl", "unload", str(self.plist_file)],
                capture_output=True,
            )

            # Remove plist file
            if self.plist_file.exists():
                self.plist_file.unlink()
                self.logger.info(f"Removed plist file: {self.plist_file}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to uninstall LaunchAgent: {e}")
            return False

    def start(self) -> bool:
        """Start LaunchAgent."""
        try:
            result = subprocess.run(
                ["launchctl", "start", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Failed to start LaunchAgent: {e}")
            return False

    def stop(self) -> bool:
        """Stop LaunchAgent."""
        try:
            result = subprocess.run(
                ["launchctl", "stop", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Failed to stop LaunchAgent: {e}")
            return False

    def status(self) -> ServiceState:
        """Get LaunchAgent status."""
        try:
            result = subprocess.run(
                ["launchctl", "list", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                # Check if PID is present in output
                if "PID" in result.stdout or '"PID" =' in result.stdout:
                    return ServiceState.RUNNING
                else:
                    return ServiceState.STOPPED
            else:
                return ServiceState.UNKNOWN

        except Exception as e:
            self.logger.error(f"Failed to get LaunchAgent status: {e}")
            return ServiceState.UNKNOWN

    def is_installed(self) -> bool:
        """Check if LaunchAgent is installed."""
        return self.plist_file.exists()


class WindowsServiceHandler(ServiceHandlerBase):
    """Handler for Windows services using NSSM."""

    SERVICE_NAME = "AIRunner"

    def install(self, config_path: Path, **kwargs) -> bool:
        """Install Windows service using NSSM."""
        # Check if NSSM is installed
        try:
            subprocess.run(
                ["nssm", "version"], capture_output=True, check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.error(
                "NSSM not found. Please install NSSM from https://nssm.cc/"
            )
            return False

        python_exe = sys.executable
        daemon_script = Path(python_exe).parent / "airunner-daemon.exe"

        if not daemon_script.exists():
            # Use Python module execution
            app_path = python_exe
            app_args = f"-m airunner.services.daemon --config {config_path}"
        else:
            app_path = str(daemon_script)
            app_args = f"--config {config_path}"

        try:
            # Install service
            subprocess.run(
                ["nssm", "install", self.SERVICE_NAME, app_path]
                + app_args.split(),
                check=True,
                capture_output=True,
            )

            # Set service description
            subprocess.run(
                [
                    "nssm",
                    "set",
                    self.SERVICE_NAME,
                    "Description",
                    "AI Runner Background Service",
                ],
                capture_output=True,
            )

            # Set startup type to automatic
            subprocess.run(
                [
                    "nssm",
                    "set",
                    self.SERVICE_NAME,
                    "Start",
                    "SERVICE_AUTO_START",
                ],
                capture_output=True,
            )

            self.logger.info(f"Installed {self.SERVICE_NAME} Windows service")
            return True

        except Exception as e:
            self.logger.error(f"Failed to install Windows service: {e}")
            return False

    def uninstall(self) -> bool:
        """Uninstall Windows service."""
        try:
            # Stop service first
            subprocess.run(
                ["nssm", "stop", self.SERVICE_NAME], capture_output=True
            )

            # Remove service
            subprocess.run(
                ["nssm", "remove", self.SERVICE_NAME, "confirm"],
                check=True,
                capture_output=True,
            )

            self.logger.info(
                f"Uninstalled {self.SERVICE_NAME} Windows service"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to uninstall Windows service: {e}")
            return False

    def start(self) -> bool:
        """Start Windows service."""
        try:
            result = subprocess.run(
                ["nssm", "start", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            return False

    def stop(self) -> bool:
        """Stop Windows service."""
        try:
            result = subprocess.run(
                ["nssm", "stop", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Failed to stop service: {e}")
            return False

    def status(self) -> ServiceState:
        """Get Windows service status."""
        try:
            result = subprocess.run(
                ["nssm", "status", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )

            status_str = result.stdout.strip().upper()
            if "RUNNING" in status_str or "SERVICE_RUNNING" in status_str:
                return ServiceState.RUNNING
            elif "STOPPED" in status_str or "SERVICE_STOPPED" in status_str:
                return ServiceState.STOPPED
            else:
                return ServiceState.UNKNOWN

        except Exception as e:
            self.logger.error(f"Failed to get service status: {e}")
            return ServiceState.UNKNOWN

    def is_installed(self) -> bool:
        """Check if Windows service is installed."""
        try:
            result = subprocess.run(
                ["nssm", "status", self.SERVICE_NAME],
                capture_output=True,
                text=True,
            )
            # If status command succeeds, service is installed
            return result.returncode == 0
        except Exception:
            return False
