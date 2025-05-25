# NodeGraphQt Vendor Module

This directory contains the NodeGraphQt vendor code, which provides the core node graph and custom QGraphicsView functionality for AI Runner's visual programming and workflow canvas features.

## Purpose
- Implements the node graph view, node item rendering, and interaction logic.
- Handles zooming, panning, and node arrangement for the visual workflow editor.
- Integrates with AI Runner's main application via custom widgets and API hooks.

## Key Components
- `widgets/viewer.py`: Main QGraphicsView subclass (`NodeViewer`) for node graph display and interaction. Handles zoom, pan, and event overrides.
- `widgets/debounced_viewer.py`: Extension of `NodeViewer` with debounced signal emission for zoom/pan events.
- `base/graph.py`: Node graph data structure and API for managing nodes, edges, and view state.

## Recent Bug Fixes
- **May 2025:** Fixed bug #1638: Resizing the panel no longer changes the zoom level. The `resizeEvent` in `widgets/viewer.py` was updated to preserve the zoom on resize, ensuring a stable user experience when adjusting panel sizes.

## Usage
This module is used internally by AI Runner. Direct modification is discouraged except for vendor bug fixes or integration patches. For upstream changes, coordinate with the AI Runner maintainers.

---
For more details, see the main project documentation or contact the AI Runner development team.
