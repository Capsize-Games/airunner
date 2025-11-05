#!/bin/bash
# Simple test runner - outputs to terminal AND log file

LOG_FILE="/tmp/math_test_results.log"

echo "Running MATH Level 5 tests..."
echo "Results will be saved to: $LOG_FILE"
echo ""

# Run tests with unbuffered output
cd "$(dirname "$0")"
stdbuf -oL -eL pytest src/airunner/components/eval/tests/test_math_level5.py::TestMATHLevel5::test_level5_agent_with_tools \
    -v -s \
    --timeout=300 \
    --tb=short \
    --capture=no \
    2>&1 | tee "$LOG_FILE"

echo ""
echo "Test complete. Results saved to: $LOG_FILE"
