"""Image Filter node - following ImageDisplayNode pattern."""

from typing import Any, Dict, Optional
import logging

from PIL.Image import Image
from PySide6.QtWidgets import QComboBox, QWidget, QVBoxLayout
from PySide6.QtCore import QSizeF

from airunner.components.nodegraph.gui.widgets.nodes.art.base_art_node import (
    BaseArtNode,
)
from airunner.vendor.nodegraphqt import NodeBaseWidget
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.components.art.utils.image_filter_utils import (
    get_all_filter_names,
    get_filter_by_name,
    get_filter_values,
    build_filter_instance,
)
from airunner.components.art.gui.widgets.filter_parameter_widget import (
    create_filter_parameter_widgets,
)

LOG = logging.getLogger(__name__)


class FilterComboWidget(NodeBaseWidget):
    """Simple combo box widget for filter selection."""

    def __init__(self, parent=None, name="filter_combo", label="Filter"):
        super().__init__(parent, name, label)
        self.combo = QComboBox()
        self.combo.setFixedWidth(280)
        self.set_custom_widget(self.combo)
        self._value = ""
        # Increase Z value so combo dropdown appears above other widgets
        self.setZValue(self.zValue() + 10)

    def set_items(self, items):
        """Set the list of available items."""
        self.combo.blockSignals(True)
        self.combo.clear()
        for item in items:
            self.combo.addItem(str(item))
        self.combo.blockSignals(False)

    def get_value(self):
        """Get the currently selected value."""
        return self.combo.currentText()

    def set_value(self, value):
        """Set the currently selected value."""
        LOG.debug(f"FilterComboWidget.set_value called with: {value}")
        self._value = value
        idx = self.combo.findText(str(value))
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
            LOG.debug(f"Set combo index to {idx} for value: {value}")
        else:
            LOG.warning(f"Could not find value '{value}' in combo box")
        self.value_changed.emit(self._name, value)


class FilterParametersWidget(NodeBaseWidget):
    """Container widget for filter parameters."""

    def __init__(self, parent=None, name="filter_params"):
        super().__init__(parent, name, "")
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(4)
        # Set a reasonable fixed width to prevent overflow
        self.container.setFixedWidth(280)
        # Don't set fixed height - let it grow dynamically
        self.set_custom_widget(self.container)
        self.parameter_widgets = []
        self.parameter_values = {}  # Store current values

    def get_value(self):
        """Required by NodeBaseWidget - return current parameter overrides."""
        return self.parameter_values.copy()

    def set_value(self, value):
        """Required by NodeBaseWidget - set parameter values."""
        if isinstance(value, dict):
            self.parameter_values.update(value)

    def clear_parameters(self):
        """Remove all parameter widgets."""
        for widget in self.parameter_widgets:
            widget.deleteLater()
        self.parameter_widgets.clear()
        self.parameter_values.clear()

        # Reset container to minimal height when cleared
        self.container.setMinimumHeight(0)
        self.container.setMaximumHeight(
            16777215
        )  # Qt's default QWIDGETSIZE_MAX
        self.container.adjustSize()
        self.container.updateGeometry()
        self.adjustSize()
        self.updateGeometry()

    def set_parameters(self, filter_name: str):
        """Load and display parameters for the given filter."""
        print(
            f"[FilterParametersWidget] set_parameters called with: {filter_name}"
        )
        LOG.debug(f"set_parameters called with filter_name: {filter_name}")
        self.clear_parameters()

        if not filter_name:
            print("[FilterParametersWidget] No filter_name, returning")
            LOG.debug("No filter_name provided, returning early")
            # Trigger redraw to collapse the node
            if self.node and self.node.view:
                self.node.view.draw_node()
            return

        # Get filter and its values
        print(
            f"[FilterParametersWidget] Getting filter by name: {filter_name}"
        )
        imgf = get_filter_by_name(filter_name)
        if not imgf:
            print(
                f"[FilterParametersWidget] ERROR: Filter not found: {filter_name}"
            )
            LOG.warning(f"Filter not found: {filter_name}")
            return

        print(
            f"[FilterParametersWidget] Found filter: {imgf.name}, getting values..."
        )
        filter_values = get_filter_values(imgf.id)
        if not filter_values:
            print(
                f"[FilterParametersWidget] ERROR: No filter values for {filter_name}"
            )
            LOG.warning(f"No filter values found for filter: {filter_name}")
            return

        print(
            f"[FilterParametersWidget] Found {len(filter_values)} filter values"
        )
        LOG.debug(
            f"Creating parameter widgets for {len(filter_values)} values"
        )

        # Create parameter widgets
        def on_param_changed(param_name: str, value: Any):
            self.parameter_values[param_name] = value
            LOG.debug(f"Parameter changed: {param_name} = {value}")

        print(
            f"[FilterParametersWidget] Calling create_filter_parameter_widgets..."
        )
        self.parameter_widgets = create_filter_parameter_widgets(
            filter_values,
            on_value_changed=on_param_changed,
            parent=self.container,
        )

        print(
            f"[FilterParametersWidget] Created {len(self.parameter_widgets)} widgets"
        )
        LOG.debug(f"Created {len(self.parameter_widgets)} parameter widgets")

        # Add widgets to layout
        print(f"[FilterParametersWidget] Adding widgets to layout...")
        for i, widget in enumerate(self.parameter_widgets):
            print(f"  Adding widget {i}: {widget}")
            self.layout.addWidget(widget)

        # Force layout update before sizing adjustments
        self.layout.activate()

        # Initialize parameter values
        for fv in filter_values:
            if fv.value_type == "int":
                self.parameter_values[fv.name] = int(fv.value)
            elif fv.value_type == "float":
                self.parameter_values[fv.name] = float(fv.value)
            elif fv.value_type == "bool":
                self.parameter_values[fv.name] = fv.value == "True"
            else:
                self.parameter_values[fv.name] = fv.value

        print(
            f"[FilterParametersWidget] Initialized values: {self.parameter_values}"
        )
        print(f"[FilterParametersWidget] set_parameters completed")
        LOG.debug(f"Initialized parameter values: {self.parameter_values}")

        # Force layout to calculate sizes
        self.container.updateGeometry()
        self.layout.invalidate()
        self.layout.activate()

        # Calculate the proper height based on widget count and actual size hints
        widget_height = sum(
            w.sizeHint().height() for w in self.parameter_widgets
        )
        margins = self.layout.contentsMargins()
        spacing = (
            self.layout.spacing() * (len(self.parameter_widgets) - 1)
            if self.parameter_widgets
            else 0
        )
        total_height = (
            widget_height
            + margins.top()
            + margins.bottom()
            + spacing
            + 10  # Extra padding
        )

        print(
            f"[FilterParametersWidget] Calculated heights: widget={widget_height}, margins={margins.top() + margins.bottom()}, spacing={spacing}, total={total_height}"
        )

        # Set minimum height based on content
        self.container.setMinimumHeight(int(total_height))
        self.container.setMaximumHeight(
            int(total_height)
        )  # Also set max to prevent expansion

        # Update container size
        self.container.adjustSize()
        self.container.updateGeometry()

        # Update the proxy widget size
        self.adjustSize()
        self.updateGeometry()

        # Trigger node redraw to recalculate size
        if self.node and self.node.view:
            print("[FilterParametersWidget] Triggering node redraw...")
            self.node.view.draw_node()

    def get_parameter_overrides(self) -> Dict[str, Any]:
        """Get current parameter values as override dict."""
        return self.parameter_values.copy()


class ImageFilterNode(BaseArtNode):
    NODE_NAME = "Image Filter"

    _input_ports = [
        {"name": "image_response", "display_name": True},
        {"name": "image", "display_name": True},
    ]

    _output_ports = [
        {"name": "image_response", "display_name": True},
        {"name": "image", "display_name": True},
    ]

    def __init__(self) -> None:
        super().__init__()

        print("=" * 80)
        print(f"ImageFilterNode.__init__ called")
        print(f"self.view = {self.view}")
        print(f"self.view type = {type(self.view)}")
        print("=" * 80)

        LOG.info(f"ImageFilterNode.__init__ called, view={self.view}")

        # Create the combo widget for filter selection
        self.filter_widget = FilterComboWidget(self.view, name="filter_combo")
        LOG.debug("Created FilterComboWidget")

        # Create the parameters widget
        self.params_widget = FilterParametersWidget(
            self.view, name="filter_params"
        )
        LOG.debug("Created FilterParametersWidget")

        # Add widgets to the node
        LOG.debug("Adding widgets to node...")
        self.add_custom_widget(self.filter_widget)
        LOG.debug("Added filter combo widget")
        self.add_custom_widget(self.params_widget)
        LOG.debug("Added params widget")

        # Load available filters
        try:
            items = get_all_filter_names()
            print(f"Loaded {len(items)} filter names: {items}")
            LOG.info(f"Loaded {len(items)} filter names: {items}")
            self.filter_widget.set_items(items)
        except Exception as e:
            print(f"ERROR loading filters: {e}")
            LOG.exception("Failed to load filters")
            items = []

        # Connect selection changes to rebuild parameters
        self.filter_widget.combo.currentTextChanged.connect(
            self._on_filter_changed
        )
        LOG.debug("Connected filter selection signal")

        # Select first item if available
        if items:
            print(f"Setting initial filter to: {items[0]}")
            LOG.info(f"Setting initial filter to: {items[0]}")
            self.filter_widget.set_value(items[0])
            self.params_widget.set_parameters(items[0])
        else:
            print("WARNING: No filters available")
            LOG.warning("No filters available to select")

        print(f"ImageFilterNode.__init__ completed")
        print("=" * 80)
        LOG.info("ImageFilterNode.__init__ completed")

    def _on_filter_changed(self, filter_name: str) -> None:
        """Called when user selects a different filter."""
        print(f"_on_filter_changed called with: {filter_name}")
        LOG.info(f"_on_filter_changed called with: {filter_name}")
        if filter_name and self.params_widget:
            self.params_widget.set_parameters(filter_name)
            # Ensure the node redraws to fit new parameters
            if self.view:
                self.view.draw_node()
        else:
            LOG.warning(
                "_on_filter_changed called with empty filter_name or no params_widget"
            )

    def _build_filter_instance(self) -> Optional[Any]:
        """Build the actual filter instance with current parameters."""
        if not self.filter_widget:
            LOG.warning(
                "Cannot build filter instance - widgets not initialized"
            )
            return None

        filter_name = self.filter_widget.get_value()
        if not filter_name:
            return None

        try:
            # Get parameter overrides from the widgets
            overrides = self.params_widget.get_parameter_overrides()

            # Build filter using shared utility
            return build_filter_instance(filter_name, overrides)
        except Exception:
            LOG.exception("Failed to build filter instance")
            return None

    def execute(self, input_data: Dict) -> Dict:
        """Apply the selected filter to the input image."""
        image_response = self.get_input_data("image_response", input_data)
        image = self.get_input_data("image", input_data)

        filt = self._build_filter_instance()
        if filt is None:
            return {"image_response": image_response, "image": image}

        try:
            if (
                isinstance(image_response, ImageResponse)
                and image_response.images
            ):
                img = image_response.images[0]
                out = filt.filter(img)
                image_response.images[0] = out
                return {"image_response": image_response, "image": out}

            if isinstance(image, Image):
                out = filt.filter(image)
                return {"image_response": None, "image": out}
        except Exception:
            LOG.exception("Error applying filter")

        return {"image_response": image_response, "image": image}
