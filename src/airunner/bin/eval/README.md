# Evaluation Testing Scripts

Simple scripts for running and testing the AI Runner evaluation system.

## Scripts

### `server.py`
Headless AI Runner server for evaluation testing.

```bash
python src/airunner/bin/eval/server.py
```

- Runs on port 8188
- Logs to `/tmp/airunner_test_server.log`
- Provides `/llm/generate` endpoint for test clients

### `run_test_server.sh`
Convenience wrapper for starting the test server.

```bash
./src/airunner/bin/eval/run_test_server.sh
```

### `run_math_tests.sh`
Run MATH Level 5 benchmark tests with clean output.

```bash
./src/airunner/bin/eval/run_math_tests.sh
```

- Outputs results to terminal and `/tmp/math_test_results.log`
- Shows problem-by-problem progress
- Displays final accuracy metrics

### `check_results.sh`
Quick results checker for completed test runs.

```bash
./src/airunner/bin/eval/check_results.sh
```

- Parses `/tmp/math_test_results.log`
- Shows summary statistics
- Lists individual problem results

## Typical Workflow

1. Start the test server:
   ```bash
   ./src/airunner/bin/eval/run_test_server.sh
   ```

2. In another terminal, run tests:
   ```bash
   ./src/airunner/bin/eval/run_math_tests.sh
   ```

3. Check results:
   ```bash
   ./src/airunner/bin/eval/check_results.sh
   ```

## Log Files

- `/tmp/airunner_test_server.log` - Server logs
- `/tmp/math_test_results.log` - Test results and output

## Requirements

- AI Runner must be installed (`pip install -e .`)
- Model must be downloaded (run `airunner-setup` first)
- Python environment must be activated
