#!/usr/bin/env python
"""
CLI tool for managing AI Runner background service.

Usage:
    airunner-service install [--enable]
    airunner-service uninstall
    airunner-service start
    airunner-service stop
    airunner-service restart
    airunner-service status
"""

import sys
import argparse
from pathlib import Path

from airunner.services.service_manager import ServiceManager, ServiceState


def cmd_install(manager: ServiceManager, args):
    """Install AI Runner as a background service."""
    print("Installing AI Runner service...")

    if manager.is_installed():
        print("Service is already installed.")
        print(
            "Run 'airunner-service uninstall' first if you want to reinstall."
        )
        return 1

    success = manager.install(enable=args.enable)

    if success:
        print(f"✅ Service installed successfully on {manager.platform.value}")
        print(f"   Config file: {manager.config_path}")

        if args.enable:
            print("   Auto-start: enabled")

        print("\nNext steps:")
        print(
            "  1. Edit configuration (optional): airunner-daemon --generate-config"
        )
        print("  2. Start service: airunner-service start")
        print("  3. Check status: airunner-service status")
        return 0
    else:
        print("❌ Failed to install service")
        print("   Check logs for details")
        return 1


def cmd_uninstall(manager: ServiceManager, args):
    """Uninstall AI Runner service."""
    print("Uninstalling AI Runner service...")

    if not manager.is_installed():
        print("Service is not installed.")
        return 1

    success = manager.uninstall()

    if success:
        print("✅ Service uninstalled successfully")
        return 0
    else:
        print("❌ Failed to uninstall service")
        return 1


def cmd_start(manager: ServiceManager, args):
    """Start AI Runner service."""
    if not manager.is_installed():
        print("❌ Service is not installed")
        print("   Run 'airunner-service install' first")
        return 1

    print("Starting AI Runner service...")
    success = manager.start()

    if success:
        print("✅ Service started successfully")
        return 0
    else:
        print("❌ Failed to start service")
        return 1


def cmd_stop(manager: ServiceManager, args):
    """Stop AI Runner service."""
    if not manager.is_installed():
        print("❌ Service is not installed")
        return 1

    print("Stopping AI Runner service...")
    success = manager.stop()

    if success:
        print("✅ Service stopped successfully")
        return 0
    else:
        print("❌ Failed to stop service")
        return 1


def cmd_restart(manager: ServiceManager, args):
    """Restart AI Runner service."""
    if not manager.is_installed():
        print("❌ Service is not installed")
        return 1

    print("Restarting AI Runner service...")
    success = manager.restart()

    if success:
        print("✅ Service restarted successfully")
        return 0
    else:
        print("❌ Failed to restart service")
        return 1


def cmd_status(manager: ServiceManager, args):
    """Check AI Runner service status."""
    print(f"Platform: {manager.platform.value}")
    print(f"Installed: {'Yes' if manager.is_installed() else 'No'}")

    if not manager.is_installed():
        print("\nRun 'airunner-service install' to install the service.")
        return 0

    status = manager.status()
    status_symbols = {
        ServiceState.RUNNING: "✅",
        ServiceState.STOPPED: "⏹️",
        ServiceState.FAILED: "❌",
        ServiceState.UNKNOWN: "❓",
    }

    symbol = status_symbols.get(status, "❓")
    print(f"Status: {symbol} {status.value.upper()}")

    # Show config path
    print(f"Config: {manager.config_path}")

    # Show service details based on platform
    if manager.platform.value == "linux":
        print("\nView logs with:")
        print("  journalctl --user -u airunner -f")
    elif manager.platform.value == "macos":
        log_path = Path.home() / "Library/Logs/airunner.log"
        print(f"\nLogs: {log_path}")

    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage AI Runner background service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  airunner-service install --enable    # Install and enable auto-start
  airunner-service start               # Start the service
  airunner-service status              # Check service status
  airunner-service stop                # Stop the service
  airunner-service restart             # Restart the service
  airunner-service uninstall           # Uninstall the service
        """,
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Command to execute"
    )

    # install command
    install_parser = subparsers.add_parser("install", help="Install service")
    install_parser.add_argument(
        "--enable",
        action="store_true",
        default=True,
        help="Enable auto-start on boot/login (default: True)",
    )
    install_parser.add_argument(
        "--config", type=Path, help="Path to daemon configuration file"
    )

    # uninstall command
    subparsers.add_parser("uninstall", help="Uninstall service")

    # start command
    subparsers.add_parser("start", help="Start service")

    # stop command
    subparsers.add_parser("stop", help="Stop service")

    # restart command
    subparsers.add_parser("restart", help="Restart service")

    # status command
    subparsers.add_parser("status", help="Check service status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Create service manager
    config_path = getattr(args, "config", None)
    manager = ServiceManager(config_path=config_path)

    # Execute command
    commands = {
        "install": cmd_install,
        "uninstall": cmd_uninstall,
        "start": cmd_start,
        "stop": cmd_stop,
        "restart": cmd_restart,
        "status": cmd_status,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        return cmd_func(manager, args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
