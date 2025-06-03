from airunner.gui.widgets.base_widget import BaseWidget
from airunner.vendor.nodegraphqt import NodeBaseWidget as NodeBaseWidgetCore


class NodeBaseWidget(NodeBaseWidgetCore):
    """
    Base class for all node widgets in the NodeGraph.
    This class extends the NodeBaseWidgetCore from nodegraphqt.
    It serves as a foundation for creating custom node widgets.
    """
