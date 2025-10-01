# Multi-Monitor Window Restoration Fixes

## Summary
Fixed issues with window and splash screen restoration on multi-monitor setups. The application now correctly restores both the splash screen and main window to the monitor where they were last closed, regardless of which monitor the application is launched from.

## Problems Solved

1. **Splash screen appearing on wrong monitor** - The splash screen now appears on the same monitor where the main window was last closed.
2. **Main window not restoring to correct monitor** - The main window now correctly restores to the monitor where it was last closed, even when maximized.
3. **Canvas offset not preserved** - Canvas position is now correctly saved and restored across sessions.
4. **State not being saved on quit** - Fixed timing issue where `save_state()` was being skipped due to `self.quitting` flag being set prematurely.

## Technical Changes

### 1. `app.py` - Splash Screen Monitor Selection
**File:** `src/airunner/app.py`

- Modified `display_splash_screen()` to load saved screen preference from QSettings
- Attempts to find the saved screen by name
- Falls back to primary screen if saved screen not found
- Passes the target screen to `SplashScreen` constructor

**Key improvement:** The splash screen now respects the saved screen preference instead of always appearing on the primary monitor.

### 2. `splash_screen.py` - Screen Positioning
**File:** `src/airunner/components/splash_screen/splash_screen.py`

- Removed full-screen-sized pixmap creation (was confusing window managers)
- Now uses the splash image at its actual size
- Uses `windowHandle().setScreen()` to reliably set the target monitor
- Centers the splash on the target screen using calculated coordinates
- Calls `move()` twice (before and after `show()`) to ensure position is respected by window managers
- Processes Qt events after showing to ensure positioning takes effect

**Key improvement:** Changed from creating a full-screen transparent pixmap to using the actual image size, which fixes window manager positioning issues in multi-monitor setups.

### 3. `main_window.py` - Window State Management
**File:** `src/airunner/components/application/gui/windows/main/main_window.py`

#### Changes to `quit()` method:
- Moved `save_state()` call BEFORE setting `self.quitting = True`
- This ensures state is actually saved on quit

#### Changes to `save_state()` method:
- Always saves window geometry and position
- Saves screen name using `screen().name()`
- Removed redundant debug logging

#### Changes to `restore_state()` method:
- Uses `windowHandle().setScreen()` to reliably set the target monitor (same technique as splash screen)
- Works for both maximized and normal window states
- Validates saved position is within target screen bounds
- Centers window if saved position is outside target screen
- Sets `_state_restored = True` BEFORE calling `showMaximized()`/`showFullScreen()` to prevent `_initialize_window()` from overriding the screen selection
- Moves window to screen's top-left corner before maximizing (Qt requirement)

**Key improvement:** Setting `_state_restored = True` before showing the window prevents the `showEvent()` → `_initialize_window()` sequence from moving the window to the primary screen.

## Technical Details

### Multi-Monitor Positioning in Qt

Qt's window positioning in multi-monitor setups requires careful handling:

1. **Screen coordinates are global** - Each monitor has x,y coordinates in a shared desktop space
2. **windowHandle().setScreen()** - The most reliable way to place a window on a specific screen
3. **Timing is critical** - Screen must be set before calling `show*()` methods
4. **Position after screen** - After setting the screen, position must be set relative to that screen's geometry
5. **State restoration flag** - Must prevent default initialization logic from overriding saved state

### Key Qt Methods Used

- `QGuiApplication.screens()` - Get list of available monitors
- `screen.name()` - Get unique identifier for a monitor (e.g., "DP-0", "DP-2")
- `screen.geometry()` - Get monitor's position and size in global coordinates
- `windowHandle().setScreen(screen)` - Assign window to a specific monitor
- `self.create()` - Ensure native window handle exists before setting screen
- `QApplication.processEvents()` - Force Qt to process pending events

## Testing

To verify the fixes work correctly:

1. **Launch app on Monitor 1** → Close → Relaunch → Should appear on Monitor 1 ✓
2. **Move to Monitor 2** → Close → Relaunch from Monitor 1 terminal → Should appear on Monitor 2 ✓
3. **Maximize on Monitor 2** → Close → Relaunch → Should maximize on Monitor 2 ✓
4. **Canvas offset** → Center canvas → Close → Relaunch → Canvas should remain centered ✓
5. **Splash screen** → Should always appear on same monitor as main window ✓

## Code Quality

- Removed all debug print statements
- Kept essential logging statements
- Followed DRY principles
- Added clear comments explaining Qt quirks
- Maintained consistent error handling
- Used appropriate log levels (debug, info, warning, exception)

## Future Considerations

- Monitor names can change between sessions (e.g., after reconnecting displays)
- Current implementation handles this gracefully by falling back to primary screen
- Could potentially add screen index fallback if name doesn't match
- Consider saving monitor serial number or other persistent identifier if available
