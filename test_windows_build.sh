#!/bin/bash
# test_windows_build.sh
set -e
TEST_LOG="windows_build_test_results.log"
ERROR_LOG="windows_build_test_errors.log"
COMPOSE_FILE="package/windows/docker-compose.yml"
SERVICE_NAME="airunner_windows_package"
OUTPUT_DIR="./dist/airunner_windows"

# Clear previous logs
> $TEST_LOG
> $ERROR_LOG

log_result() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $TEST_LOG
}

log_error() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: $1" | tee -a $ERROR_LOG
  # Attempt cleanup before exiting
  cleanup
  exit 1
}

cleanup() {
  log_result "Cleaning up Windows build test containers and potentially images"
  # Stop and remove the specific compose service container if it exists
  docker compose -f "$COMPOSE_FILE" down --remove-orphans || log_result "No containers to remove or cleanup failed."

  # Optionally remove the builder image if requested
  if [[ "$1" == "--remove-images" ]]; then
    log_result "Removing builder image..."
    # Get the image name from the compose file (adjust if needed)
    IMAGE_NAME=$(grep 'image:' "$COMPOSE_FILE" | head -n 1 | awk '{print $2}')
    if [ -n "$IMAGE_NAME" ]; then
      docker rmi -f "$IMAGE_NAME" || log_result "Failed to remove image $IMAGE_NAME or it was not found."
    else
        log_result "Could not determine image name from compose file for removal."
    fi
  fi
  log_result "Cleanup completed"
}

build_image() {
  log_result "Building the Wine Docker image for Windows packaging"
  log_result "This may take a while due to the multi-stage build process..."
  # Adding --progress=plain to see more detailed output
  # Adding --no-cache to ensure a clean build each time
  DOCKER_BUILDKIT=1 docker compose -f "$COMPOSE_FILE" build --progress=plain --no-cache $SERVICE_NAME || log_error "Wine Docker image build failed"
  # Check if the image was built (basic check)
  IMAGE_NAME=$(grep 'image:' "$COMPOSE_FILE" | head -n 1 | awk '{print $2}')
  if docker image inspect "$IMAGE_NAME" &> /dev/null; then
      log_result "✅ Wine Docker image '$IMAGE_NAME' built successfully"
  else
      log_error "❌ Wine Docker image '$IMAGE_NAME' not found after build attempt"
  fi
}

test_wine_python() {
  log_result "Testing Wine Python installation..."
  # Simple test to verify Python and pip work
  docker compose -f "$COMPOSE_FILE" run --rm $SERVICE_NAME xvfb-run -a wine64 C:\\Python310\\python.exe -c "print('Python is working in Wine')" || log_error "Python test failed in Wine"
  log_result "✅ Python in Wine is working"
  
  # Also test PyInstaller
  docker compose -f "$COMPOSE_FILE" run --rm $SERVICE_NAME xvfb-run -a wine64 C:\\Python310\\Scripts\\pyinstaller.exe --version || log_error "PyInstaller test failed in Wine"
  log_result "✅ PyInstaller in Wine is working"
}

# Register cleanup function to run on exit (excluding the --remove-images flag initially)
trap cleanup EXIT

log_result "Starting Windows build local test"
log_result "=================================="

# Ensure the build script is executable
if [ -f "./pyinstaller/build_windows.sh" ]; then
    chmod +x ./pyinstaller/build_windows.sh
    log_result "Made build_windows.sh executable"
else
    log_error "❌ ./pyinstaller/build_windows.sh not found!"
fi

# Test 1: Build the Wine Docker image
log_result "Test 1: Building the Wine Docker image for Windows packaging"
log_result "This will take some time as it's a multi-stage build with several components"
build_image

# Test 1.5: Test if Python is working in Wine
log_result "Test 1.5: Verifying Python works in Wine"
test_wine_python

# Test 2: Run the PyInstaller build script inside the container
log_result "Test 2: Running PyInstaller build script via Wine in Docker"
# Ensure the output directory is clean before the build
log_result "Cleaning previous build output directory: $OUTPUT_DIR"
rm -rf "$OUTPUT_DIR"
mkdir -p ./dist # Ensure parent dist directory exists

docker compose -f "$COMPOSE_FILE" run --rm $SERVICE_NAME ./pyinstaller/build_windows.sh || log_error "PyInstaller build script execution failed"

# Test 3: Check for build output
log_result "Test 3: Checking for Windows build output in $OUTPUT_DIR"
if [ -d "$OUTPUT_DIR" ]; then
  # Check for a key file, e.g., the main executable
  if [ -f "$OUTPUT_DIR/airunner.exe" ]; then
    log_result "✅ Windows build output directory and airunner.exe found."
  else
    log_error "❌ Windows build output directory found, but airunner.exe is missing."
  fi
else
  log_error "❌ Windows build output directory '$OUTPUT_DIR' not found."
fi

# All tests passed
log_result "=================================="
log_result "🎉 Windows build local test completed successfully! 🎉"
log_result "Output located in $OUTPUT_DIR"
log_result "See full results in $TEST_LOG"

# Explicitly call cleanup before exiting successfully
# Pass --remove-images if you want to clean the builder image as well
# cleanup --remove-images
cleanup

# Disable trap now that we've manually cleaned up
trap - EXIT
