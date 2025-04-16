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

cat > /tmp/mock_build.sh << 'EOF'
#!/bin/bash
mkdir -p /app/dist
echo "Mock build output: $(date)" > /app/dist/mock_build_output.txt
echo "Build completed successfully!"
EOF
chmod +x /tmp/mock_build.sh

# Copy and run the mock build
./src/airunner/bin/docker.sh --ci bash -c "cat > /app/mock_build.sh << EOF
$(cat /tmp/mock_build.sh)
EOF
chmod +x /app/mock_build.sh && /app/mock_build.sh"

if [ -f "./dist/mock_build_output.txt" ]; then
  log_result "✅ Build output is accessible from host"
else
  log_error "❌ Build output is not visible on host"
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

cat > /tmp/mini_spec.py << 'EOF'
# Simple spec for testing PyInstaller
a = Analysis(['./src/airunner/__main__.py'], pathex=[])
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz, a.scripts, [], name='mini_airunner', debug=False)
EOF

./src/airunner/bin/docker.sh --ci bash -c "pip install pyinstaller && cp /tmp/mini_spec.py /app/mini_spec.py && cd /app && python -m PyInstaller --clean mini_spec.py"

if [ -f "./dist/mini_airunner" ]; then
  log_result "✅ PyInstaller build completed successfully"
else
  log_error "❌ PyInstaller build failed"
fi

# All tests passed
log_result "======================="
log_result "🎉 All CI mode tests passed successfully! 🎉"
log_result "See full results in $TEST_LOG"

# Invoke cleanup with image removal
cleanup --remove-images