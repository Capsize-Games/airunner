"""Build AIRunner Docker services outside the GUI package."""

from __future__ import annotations

import subprocess


def _build_docker_image(docker_compose_file: str) -> int:
    """Build the Docker image for the provided compose file."""
    try:
        subprocess.run(
            ["docker-compose", "-f", docker_compose_file, "up", "--build"],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Error building Docker image: {exc}")
        return exc.returncode or 1
    print("Docker image built successfully.")
    return 0


def dev_image() -> int:
    """Build the development Docker image."""
    return _build_docker_image("./package/docker-compose.yml")


def main() -> int:
    """CLI entry point for Docker image builds."""
    return dev_image()


if __name__ == "__main__":
    raise SystemExit(main())