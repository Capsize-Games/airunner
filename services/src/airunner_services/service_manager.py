"""
Cross-platform service manager for AI Runner.

Handles installation, configuration, and control of AI Runner as a
background service/daemon across Linux (systemd), macOS (LaunchAgent),
and Windows (NSSM/Task Scheduler).
"""

import logging
import os
import platform
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

from airunner_native.linux_bundle_layout import build_linux_bundle_layout
from airunner_services.config.runtime_layout import (
    build_runtime_directory_layout,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _named_logger(name: str):
    """Return one concrete logger for a module or helper class."""
    get_named_logger = getattr(logger, "getLogger", None)
    if callable(get_named_logger):
        return get_named_logger(name)
    get_child = getattr(logger, "getChild", None)
    if callable(get_child):
        return get_child(name)
    return logging.getLogger(name)


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
        self.logger = _named_logger(__name__)
        self.platform = self._detect_platform()
        self.config_path = config_path or self._default_config_path()

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
        if system == "darwin":
            return ServicePlatform.MACOS
        if system == "windows":
            return ServicePlatform.WINDOWS
        self.logger.warning(f"Unknown platform: {system}")
        return ServicePlatform.UNKNOWN

    def _default_config_path(self) -> Path:
        """Get default configuration path."""
        if self.platform == ServicePlatform.WINDOWS:
            config_dir = Path(os.environ.get("APPDATA", "")) / "airunner"
            return config_dir / "daemon.yaml"
        layout = build_runtime_directory_layout()
        return layout.config_file("daemon")

    def install(self, **kwargs) -> bool:
        """Install AI Runner as a service."""
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
        """Uninstall AI Runner service."""
        if self.platform == ServicePlatform.UNKNOWN:
            self.logger.error("Cannot uninstall service on unknown platform")
            return False

        handler = self._handlers.get(self.platform)
        if not handler:
            self.logger.error(f"No handler for platform: {self.platform}")
            return False

        try:
            self.stop()
            return handler.uninstall()
        except Exception as e:
            self.logger.error(f"Failed to uninstall service: {e}")
            return False

    def start(self) -> bool:
        """Start the AI Runner service."""
        handler = self._handlers.get(self.platform)
        if not handler:
            return False

        try:
            return handler.start()
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            return False

    def stop(self) -> bool:
        """Stop the AI Runner service."""
        handler = self._handlers.get(self.platform)
        if not handler:
            return False

        try:
            return handler.stop()
        except Exception as e:
            self.logger.error(f"Failed to stop service: {e}")
            return False

    def restart(self) -> bool:
        """Restart the AI Runner service."""
        return self.stop() and self.start()

    def status(self) -> ServiceState:
        """Check service status."""
        handler = self._handlers.get(self.platform)
        if not handler:
            return ServiceState.UNKNOWN

        try:
            return handler.status()
        except Exception as e:
            self.logger.error(f"Failed to check service status: {e}")
            return ServiceState.UNKNOWN

    def is_installed(self) -> bool:
        """Check if service is installed."""
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
        self.logger = _named_logger(self.__class__.__name__)

    def install(self, config_path: Path, **kwargs) -> bool:
        raise NotImplementedError

    def uninstall(self) -> bool:
        raise NotImplementedError

    def start(self) -> bool:
        raise NotImplementedError

    def stop(self) -> bool:
        raise NotImplementedError

    def status(self) -> ServiceState:
        raise NotImplementedError

    def is_installed(self) -> bool:
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
        bundle_layout = build_linux_bundle_layout(python_executable=sys.executable)
        daemon_script = bundle_layout.daemon_executable()

        if daemon_script is None:
            daemon_cmd = (
                f"{bundle_layout.python_executable} "
                "-m airunner_services.daemon"
            )
        else:
            daemon_cmd = str(daemon_script)

        layout = build_runtime_directory_layout()
        layout.ensure_exists()
        service_content = self._generate_service_content(
            daemon_cmd,
            config_path,
            bundle_layout,
        )

        try:
            self.service_file.parent.mkdir(parents=True, exist_ok=True)
            self.service_file.write_text(service_content)
            self.logger.info(f"Created service file: {self.service_file}")

            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=True,
                capture_output=True,
            )

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

    def _generate_service_content(
        self,
        daemon_cmd: str,
        config_path: Path,
        bundle_layout=None,
    ) -> str:
        """Return the full systemd unit content for the daemon service."""
        bundle_layout = bundle_layout or build_linux_bundle_layout()
        environment = "\n".join(
            self._environment_lines(config_path, bundle_layout)
        )
        prestart = "\n".join(self._prestart_lines())
        security = "\n".join(self._security_lines())
        return f"""[Unit]
Description=AI Runner Background Service
After=network.target

[Service]
Type=simple
WorkingDirectory={bundle_layout.bundle_root}
{environment}
{prestart}
ExecStart={daemon_cmd} --config {config_path}
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
{security}

[Install]
WantedBy=default.target
"""

    def _environment_lines(self, config_path: Path, bundle_layout) -> list[str]:
        """Return environment lines for the systemd unit."""
        layout = build_runtime_directory_layout()
        environment = layout.as_environment(config_path)
        environment.update(
            {
                "AIRUNNER_BUNDLE_ROOT": str(bundle_layout.bundle_root),
                "AIRUNNER_HEADLESS": "1",
                "AIRUNNER_HTTP_HOST": "127.0.0.1",
                "AIRUNNER_RUNTIME_BIND_HOST": "127.0.0.1",
                "AIRUNNER_LLM_ON": "1",
                "AIRUNNER_PYTHON": str(bundle_layout.python_executable),
                "AIRUNNER_LOG_LEVEL": "INFO",
                "QT_QPA_PLATFORM": "offscreen",
                "QT_LOGGING_RULES": "*.debug=false;qt.qpa.*=false",
                "DEV_ENV": "0",
                "PATH": bundle_layout.path_environment(),
            }
        )
        return [
            f'Environment="{key}={value}"'
            for key, value in environment.items()
        ]

    def _prestart_lines(self) -> list[str]:
        """Return directory preparation commands for the service."""
        layout = build_runtime_directory_layout()
        managed = " ".join(str(path) for path in layout._managed_paths())
        return [
            f"ExecStartPre=/bin/mkdir -p {managed}",
            f"ExecStartPre=/bin/chmod 700 {managed}",
        ]

    def _security_lines(self) -> list[str]:
        """Return conservative least-privilege systemd directives."""
        layout = build_runtime_directory_layout()
        return [
            "LimitNOFILE=65536",
            "UMask=0077",
            "NoNewPrivileges=yes",
            "PrivateTmp=yes",
            "ProtectSystem=full",
            "ProtectHome=read-only",
            f"ReadWritePaths={layout.base_path}",
            "RestrictSUIDSGID=yes",
            "LockPersonality=yes",
            "RestrictRealtime=yes",
        ]

    def uninstall(self) -> bool:
        """Uninstall systemd user service."""
        try:
            subprocess.run(
                ["systemctl", "--user", "disable", self.SERVICE_NAME],
                capture_output=True,
            )
            subprocess.run(
                ["systemctl", "--user", "stop", self.SERVICE_NAME],
                capture_output=True,
            )

            if self.service_file.exists():
                self.service_file.unlink()
                self.logger.info(f"Removed service file: {self.service_file}")

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
            if status_str == "inactive":
                return ServiceState.STOPPED
            if status_str == "failed":
                return ServiceState.FAILED
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
            daemon_cmd = [python_exe, "-m", "airunner_services.daemon"]
        else:
            daemon_cmd = [str(daemon_script)]

        daemon_cmd.extend(["--config", str(config_path)])

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
            self.plist_file.parent.mkdir(parents=True, exist_ok=True)
            self.plist_file.write_text(plist_content)
            self.logger.info(f"Created plist file: {self.plist_file}")

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
            subprocess.run(
                ["launchctl", "unload", str(self.plist_file)],
                capture_output=True,
            )

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
                if "PID" in result.stdout or '"PID" =' in result.stdout:
                    return ServiceState.RUNNING
                return ServiceState.STOPPED
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
            app_path = python_exe
            app_args = f"-m airunner_services.daemon --config {config_path}"
        else:
            app_path = str(daemon_script)
            app_args = f"--config {config_path}"

        try:
            subprocess.run(
                ["nssm", "install", self.SERVICE_NAME, app_path]
                + app_args.split(),
                check=True,
                capture_output=True,
            )

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
            subprocess.run(
                ["nssm", "stop", self.SERVICE_NAME], capture_output=True
            )
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
            if "STOPPED" in status_str or "SERVICE_STOPPED" in status_str:
                return ServiceState.STOPPED
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
            return result.returncode == 0
        except Exception:
            return False
