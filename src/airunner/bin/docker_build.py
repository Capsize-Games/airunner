import subprocess


def _build_docker_image(docker_compose_file: str):
    """
    Build the docker image.
    """
    try:
        # Build the Docker image
        subprocess.run(
            [
                "docker-compose",
                "-f",
                docker_compose_file,
                "up",
                "--build",
            ],
            check=True,
        )
        print("Docker image built successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error building Docker image: {e}")


def dev_image():
    """
    Main function to build the docker image.
    """
    _build_docker_image("./package/docker-compose.yml")
