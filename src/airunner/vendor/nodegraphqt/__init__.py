#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
**airunner.vendor.nodegraphqt** is a node graph framework that can be implemented and re purposed
into applications that supports **PySide2**.

project: https://github.com/jchanvfx/airunner.vendor.nodegraphqt
documentation: https://jchanvfx.github.io/airunner.vendor.nodegraphqt/api/html/index.html

example code:

.. code-block:: python
    :linenos:

    from airunner.vendor.nodegraphqt import QtWidgets, NodeGraph, BaseNode


    class MyNode(BaseNode):

        __identifier__ = 'io.github.jchanvfx'
        NODE_NAME = 'My Node'

        def __init__(self):
            super(MyNode, self).__init__()
            self.add_input('foo', color=(180, 80, 0))
            self.add_output('bar')

    if __name__ == '__main__':
        app = QtWidgets.QApplication([])
        graph = NodeGraph()

        graph.register_node(BaseNode)
        graph.register_node(BackdropNode)

        backdrop = graph.create_node('airunner.vendor.nodegraphqt.nodes.Backdrop', name='Backdrop')
        node_a = graph.create_node('io.github.jchanvfx.MyNode', name='Node A')
        node_b = graph.create_node('io.github.jchanvfx.MyNode', name='Node B', color='#5b162f')

        node_a.set_input(0, node_b.output(0))

        viewer = graph.viewer()
        viewer.show()

        app.exec_()
"""

# node graph
from airunner.vendor.nodegraphqt.base.graph import NodeGraph, SubGraph
from airunner.vendor.nodegraphqt.base.menu import (
    NodesMenu,
    NodeGraphMenu,
    NodeGraphCommand,
)

# nodes & ports
from airunner.vendor.nodegraphqt.base.port import Port
from airunner.vendor.nodegraphqt.base.node import NodeObject
from airunner.vendor.nodegraphqt.nodes.base_node import BaseNode
from airunner.vendor.nodegraphqt.nodes.base_node_circle import BaseNodeCircle
from airunner.vendor.nodegraphqt.nodes.backdrop_node import BackdropNode
from airunner.vendor.nodegraphqt.nodes.group_node import GroupNode

# widgets
from airunner.vendor.nodegraphqt.widgets.node_widgets import NodeBaseWidget
from airunner.vendor.nodegraphqt.custom_widgets.nodes_tree import (
    NodesTreeWidget,
)
from airunner.vendor.nodegraphqt.custom_widgets.nodes_palette import (
    NodesPaletteWidget,
)
from airunner.vendor.nodegraphqt.custom_widgets.properties_bin.node_property_widgets import (
    NodePropEditorWidget,
    PropertiesBinWidget,
)


__all__ = [
    "BackdropNode",
    "BaseNode",
    "BaseNodeCircle",
    "GroupNode",
    "LICENSE",
    "NodeBaseWidget",
    "NodeGraph",
    "NodeGraphCommand",
    "NodeGraphMenu",
    "NodeObject",
    "NodesPaletteWidget",
    "NodePropEditorWidget",
    "NodesTreeWidget",
    "NodesMenu",
    "Port",
    "PropertiesBinWidget",
    "SubGraph",
    "VERSION",
    "constants",
    "custom_widgets",
]
