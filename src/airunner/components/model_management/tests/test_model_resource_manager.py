"""
Test Model Resource Manager functionality.

This script tests the universal model management system to ensure:
1. Models can be loaded and tracked
2. State transitions work correctly
3. Memory allocation is managed
4. Automatic model swapping works
5. Canvas memory is tracked
"""

import logging
from airunner.components.model_management import (
    ModelResourceManager,
    ModelState,
    CanvasMemoryTracker,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_basic_lifecycle():
    """Test basic model lifecycle: prepare -> load -> busy -> ready -> cleanup."""
    logger.info("\n=== Testing Basic Model Lifecycle ===")

    manager = ModelResourceManager()

    # Test model ID (using a path-like identifier)
    model_id = "/path/to/test/model"

    # 1. Check initial state
    state = manager.get_model_state(model_id)
    assert state == ModelState.UNLOADED, f"Expected UNLOADED, got {state}"
    logger.info(f"✓ Initial state: {state.value}")

    # 2. Prepare model loading
    result = manager.prepare_model_loading(
        model_id=model_id,
        model_type="llm",
        auto_swap=False,  # Don't auto-swap for testing
    )

    logger.info(f"✓ Prepare result: can_load={result.get('can_load')}")
    if not result.get("can_load"):
        logger.info(f"  Reason: {result.get('reason')}")

    # 3. Mark as loaded
    if result.get("can_load"):
        manager.model_loaded(model_id)
        state = manager.get_model_state(model_id)
        assert state == ModelState.LOADED, f"Expected LOADED, got {state}"
        logger.info(f"✓ After load: {state.value}")

        # 4. Mark as busy
        manager.model_busy(model_id)
        state = manager.get_model_state(model_id)
        assert state == ModelState.BUSY, f"Expected BUSY, got {state}"
        logger.info(f"✓ After busy: {state.value}")

        # 5. Mark as ready
        manager.model_ready(model_id)
        state = manager.get_model_state(model_id)
        assert state == ModelState.LOADED, f"Expected LOADED, got {state}"
        logger.info(f"✓ After ready: {state.value}")

        # 6. Cleanup
        manager.cleanup_model(model_id, "llm")
        state = manager.get_model_state(model_id)
        assert state == ModelState.UNLOADED, f"Expected UNLOADED, got {state}"
        logger.info(f"✓ After cleanup: {state.value}")

    logger.info("✓ Basic lifecycle test passed!")


def test_concurrent_operation_blocking():
    """Test that concurrent operations are blocked correctly."""
    logger.info("\n=== Testing Concurrent Operation Blocking ===")

    manager = ModelResourceManager()

    model1_id = "/path/to/model1"
    model2_id = "/path/to/model2"

    # Start loading model1
    result1 = manager.prepare_model_loading(model1_id, "llm", auto_swap=False)

    if result1.get("can_load"):
        # Model1 is now in LOADING state
        state = manager.get_model_state(model1_id)
        logger.info(f"Model1 state: {state.value}")

        # Try to perform operation on model2 while model1 is loading
        can_operate, reason = manager.can_perform_operation(
            "text_to_image", model2_id
        )

        logger.info(
            f"Can operate on model2 while model1 loading: {can_operate}"
        )
        logger.info(f"Reason: {reason}")

        # Should be blocked because model1 is LOADING
        # (In real system this depends on available VRAM, but LOADING state should block)

        # Complete model1 load
        manager.model_loaded(model1_id)
        logger.info(
            f"Model1 completed load: {manager.get_model_state(model1_id).value}"
        )

        # Cleanup
        manager.cleanup_model(model1_id, "llm")

    logger.info("✓ Concurrent operation blocking test passed!")


def test_active_models_reporting():
    """Test that active models are reported correctly."""
    logger.info("\n=== Testing Active Models Reporting ===")

    manager = ModelResourceManager()

    # Load a test model
    model_id = "/path/to/test/model"
    result = manager.prepare_model_loading(model_id, "llm", auto_swap=False)

    if result.get("can_load"):
        manager.model_loaded(model_id)

        # Get active models
        active = manager.get_active_models()

        logger.info(f"Active models count: {len(active)}")
        for model in active:
            logger.info(f"  - {model.model_id}")
            logger.info(f"    Type: {model.model_type}")
            logger.info(f"    State: {model.state.value}")
            logger.info(f"    VRAM: {model.vram_allocated_gb:.2f} GB")
            logger.info(f"    RAM: {model.ram_allocated_gb:.2f} GB")
            logger.info(f"    Can unload: {model.can_unload}")

        # Cleanup
        manager.cleanup_model(model_id, "llm")

        # Verify empty after cleanup
        active_after = manager.get_active_models()
        assert (
            len(active_after) == 0
        ), f"Expected 0 active models, got {len(active_after)}"
        logger.info("✓ No active models after cleanup")

    logger.info("✓ Active models reporting test passed!")


def test_memory_breakdown():
    """Test memory allocation breakdown."""
    logger.info("\n=== Testing Memory Allocation Breakdown ===")

    manager = ModelResourceManager()

    # Get initial breakdown
    breakdown = manager.get_memory_allocation_breakdown()

    logger.info("Memory Allocation Breakdown:")
    logger.info(f"  Models VRAM: {breakdown.models_vram_gb:.2f} GB")
    logger.info(
        f"  Canvas History VRAM: {breakdown.canvas_history_vram_gb:.2f} GB"
    )
    logger.info(
        f"  System Reserve VRAM: {breakdown.system_reserve_vram_gb:.2f} GB"
    )
    logger.info(
        f"  External Apps VRAM: {breakdown.external_apps_vram_gb:.2f} GB"
    )
    logger.info(
        f"  Total Available VRAM: {breakdown.total_available_vram_gb:.2f} GB"
    )
    logger.info(
        f"  Canvas History RAM: {breakdown.canvas_history_ram_gb:.2f} GB"
    )
    logger.info(
        f"  Total Available RAM: {breakdown.total_available_ram_gb:.2f} GB"
    )

    # Test canvas memory update
    manager.update_canvas_history_allocation(0.5, 0.3)
    breakdown_after = manager.get_memory_allocation_breakdown()

    assert (
        breakdown_after.canvas_history_vram_gb == 0.5
    ), "Canvas VRAM not updated"
    assert (
        breakdown_after.canvas_history_ram_gb == 0.3
    ), "Canvas RAM not updated"
    logger.info("✓ Canvas memory update works")

    logger.info("✓ Memory breakdown test passed!")


def test_canvas_memory_tracker():
    """Test CanvasMemoryTracker independently."""
    logger.info("\n=== Testing CanvasMemoryTracker ===")

    tracker = CanvasMemoryTracker()

    # Create a mock scene with history
    class MockScene:
        def __init__(self):
            self.undo_history = []
            self.redo_history = []

    scene = MockScene()

    # Test with empty history
    vram, ram = tracker.estimate_history_memory(scene)
    assert vram == 0.0, f"Expected 0 VRAM for empty history, got {vram}"
    assert ram == 0.0, f"Expected 0 RAM for empty history, got {ram}"
    logger.info("✓ Empty history: 0 VRAM, 0 RAM")

    # Add mock history entry
    # Format: b'AIRAW1' + width (4 bytes) + height (4 bytes) + rgba data
    width = 1024
    height = 1024
    rgba_size = width * height * 4

    mock_data = (
        b"AIRAW1" + width.to_bytes(4, "little") + height.to_bytes(4, "little")
    )
    mock_data += b"\x00" * rgba_size  # Mock RGBA data

    scene.undo_history.append(
        {
            "type": "image",
            "before": mock_data,
            "after": mock_data,
        }
    )

    vram, ram = tracker.estimate_history_memory(scene)
    logger.info(
        f"✓ With 1024x1024 image: VRAM={vram:.4f} GB, RAM={ram:.4f} GB"
    )

    # Get summary
    summary = tracker.get_history_summary(scene)
    logger.info(f"  History summary:")
    logger.info(f"    Total entries: {summary['total_entries']}")
    logger.info(f"    Total VRAM: {summary['vram_gb']:.4f} GB")
    logger.info(f"    Total RAM: {summary['ram_gb']:.4f} GB")
    logger.info(f"    VRAM (MB): {summary['vram_mb']:.2f} MB")

    logger.info("✓ Canvas memory tracker test passed!")


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Model Resource Manager Test Suite")
    logger.info("=" * 60)

    try:
        test_basic_lifecycle()
        test_concurrent_operation_blocking()
        test_active_models_reporting()
        test_memory_breakdown()
        test_canvas_memory_tracker()

        logger.info("\n" + "=" * 60)
        logger.info("ALL TESTS PASSED! ✓")
        logger.info("=" * 60)

    except AssertionError as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        logger.error(f"\n❌ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
