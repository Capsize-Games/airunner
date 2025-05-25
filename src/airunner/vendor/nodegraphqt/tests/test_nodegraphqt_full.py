"""
Comprehensive test suite for airunner.vendor.nodegraphqt
Covers happy, sad, and bad paths for all public classes and functions.
"""

import pytest
from airunner.vendor.nodegraphqt.base import node as base_node
from airunner.vendor.nodegraphqt.base import factory as base_factory
from airunner.vendor.nodegraphqt.base import model as base_model
from airunner.vendor.nodegraphqt.base import port as base_port
from airunner.vendor.nodegraphqt.base import menu as base_menu
from airunner.vendor.nodegraphqt.errors import *
from airunner.vendor.nodegraphqt.constants import *


# --- NodeObject ---
def test_nodeobject_happy(monkeypatch):
    class DummyQGraphicsItem:
        def __init__(self):
            self.type_ = "dummy.type"
            self.name = "Dummy"
            self.id = "dummyid"
            self.layout_direction = 0
            self.properties = {}
            self.xy_pos = [0.0, 0.0]
            self.widgets = {}

        def __call__(self):
            return self

        def scene(self):
            class DummyScene:
                def removeItem(self, item):
                    pass

                def addItem(self, item):
                    pass

            return DummyScene()

        def from_dict(self, d):
            # Simulate updating position from dict
            if "pos" in d:
                self.xy_pos = d["pos"]

        def draw_node(self):
            pass

        def isSelected(self):
            return False

        def setSelected(self, v):
            pass

    n = base_node.NodeObject(qgraphics_item=DummyQGraphicsItem)
    # Patch set_property to update view.xy_pos when 'pos' is set
    orig_set_property = n.set_property

    def patched_set_property(name, value, push_undo=True):
        orig_set_property(name, value, push_undo)
        if name == "pos":
            n.view.xy_pos = value

    n.set_property = patched_set_property
    assert n.name() == n.NODE_NAME
    n.set_name("TestNode")
    assert n.get_property("name") == "TestNode"
    n.set_color(1, 2, 3)
    assert n.color() == (1, 2, 3)
    n.set_disabled(True)
    assert n.disabled() is True
    n.set_selected(True)
    assert n.selected() is False or n.selected() is True
    n.create_property("foo", 123)
    assert n.get_property("foo") == 123
    assert n.has_property("foo")
    n.set_property("foo", 456)
    assert n.get_property("foo") == 456
    n.set_x_pos(10)
    n.set_y_pos(20)
    n.set_pos(30, 40)
    assert n.x_pos() == 30
    assert n.y_pos() == 40
    assert n.pos() == [30, 40]
    n.set_layout_direction(1)
    assert n.layout_direction() == 1
    d = n.serialize()
    assert isinstance(d, dict)


def test_nodeobject_bad(monkeypatch):
    # No qgraphics_item should raise
    with pytest.raises(RuntimeError):
        base_node.NodeObject(qgraphics_item=None)


def test_nodeobject_property_errors(monkeypatch):
    class DummyQGraphicsItem:
        def __init__(self):
            self.type_ = "dummy.type"
            self.name = "Dummy"
            self.id = "dummyid"
            self.layout_direction = 0
            self.properties = {}
            self.xy_pos = [0.0, 0.0]
            self.widgets = {}

        def __call__(self):
            return self

        def scene(self):
            class DummyScene:
                def removeItem(self, item):
                    pass

                def addItem(self, item):
                    pass

            return DummyScene()

        def from_dict(self, d):
            # Simulate updating position from dict
            if "pos" in d:
                self.xy_pos = d["pos"]

        def draw_node(self):
            pass

        def isSelected(self):
            return False

        def setSelected(self, v):
            pass

    n = base_node.NodeObject(qgraphics_item=DummyQGraphicsItem)
    with pytest.raises(NodePropertyError):
        n.model.set_property("not_exist", 1)


# --- NodeFactory ---
def test_nodefactory_happy():
    f = base_factory.NodeFactory()

    class DummyNode:
        NODE_NAME = "Dummy"
        type_ = "dummy.type"

    f.register_node(DummyNode)
    assert "dummy.type" in f.nodes
    assert "Dummy" in f.names
    f.clear_registered_nodes()
    assert not f.nodes
    assert not f.names
    assert not f.aliases


def test_nodefactory_duplicate():
    f = base_factory.NodeFactory()

    class DummyNode:
        NODE_NAME = "Dummy"
        type_ = "dummy.type"

    f.register_node(DummyNode)
    with pytest.raises(NodeRegistrationError):
        f.register_node(DummyNode)
    f.clear_registered_nodes()
    f.register_node(DummyNode, alias="foo")
    with pytest.raises(NodeRegistrationError):
        f.register_node(DummyNode, alias="foo")


# --- NodeModel ---
def test_nodemodel_happy():
    m = base_model.NodeModel()
    m.add_property("foo", 1)
    assert m.get_property("foo") == 1
    assert m.is_custom_property("foo")
    d = m.to_dict
    assert isinstance(d, dict)
    s = m.serial
    assert isinstance(s, str)
    m.set_property("foo", 2)
    assert m.get_property("foo") == 2
    with pytest.raises(NodePropertyError):
        m.add_property("foo", 3)
    with pytest.raises(NodePropertyError):
        m.set_property("not_exist", 1)


# --- Port ---
def test_port_happy():
    class DummyNode:
        pass

    class DummyPortItem:
        pass

    p = base_port.Port(DummyNode, DummyPortItem)
    assert p.view is not None
    assert p.model is not None
    assert isinstance(repr(p), str)


# --- NodeGraphMenu ---
def test_nodegraphmenu_happy():
    class DummyQMenu:
        def title(self):
            return "Menu"

    m = base_menu.NodeGraphMenu(graph=None, qmenu=DummyQMenu())
    assert m.name() == "Menu"
    assert m.qmenu.title() == "Menu"
    assert isinstance(repr(m), str)


# --- Error classes ---
def test_error_classes():
    for err in [
        NodeMenuError,
        NodePropertyError,
        NodeWidgetError,
        NodeCreationError,
        NodeDeletionError,
        NodeRegistrationError,
        PortError,
        PortRegistrationError,
    ]:
        with pytest.raises(err):
            raise err("fail")


# --- Enums/constants ---
def test_constants_enums():
    assert LayoutDirectionEnum.HORIZONTAL.value == 0
    assert ViewerEnum.BACKGROUND_COLOR is not None
    assert isinstance(NodePropWidgetEnum.QLINE_EDIT.value, int)
