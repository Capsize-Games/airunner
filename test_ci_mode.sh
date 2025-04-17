#!/bin/bash
# test_ci_mode.sh
set -e
TEST_LOG="ci_mode_test_results.log"
ERROR_LOG="ci_mode_test_errors.log"

# Clear previous logs
> $TEST_LOG
> $ERROR_LOG

log_result() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $TEST_LOG
}

log_error() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: $1" | tee -a $ERROR_LOG
  exit 1
}

cleanup() {
  log_result "Cleaning up test containers and images"
  
  # Stop and remove any test containers
  docker ps -a | grep "airunner_.*_ci" | awk '{print $1}' | xargs -r docker rm -f
  
  # Remove test images if requested
  if [[ "$1" == "--remove-images" ]]; then
    docker images | grep "airunner.*ci" | awk '{print $1":"$2}' | xargs -r docker rmi -f
  fi
  
  log_result "Cleanup completed"
}

# Register cleanup function to run on exit
trap "cleanup" EXIT

log_result "Starting CI mode tests"
log_result "======================="

# Test 1: Build base image
log_result "Test 1: Building base image in CI mode"
./src/airunner/bin/docker.sh --ci build_base || log_error "Base image build failed"
if docker images | grep -q "linux_ci"; then
  log_result "✅ Base image successfully created"
else
  log_error "❌ Base image not found"
fi

# Test 2: Build runtime
log_result "Test 2: Building runtime in CI mode"
./src/airunner/bin/docker.sh --ci build_runtime || log_error "Runtime build failed"
if docker images | grep -q "linux_build_runtime_ci"; then
  log_result "✅ Runtime image successfully created"
else
  log_error "❌ Runtime image not found"
fi

# Test 3: Test filesystem isolation
log_result "Test 3: Testing filesystem isolation"
TEST_FILE="isolation_test_$(date +%s).txt"
TEST_CONTENT="CI test content $(date)"

./src/airunner/bin/docker.sh --ci bash -c "echo '$TEST_CONTENT' > /home/appuser/.local/share/airunner/$TEST_FILE"

if [ -f "$HOME/.local/share/airunner/$TEST_FILE" ]; then
  log_error "❌ File isolation failed - file appeared on host filesystem"
else
  log_result "✅ File isolation working correctly"
fi

# Test 4: Create a mock build to test output
log_result "Test 4: Testing package output access"

# Ensure dist directory exists on host
mkdir -p ./dist

# Clear any previous test files
rm -f ./dist/mock_build_output.txt

# Run the commands directly in the container without using a script file
./src/airunner/bin/docker.sh --ci bash -c "mkdir -p /app/dist && echo 'Mock build output: $(date)' > /app/dist/mock_build_output.txt && echo 'Build completed successfully!'"

# Check if output is accessible
if [ -f "./dist/mock_build_output.txt" ]; then
  log_result "✅ Build output is accessible from host"
else
  log_error "❌ Build output is not visible on host"
fi

# Additional isolation verification
TEST_ISOLATION_FILE="isolation_test_$(date +%s).txt"
./src/airunner/bin/docker.sh --ci bash -c "echo 'Isolation test' > /home/appuser/$TEST_ISOLATION_FILE"

if [ -f "$HOME/$TEST_ISOLATION_FILE" ]; then
  log_error "❌ Container isolation failed - isolation test file appeared on host"
else
  log_result "✅ Container isolation confirmed while build outputs are accessible"
fi

# Test 5: Verify docker-compose files
log_result "Test 5: Verifying docker-compose file structure"
for file in "./package/prod/docker-compose-ci.yml" "./package/prod/docker-compose-ci-runtime.yml" "./package/prod/docker-compose-ci-package.yml"; do
  if [ -f "$file" ]; then
    if grep -q "services:" "$file"; then
      log_result "✅ $file has correct structure"
    else
      log_error "❌ $file is missing 'services:' key"
    fi
  else
    log_error "❌ $file does not exist"
  fi
done

# Test 6: Check service naming
log_result "Test 6: Checking service naming consistency"
SERVICE_CHECKS=(
  "docker-compose-ci.yml:airunner_prod_ci"
  "docker-compose-ci-runtime.yml:airunner_build_runtime_ci" 
  "docker-compose-ci-package.yml:airunner_package_ci"
)

for check in "${SERVICE_CHECKS[@]}"; do
  IFS=':' read -ra PARTS <<< "$check"
  FILE="./package/prod/${PARTS[0]}"
  SERVICE="${PARTS[1]}"
  
  if grep -q "$SERVICE" "$FILE"; then
    log_result "✅ Service $SERVICE found in $FILE"
  else
    log_error "❌ Service $SERVICE not found in $FILE"
  fi
done

# Test 7: Test PyInstaller mini-build
log_result "Test 7: Testing minimal PyInstaller build"

# Define the spec content
MINI_SPEC_CONTENT=$(cat << 'EOF'
# Simple spec for testing PyInstaller
a = Analysis(['./src/airunner/__main__.py'], pathex=[])
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz, a.scripts, [], name='mini_airunner', debug=False)
EOF
)

./src/airunner/bin/docker.sh --ci bash -c " \
  echo 'Installing PyInstaller...' && \
  pip install pyinstaller && \
  echo 'Creating spec file in /app directory...' && \
  echo \"${MINI_SPEC_CONTENT}\" > /app/mini_airunner.spec && \
  echo 'Ensuring dist directory exists and is writable...' && \
  mkdir -p /app/dist && \
  echo 'Verifying source file path inside container...' && \
  ls -la /app/src/airunner/ && \
  echo 'Running PyInstaller...' && \
  cd /app && \
  python3 -m PyInstaller /app/mini_airunner.spec && \
  echo 'Files in dist directory:' && \
  ls -la /app/dist/ \
" || log_error "PyInstaller build command failed"

# Check for the executable with proper name matching
if [ -f "./dist/mini_airunner" ] || [ -d "./dist/mini_airunner" ]; then
  log_result "✅ PyInstaller build completed successfully"
else
  # Diagnostic - show what files were actually produced
  echo "Files found in dist directory:"
  ls -la ./dist/
  log_error "❌ PyInstaller build failed - output file 'mini_airunner' not found in ./dist"
fi

# All tests passed
log_result "======================="
log_result "🎉 All CI mode tests passed successfully! 🎉"
log_result "See full results in $TEST_LOG"

# Invoke cleanup with image removal
cleanup --remove-images