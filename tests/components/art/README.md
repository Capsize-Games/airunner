# Canvas Repositioning Tests

## Overview

This directory contains comprehensive tests for the canvas repositioning logic in AI Runner's art components. The tests verify that images, layers, and the active grid area maintain correct positions when:

- The viewport is resized (splitter panel adjustments, window resizing)
- The application loads for the first time
- The canvas is panned by the user
- The grid is recentered

## Test Coverage

### Current Test Modules

#### `test_repositioning.py`

**Purpose:** Unit and functional tests for canvas/view/scene repositioning behavior.

**Key Test Cases:**

1. **`test_update_active_grid_area_position_applies_offsets`**
   - Verifies active grid area display position calculation
   - Tests: `absolute_position - canvas_offset = display_position`

2. **`test_active_grid_area_drag_updates_settings_and_display`**
   - Simulates dragging the active grid area
   - Verifies snapping to grid and position updates

3. **`test_viewport_resize_applies_compensation_without_changing_offset`**
   - Tests viewport resize handling
   - Ensures `canvas_offset` (user pan state) is preserved
   - Verifies `grid_compensation_offset` adjusts for viewport center shift

4. **`test_resize_during_restoration_skips_compensation`**
   - Tests that resizes during initial load don't apply compensation
   - Prevents drift from viewport adjustments during startup

5. **`test_apply_viewport_compensation_updates_positions`**
   - Tests `_apply_viewport_compensation` directly
   - Verifies grid compensation and item positions update correctly

6. **`test_showEvent_loads_offset_and_preserves_it`**
   - Tests initial load sequence
   - Verifies saved `canvas_offset` is loaded and preserved
   - Ensures `grid_compensation_offset` is reset on load

7. **`test_recenter_grid_resets_offsets_and_repositions`**
   - Tests recenter functionality
   - Verifies all offsets reset to (0, 0)
   - Checks items are repositioned to centered positions

8. **`test_negligible_resize_skipped`**
   - Tests that very small resize events are ignored
   - Prevents unnecessary recalculations

9. **`test_get_recentered_position_snaps_to_grid`**
   - Tests recentering calculation with grid snapping
   - Verifies returned positions are snapped to grid

## Architecture

### Key Components Tested

- **`CustomGraphicsView`** (`custom_view.py`)
  - Viewport resize handling (`resizeEvent`)
  - Canvas offset management
  - Grid compensation offset tracking
  - Initial load sequence (`showEvent`)
  - Recenter logic

- **`CustomScene`** (`custom_scene.py`)
  - Layer image positioning
  - Item position cache management

- **`ActiveGridArea`** (`active_grid_area.py`)
  - Drag and drop with snapping
  - Position persistence

### Key Concepts

#### Canvas Offset
- Represents user's pan position
- Persisted to QSettings
- Should remain unchanged during viewport resizes

#### Grid Compensation Offset
- Tracks viewport center shifts due to resizing
- Applied to maintain visual alignment
- NOT persisted (resets on load)

#### Absolute vs. Display Position
- **Absolute Position:** Stored in database, independent of viewport
- **Display Position:** Visual position in scene = `absolute - canvas_offset + compensation`

## Running Tests

### Run all repositioning tests:
```bash
pytest tests/components/art/gui/test_repositioning.py -v
```

### Run a specific test:
```bash
pytest tests/components/art/gui/test_repositioning.py::test_viewport_resize_applies_compensation_without_changing_offset -v
```

### Run with coverage:
```bash
pytest tests/components/art/gui/test_repositioning.py --cov=src/airunner/components/art/gui/widgets/canvas --cov-report=html
```

## Test Patterns and Helpers

### `make_settings()`
Creates lightweight mock settings objects (ActiveGridSettings, GridSettings, ApplicationSettings) to avoid database access in tests.

### Settings Monkeypatching
Tests use `types.MethodType` to override `_get_or_cache_settings` to return mock settings:

```python
def fake_get_or_cache_settings(self, cls, eager_load=None):
    name = getattr(cls, "__name__", str(cls))
    if name == "ActiveGridSettings":
        return active
    # ... more mappings
    
view._get_or_cache_settings = types.MethodType(
    fake_get_or_cache_settings, view
)
```

### Event Simulation
Tests create mock Qt events:

```python
from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent

old_size = QSize(800, 600)
new_size = QSize(1000, 700)
resize_event = QResizeEvent(new_size, old_size)
view.resizeEvent(resize_event)
```

## Extending Tests

### Adding New Test Cases

To test new repositioning scenarios:

1. **Create a new test function** in `test_repositioning.py`
2. **Set up the view** with mock settings
3. **Simulate the scenario** (resize, pan, drag, etc.)
4. **Assert expected behavior**

Example template:

```python
def test_new_scenario():
    """Test description."""
    view = CustomGraphicsView()
    active, grid, app_settings = make_settings(pos_x=100, pos_y=150)
    
    # Monkeypatch settings
    def fake_get_or_cache_settings(self, cls, eager_load=None):
        # ... settings mapping
        
    view._get_or_cache_settings = types.MethodType(
        fake_get_or_cache_settings, view
    )
    
    view.setProperty("canvas_type", "image")
    _ = view.scene
    
    # Simulate scenario
    # ...
    
    # Assert expectations
    assert view.canvas_offset.x() == expected_x
```

### Testing Layer Repositioning

To add tests for layer-specific repositioning:

1. Create mock `LayerImageItem` instances
2. Add to `view.scene._layer_items`
3. Set up `DrawingPadSettings` with layer positions
4. Trigger repositioning
5. Assert layer display positions

### Testing with Real Database

For integration tests with actual DB models:

1. Create pytest fixtures with in-memory SQLite
2. Use `session_scope()` for transactions
3. Create real model instances
4. Test full persistence cycle

## Known Issues and Limitations

### Current Limitations

1. **No painter/rendering tests:** Tests verify position calculations but not actual rendering
2. **Limited layer tests:** Most tests focus on active grid area; layer repositioning needs expansion
3. **No multi-layer tests:** Tests don't cover complex layer stacking scenarios

### Future Enhancements

- [ ] Add tests for `DraggablePixmap` snap-to-grid behavior
- [ ] Test `CustomScene.update_image_position` with multiple layers
- [ ] Add integration tests with real DB models
- [ ] Test text item repositioning
- [ ] Add performance benchmarks for repositioning operations
- [ ] Test edge cases (negative coordinates, very large offsets)

## Troubleshooting

### Test Failures

**"AttributeError: 'SimpleNamespace' object has no attribute 'X'"**
- Add missing attribute to `make_settings()` mock objects
- Check if code path accesses settings property not in mock

**"QApplication instance already exists"**
- Use the `qapp` fixture which reuses existing QApplication
- Don't create new QApplication in test functions

**Flaky position assertions**
- Use `abs(actual - expected) < tolerance` for floating-point comparisons
- Round values before comparing: `int(round(value))`

### Debugging Tips

1. **Add logging:** Use `view.logger.info()` to trace execution
2. **Print intermediate values:** Check offsets at each step
3. **Run single test:** Isolate failing test with `-k` flag
4. **Use pdb:** Add `import pdb; pdb.set_trace()` for interactive debugging

## Related Documentation

- [Main README](/README.md)
- [Architecture Overview](/OVERVIEW.md)
- [Canvas Drift Fix](/docs/CANVAS_DRIFT_FIX.md)
- [Canvas Offset Drift Fix](/docs/CANVAS_OFFSET_DRIFT_FIX.md)

## Contributing

When adding new positioning features:

1. Write tests first (TDD approach recommended)
2. Test both unit behavior and integration scenarios
3. Add test documentation to this README
4. Ensure tests pass in CI environment
5. Update coverage reports

For questions or issues, consult the project's contributing guidelines.
