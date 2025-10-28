# Knowledge Browser Enhancements

This module provides enhanced export, bulk operations, and verification features for the Knowledge Browser widget.

## Features

### 1. Export Capabilities

**KnowledgeExporter** provides multiple export formats:

- **JSON Export**: Full structured export with metadata
- **CSV Export**: Spreadsheet-compatible format
- **Backup Creation**: Timestamped automatic backups

```python
from airunner.components.knowledge.knowledge_browser_utils import KnowledgeExporter

exporter = KnowledgeExporter()

# Export all facts to JSON
count = exporter.export_to_json("knowledge.json")

# Export verified facts only
count = exporter.export_to_json("verified.json", verified_only=True)

# Export filtered by category
count = exporter.export_to_csv("tech_facts.csv", category="technology")

# Create automatic backup
backup_path = exporter.create_backup()  # Saves to ./backups/
```

### 2. Bulk Operations

**KnowledgeBulkOperations** enables batch operations:

- **Bulk Delete**: Remove multiple facts at once
- **Bulk Verify/Unverify**: Approve or reject multiple facts
- **Bulk Categorize**: Change category for multiple facts
- **Bulk Enable/Disable**: Toggle enabled status for multiple facts

```python
from airunner.components.knowledge.knowledge_browser_utils import KnowledgeBulkOperations

ops = KnowledgeBulkOperations()

# Delete multiple facts
deleted = ops.bulk_delete([1, 2, 3])

# Verify multiple facts
verified = ops.bulk_verify([4, 5, 6], verified=True)

# Change category for multiple facts
updated = ops.bulk_categorize([7, 8, 9], "general_knowledge")
```

### 3. UI Enhancements

**KnowledgeBrowserEnhancements** provides a mixin for adding features to widgets:

```python
from airunner.components.knowledge.knowledge_browser_enhancements import (
    KnowledgeBrowserEnhancements
)

class MyKnowledgeWidget(BaseWidget, KnowledgeBrowserEnhancements):
    def __init__(self):
        super().__init__()
        
        # Add export buttons to your layout
        self.add_export_buttons(self.ui.main_layout)
        
        # Add bulk operation buttons
        self.add_bulk_operation_buttons(self.ui.main_layout)
    
    def populate_table_row(self, row, fact_id):
        # Add selection checkbox
        self.add_selection_checkbox(row, fact_id)
        
        # Add quick verify/reject buttons
        self.add_quick_verify_buttons(row, fact_id)
```

## Widget Features

### Export Buttons
- **Export to JSON**: Opens file dialog for JSON export
- **Export to CSV**: Opens file dialog for CSV export
- **Create Backup**: Creates timestamped backup in `./backups/`

### Bulk Operations
- **Verify Selected**: Mark selected facts as verified
- **Unverify Selected**: Mark selected facts as unverified
- **Delete Selected**: Delete selected facts (with confirmation)

### Quick Actions
- **✓ Button**: Quick verify individual fact
- **✗ Button**: Quick reject individual fact
- **Checkboxes**: Select multiple facts for bulk operations

## Integration with Existing Widget

The enhancements are designed to work with the existing `knowledge_manager_widget.py`:

1. **Non-invasive**: Mixin pattern doesn't modify existing code
2. **Optional**: Features can be added incrementally
3. **Compatible**: Works with existing table structure and signals

### Example Integration

```python
from airunner.components.knowledge.gui.widgets.base_widget import BaseWidget
from airunner.components.knowledge.knowledge_browser_enhancements import (
    KnowledgeBrowserEnhancements
)

class EnhancedKnowledgeManagerWidget(BaseWidget, KnowledgeBrowserEnhancements):
    def initialize_form(self):
        super().initialize_form()
        
        # Add new UI elements
        self.add_export_buttons(self.ui.button_layout)
        self.add_bulk_operation_buttons(self.ui.button_layout)
    
    def _add_fact_row(self, fact, row):
        # Add selection checkbox to first column
        self.add_selection_checkbox(row, fact.id)
        
        # ... existing row population code ...
        
        # Add quick verify buttons to actions column
        self.add_quick_verify_buttons(row, fact.id)
```

## Testing

Comprehensive test suite in `tests/test_knowledge_browser_utils.py`:

```bash
# Run tests
pytest src/airunner/components/knowledge/tests/test_knowledge_browser_utils.py -v

# Test coverage
pytest src/airunner/components/knowledge/tests/test_knowledge_browser_utils.py --cov
```

Test coverage:
- ✅ 13 tests total
- ✅ Export to JSON (all facts, filtered, verified only)
- ✅ Export to CSV (all facts, filtered)
- ✅ Backup creation with timestamping
- ✅ Bulk delete, verify, categorize, enable/disable
- ✅ Edge cases (empty lists, nonexistent IDs)

## File Structure

```
src/airunner/components/knowledge/
├── knowledge_browser_utils.py           # Core export & bulk ops
├── knowledge_browser_enhancements.py    # UI integration mixin
└── tests/
    └── test_knowledge_browser_utils.py  # Comprehensive tests
```

## API Reference

### KnowledgeExporter

**Methods:**
- `export_to_json(output_path, category=None, verified_only=False) -> int`
- `export_to_csv(output_path, category=None, verified_only=False) -> int`
- `create_backup(backup_dir=None) -> str`

### KnowledgeBulkOperations

**Methods:**
- `bulk_delete(fact_ids: List[int]) -> int`
- `bulk_verify(fact_ids: List[int], verified: bool) -> int`
- `bulk_categorize(fact_ids: List[int], category: str) -> int`
- `bulk_enable_disable(fact_ids: List[int], enabled: bool) -> int`

### KnowledgeBrowserEnhancements

**Methods:**
- `add_export_buttons(layout)` - Add export UI buttons
- `add_bulk_operation_buttons(layout)` - Add bulk operation UI
- `add_selection_checkbox(row, fact_id)` - Add row checkbox
- `add_quick_verify_buttons(row, fact_id)` - Add verify/reject buttons
- `on_export_json()` - Export handler
- `on_export_csv()` - Export handler
- `on_create_backup()` - Backup handler
- `on_bulk_verify()` - Bulk verify handler
- `on_bulk_unverify()` - Bulk unverify handler
- `on_bulk_delete()` - Bulk delete handler
- `on_quick_verify(fact_id, verified)` - Quick verify handler

## Dependencies

- PySide6 (Qt widgets)
- SQLAlchemy (database operations)
- airunner.components.knowledge.data.models (KnowledgeFact model)
- airunner.components.data.session_manager (session management)

## Notes

- All database operations use session_scope() for proper transaction management
- Export functions respect enabled flag (only export enabled facts)
- Bulk operations provide proper logging and error handling
- UI enhancements include confirmation dialogs for destructive operations
- All methods have comprehensive docstrings following Google style
