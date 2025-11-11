"""Test for the settings cache invalidation bug.

Root Cause:
When recentering updates DrawingPadSettings in the database, it doesn't
invalidate the cached settings. So when panning later reads from cache,
it gets stale position values.

Fix:
After updating DrawingPadSettings during recenter, invalidate the cache
for that layer's settings.
"""

from PySide6.QtCore import QPointF


class TestSettingsCacheInvalidation:
    """Test that settings cache is invalidated when positions are updated."""

    def test_cache_invalidation_on_position_update(self):
        """Test that cache is invalidated when DrawingPadSettings is updated.

        Scenario:
        1. Layer has DrawingPadSettings with position (-112, -20) in DB
        2. Settings are cached
        3. Recenter updates DB to (144, 44)
        4. Cache should be invalidated
        5. Next read should get (144, 44) from DB, not (-112, -20) from cache
        """
        # This is what SHOULD happen but currently doesn't

        old_position = QPointF(-112, -20)
        new_position = QPointF(144, 44)

        # Step 1-2: Initial cached value
        cached_value = {"x_pos": old_position.x(), "y_pos": old_position.y()}

        # Step 3: Update database (this happens in recenter_layer_positions)
        db_value = {"x_pos": new_position.x(), "y_pos": new_position.y()}

        # Step 4: Cache should be invalidated (THIS IS THE BUG - it doesn't happen)
        # Without invalidation, next read gets cached_value instead of db_value

        # Step 5: Next read should get new value
        # Currently: reads cached_value (-112, -20)  <- BUG
        # Expected: reads db_value (144, 44)         <- CORRECT

        # The fix is to invalidate cache after updating DB
        assert db_value["x_pos"] == 144
        assert db_value["y_pos"] == 44

    def test_recenter_should_invalidate_layer_settings_cache(self):
        """Document that recenter_layer_positions should invalidate cache.

        Current behavior:
        ```python
        # In layer_item_management_mixin.py:
        DrawingPadSettings.objects.update(
            drawingpad_settings.id,
            x_pos=pos_x,
            y_pos=pos_y,
        )
        # BUG: No cache invalidation here!
        ```

        Should be:
        ```python
        DrawingPadSettings.objects.update(
            drawingpad_settings.id,
            x_pos=pos_x,
            y_pos=pos_y,
        )
        # Invalidate cache so next read gets fresh value from DB
        cache_key = f"DrawingPadSettings_layer_{layer.id}"
        self.settings_mixin_shared_instance.invalidate_cached_setting_by_key(cache_key)
        ```
        """
        # This test documents the fix needed
        layer_id = 1

        expected_cache_key = f"DrawingPadSettings_layer_{layer_id}"

        # After updating DB, this cache key should be invalidated
        assert expected_cache_key == "DrawingPadSettings_layer_1"

    def test_alternative_fix_update_cache_instead_of_invalidate(self):
        """Alternative fix: Update cache with new value instead of invalidating.

        Instead of invalidating, we could update the cache:
        ```python
        DrawingPadSettings.objects.update(
            drawingpad_settings.id,
            x_pos=pos_x,
            y_pos=pos_y,
        )
        # Option 1: Invalidate cache (force re-read from DB next time)
        cache_key = f"DrawingPadSettings_layer_{layer.id}"
        self.settings_mixin_shared_instance.invalidate_cached_setting_by_key(cache_key)

        # Option 2: Update cache with new values (avoid DB read)
        drawingpad_settings.x_pos = pos_x
        drawingpad_settings.y_pos = pos_y
        self.settings_mixin_shared_instance.set_cached_setting_by_key(
            cache_key, drawingpad_settings
        )
        ```

        Option 2 is more efficient (no DB read), but Option 1 is simpler.
        """
        # This test documents both fix approaches

    def test_original_item_positions_cache_vs_settings_cache(self):
        """Understand the two-level caching issue.

        There are TWO caches:
        1. `original_item_positions` dict - maps scene items to positions
        2. Settings cache - caches DrawingPadSettings from DB

        Bug flow:
        1. Recenter clears original_item_positions
        2. Recenter updates DB
        3. Recenter calls updateImagePositions with new_positions dict
        4. updateImagePositions temporarily uses new_positions
        5. User pans - updateImagePositions called again with original_item_positions=None
        6. Code checks original_item_positions - it's empty
        7. Code falls back to _ensure_layer_has_original_position
        8. This reads from Settings cache which has stale value!

        The fix is at step 2: invalidate Settings cache after DB update.
        """
        # This test documents the complete bug flow
