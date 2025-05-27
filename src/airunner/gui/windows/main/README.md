# ModelLoadBalancer

## Purpose

`ModelLoadBalancer` orchestrates the loading and unloading of AI models (LLM, TTS, STT, SD) to optimize VRAM usage and enable seamless switching between art (image generation) and non-art (text, speech) modes in AI Runner.

## Key Features
- Tracks which models are loaded/unloaded.
- Delegates actual load/unload to the appropriate worker manager(s).
- Remembers which non-art models were loaded before switching to art mode, and restores them after.
- Can be extended to use VRAM stats and model size for smarter balancing.

## API
- `switch_to_art_mode()`: Unloads all non-art models (LLM, TTS, STT) and loads Stable Diffusion.
- `switch_to_non_art_mode()`: Reloads previously unloaded non-art models.
- `get_loaded_models()`: Returns a list of currently loaded models.
- `vram_stats(device)`: Returns VRAM stats for a given device.

## Usage

Instantiate with a `WorkerManager`:

```python
from airunner.gui.windows.main.model_load_balancer import ModelLoadBalancer
balancer = ModelLoadBalancer(worker_manager, logger=logger)
```

Switch to art mode (for image generation):
```python
balancer.switch_to_art_mode()
```

Switch back to non-art mode (for LLM, TTS, STT):
```python
balancer.switch_to_non_art_mode()
```

## Extending
- To add smarter VRAM/model size balancing, extend `switch_to_art_mode` and `switch_to_non_art_mode` to use `vram_stats` and model size info.
- For more granular control, add methods for individual model types.

## Tests
See `tests/model_load_balancer/test_model_load_balancer.py` for TDD and usage examples.

---

# WorkerManager (Thread & Worker Management)

## Purpose

`WorkerManager` is responsible for robust, testable, and leak-free management of all background workers and their threads in the AI Runner application.

## Key Features
- Manages all worker/thread pairs via an internal registry (no global state).
- Uses `create_worker(..., registry=...)` to track all created workers and their QThreads.
- Provides `shutdown_workers()` to stop all workers and join all threads, ensuring a clean shutdown.
- No monkey patching or global state required for tests or production.

## Usage

```python
from airunner.gui.windows.main.worker_manager import WorkerManager
wm = WorkerManager(logger=logger)
wm.initialize_workers()
# ... use workers ...
wm.shutdown_workers()  # Ensures all threads are stopped and joined
```

## Testing
- In tests, use `WorkerManager` and call `shutdown_workers()` in teardown to guarantee no thread leaks.
- Example test:

```python
def test_shutdown_workers_stops_and_joins_all():
    workers = [DummyWorker(), DummyWorker()]
    threads = [DummyThread(), DummyThread()]
    wm = WorkerManager(logger=None)
    wm._worker_threads = list(zip(workers, threads))
    wm.shutdown_workers()
    assert not wm._worker_threads
```

## Migration Notes
- The old global `WORKERS`/`THREADS` lists in `create_worker.py` are no longer used for management.
- All thread and worker lifecycle is now managed by `WorkerManager` for reliability and testability.
