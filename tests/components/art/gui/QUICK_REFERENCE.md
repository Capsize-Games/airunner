# Quick Reference: Canvas Repositioning Tests

## Running Tests

```bash
# All repositioning tests
pytest tests/components/art/gui/ -v

# Single file
pytest tests/components/art/gui/test_repositioning.py -v

# Single test
pytest tests/components/art/gui/test_repositioning.py::test_viewport_resize_applies_compensation_without_changing_offset -v

# With coverage
pytest tests/components/art/gui/ --cov=src/airunner/components/art/gui/widgets/canvas --cov-report=html

# Watch mode (requires pytest-watch)
ptw tests/components/art/gui/ -- -v
```

## Test File Structure

```
tests/components/art/gui/
├── README.md                      # Full documentation
├── TEST_SUMMARY.md                # This test suite summary
├── QUICK_REFERENCE.md             # This file
├── test_repositioning.py          # Core repositioning (8 tests)
└── test_layer_repositioning.py    # Layer-specific (5 tests)
```

## Key Concepts

### Canvas Offset
- **What:** User's pan position
- **Persisted:** Yes (QSettings)
- **Changed by resize:** No ❌

### Grid Compensation Offset
- **What:** Viewport center shift tracking
- **Persisted:** No (resets on load)
- **Changed by resize:** Yes ✅

### Position Formula
```python
display_pos = absolute_pos - canvas_offset + grid_compensation_offset
```

## Common Test Patterns

### Basic Setup
```python
def test_something():
    view = CustomGraphicsView()
    active, grid, app_settings = make_settings(pos_x=100, pos_y=150)
    
    # Monkeypatch settings
    def fake_get_or_cache_settings(self, cls, eager_load=None):
        name = getattr(cls, "__name__", str(cls))
        if name == "ActiveGridSettings":
            return active
        if name == "GridSettings":
            return grid
        if name == "ApplicationSettings":
            return app_settings
        return cls()
    
    view._get_or_cache_settings = types.MethodType(
        fake_get_or_cache_settings, view
    )
    
    view.setProperty("canvas_type", "image")
    _ = view.scene
    
    # Your test code here
```

### Simulate Viewport Resize
```python
from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent

view._initialized = True
view._is_restoring_state = False

old_size = QSize(800, 600)
new_size = QSize(1000, 700)
view._last_viewport_size = old_size
view.viewport().resize(new_size)

resize_event = QResizeEvent(new_size, old_size)
view.resizeEvent(resize_event)
```

### Create Mock Layer
```python
from PySide6.QtGui import QImage
from airunner.components.art.gui.widgets.canvas.draggables.layer_image_item import LayerImageItem

qimage = QImage(512, 512, QImage.Format.Format_ARGB32)
qimage.fill(0xFF000000)

layer_item = LayerImageItem(qimage, layer_id=1)
layer_item.setPos(200, 300)

view.scene.addItem(layer_item)
view.scene._layer_items[1] = layer_item
view.scene.original_item_positions = {layer_item: QPointF(200, 300)}
```

## Debugging Tips

### Print Offsets
```python
print(f"Canvas offset: ({view.canvas_offset.x()}, {view.canvas_offset.y()})")
print(f"Grid comp: ({view._grid_compensation_offset.x()}, {view._grid_compensation_offset.y()})")
```

### Check Item Position
```python
pos = layer_item.scenePos()
print(f"Display position: ({pos.x()}, {pos.y()})")
```

### Use pytest with pdb
```bash
pytest tests/components/art/gui/test_repositioning.py::test_name --pdb
```

## Assertion Helpers

### Float Comparison
```python
# Don't do this:
assert pos.x() == expected_x  # May fail due to floating point

# Do this:
assert abs(pos.x() - expected_x) < 1.0
# or
assert int(round(pos.x())) == int(round(expected_x))
```

### Position Checking
```python
def assert_position(item, expected_x, expected_y, tolerance=1.0):
    pos = item.scenePos()
    assert abs(pos.x() - expected_x) < tolerance
    assert abs(pos.y() - expected_y) < tolerance
```

## What to Test When...

### Adding New Positioning Feature
1. Unit test the calculation
2. Integration test with view/scene
3. Test persistence (if applicable)
4. Test interaction with existing features

### Fixing Positioning Bug
1. Write failing test reproducing bug
2. Fix the code
3. Verify test passes
4. Add related edge case tests

### Refactoring Positioning Code
1. Ensure all existing tests pass
2. Add tests for new code paths
3. Run coverage to find gaps
4. Update documentation

## Test Fixtures

### `qapp` (autouse)
- Creates/reuses QApplication instance
- Required for all Qt widget tests

### `make_settings()`
- Creates mock settings objects
- Customize with kwargs
- Returns (active, grid, app_settings)

## Quick Checks

### Before Committing
```bash
# Format
black tests/components/art/gui/

# Run tests
pytest tests/components/art/gui/ -v

# Check coverage
pytest tests/components/art/gui/ --cov=src/airunner/components/art/gui/widgets/canvas --cov-report=term-missing
```

### CI Will Check
- All tests pass
- Code coverage threshold met
- No linting errors
- Tests run on all platforms

## Common Errors

### "AttributeError: 'SimpleNamespace' object has no attribute 'X'"
**Fix:** Add missing attribute to `make_settings()`:
```python
grid.missing_attribute = True
```

### "QApplication instance already exists"
**Fix:** Use the `qapp` fixture, don't create new QApplication

### "Scene has no attribute '_layer_items'"
**Fix:** Initialize before use:
```python
if not hasattr(view.scene, "_layer_items"):
    view.scene._layer_items = {}
```

### Flaky position tests
**Fix:** Use tolerance in assertions:
```python
assert abs(actual - expected) < 1.0
```

## Test Coverage Goals

### Current Coverage
- ✅ Core repositioning: 8 tests
- ✅ Layer repositioning: 5 tests
- ✅ Total: 13 tests

### Target Coverage
- [ ] 20+ tests
- [ ] >90% code coverage for repositioning modules
- [ ] Integration tests with real DB
- [ ] Performance benchmarks

## Related Files

### Source Code
- `src/airunner/components/art/gui/widgets/canvas/custom_view.py`
- `src/airunner/components/art/gui/widgets/canvas/custom_scene.py`
- `src/airunner/components/art/gui/widgets/canvas/draggables/active_grid_area.py`
- `src/airunner/components/art/gui/widgets/canvas/draggables/layer_image_item.py`

### Documentation
- `tests/components/art/README.md` - Full test documentation
- `tests/components/art/gui/TEST_SUMMARY.md` - Test suite summary
- `docs/CANVAS_DRIFT_FIX.md` - Original drift fix documentation
- `docs/CANVAS_OFFSET_DRIFT_FIX.md` - Offset drift fix documentation

## Quick Examples

### Test Canvas Offset Preservation
```python
initial_offset = QPointF(50, 75)
view.canvas_offset = initial_offset

# ... perform resize ...

assert view.canvas_offset == initial_offset  # Should not change
```

### Test Grid Compensation
```python
initial_comp = view._grid_compensation_offset

# ... perform resize ...

expected_shift = (new_width - old_width) / 2
assert view._grid_compensation_offset.x() == initial_comp.x() + expected_shift
```

### Test Layer Display Position
```python
abs_pos = QPointF(200, 300)
canvas_offset = QPointF(50, 75)

# ... set up layer and offset ...

expected_display = QPointF(
    abs_pos.x() - canvas_offset.x(),
    abs_pos.y() - canvas_offset.y()
)
assert layer_item.scenePos() == expected_display
```

## Support

For questions or issues:
1. Check README.md for detailed documentation
2. Review TEST_SUMMARY.md for overview
3. Look at existing tests for examples
4. Ask in project chat/issues
