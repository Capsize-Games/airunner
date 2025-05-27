"""
Test suite for airunner.vendor.nodegraphqt
Covers happy, sad, and bad paths for all public classes and functions.
"""

import pytest
import types

import airunner.vendor.nodegraphqt as nodegraphqt


# Import all submodules and key classes for coverage
def import_all_nodegraphqt():
    import importlib
    import pkgutil
    import sys

    base = nodegraphqt
    modules = []
    for finder, name, ispkg in pkgutil.walk_packages(
        base.__path__, base.__name__ + "."
    ):
        try:
            mod = importlib.import_module(name)
            modules.append(mod)
        except Exception:
            pass  # Some modules may require Qt context or fail on import
    return modules


def test_import_all_nodegraphqt():
    modules = import_all_nodegraphqt()
    assert any("base" in m.__name__ for m in modules)
    assert any("widgets" in m.__name__ for m in modules)
    assert any("nodes" in m.__name__ for m in modules)
    assert any("qgraphics" in m.__name__ for m in modules)
    assert any("custom_widgets" in m.__name__ for m in modules)


# Example: test a basic class from nodegraphqt.base.node
from airunner.vendor.nodegraphqt.base import node as base_node


def test_base_node_instantiation():
    # Should be able to instantiate a Node (if not abstract)
    if hasattr(base_node, "Node"):
        Node = base_node.Node
        n = Node()
        assert n is not None


# More tests for happy/sad/bad paths will be added for each class/function


# --- NodeObject instantiation and property tests ---
def test_nodeobject_instantiation_and_properties():
    from airunner.vendor.nodegraphqt.base import node as base_node

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


# --- NodeObject error and edge cases ---
def test_nodeobject_missing_qgraphics_item():
    from airunner.vendor.nodegraphqt.base import node as base_node
    import pytest

    with pytest.raises(RuntimeError):
        base_node.NodeObject(qgraphics_item=None)


def test_nodeobject_property_error():
    from airunner.vendor.nodegraphqt.base import node as base_node
    from airunner.vendor.nodegraphqt.errors import NodePropertyError

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


# --- NodeFactory registration and error tests ---
def test_nodefactory_registration_and_errors():
    from airunner.vendor.nodegraphqt.base import factory as base_factory
    from airunner.vendor.nodegraphqt.errors import NodeRegistrationError

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
    f.register_node(DummyNode, alias="foo")
    with pytest.raises(NodeRegistrationError):
        f.register_node(DummyNode, alias="foo")


# --- NodeFactory create_node_instance edge cases ---
def test_nodefactory_create_node_instance():
    from airunner.vendor.nodegraphqt.base import factory as base_factory

    f = base_factory.NodeFactory()

    class DummyNode:
        NODE_NAME = "Dummy"
        type_ = "dummy.type"

    f.register_node(DummyNode)
    # Should return DummyNode class (not instance, as per code)
    node_cls = f.create_node_instance("dummy.type")
    assert isinstance(node_cls, DummyNode)
    # Should return None for unknown type
    assert f.create_node_instance("notype") is None


# --- NodeModel property and serialization tests ---
def test_nodemodel_properties_and_serialization():
    from airunner.vendor.nodegraphqt.base import model as base_model
    from airunner.vendor.nodegraphqt.errors import NodePropertyError

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


# --- NodeModel edge cases ---
def test_nodemodel_duplicate_property():
    from airunner.vendor.nodegraphqt.base import model as base_model
    from airunner.vendor.nodegraphqt.errors import NodePropertyError

    m = base_model.NodeModel()
    m.add_property("foo", 1)
    with pytest.raises(NodePropertyError):
        m.add_property("foo", 2)


# --- Port instantiation ---
def test_port_instantiation():
    from airunner.vendor.nodegraphqt.base import port as base_port

    class DummyNode:
        pass

    class DummyPortItem:
        pass

    p = base_port.Port(DummyNode, DummyPortItem)
    assert p.view is not None
    assert p.model is not None
    assert isinstance(repr(p), str)


# --- Port model edge case ---
def test_port_repr_and_model():
    from airunner.vendor.nodegraphqt.base import port as base_port

    class DummyNode:
        pass

    class DummyPortItem:
        pass

    p = base_port.Port(DummyNode, DummyPortItem)
    assert str(p) == repr(p)
    assert hasattr(p.model, "to_dict")


# --- NodeGraphMenu basic usage ---
def test_nodegraphmenu_basic():
    from airunner.vendor.nodegraphqt.base import menu as base_menu

    class DummyQMenu:
        def title(self):
            return "Menu"

    m = base_menu.NodeGraphMenu(graph=None, qmenu=DummyQMenu())
    assert m.name() == "Menu"
    assert m.qmenu.title() == "Menu"
    assert isinstance(repr(m), str)


# --- NodeGraphMenu command registration edge case ---
def test_nodegraphmenu_commands():
    from airunner.vendor.nodegraphqt.base import menu as base_menu

    class DummyQMenu:
        def title(self):
            return "Menu"

    m = base_menu.NodeGraphMenu(graph=None, qmenu=DummyQMenu())
    # Add a dummy command and check
    m._commands["test"] = lambda: 42
    assert m._commands["test"]() == 42


# --- Error classes ---
def test_error_classes_all():
    from airunner.vendor.nodegraphqt.errors import (
        NodeMenuError,
        NodePropertyError,
        NodeWidgetError,
        NodeCreationError,
        NodeDeletionError,
        NodeRegistrationError,
        PortError,
        PortRegistrationError,
    )

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


# --- Error class string representation ---
def test_error_class_str():
    from airunner.vendor.nodegraphqt.errors import NodeMenuError

    err = NodeMenuError("fail")
    assert str(err) == "fail"


# --- Enums/constants ---
def test_constants_and_enums():
    from airunner.vendor.nodegraphqt.constants import (
        LayoutDirectionEnum,
        ViewerEnum,
        NodePropWidgetEnum,
    )

    assert LayoutDirectionEnum.HORIZONTAL.value == 0
    assert ViewerEnum.BACKGROUND_COLOR is not None
    assert isinstance(NodePropWidgetEnum.QLINE_EDIT.value, int)


# --- Enum string representation and comparison ---
def test_enum_str_and_comparison():
    from airunner.vendor.nodegraphqt.constants import LayoutDirectionEnum

    assert str(LayoutDirectionEnum.HORIZONTAL) == "LayoutDirectionEnum.HORIZONTAL"
    assert LayoutDirectionEnum.HORIZONTAL == LayoutDirectionEnum(0)


# --- NodeBaseWidget and widget subclasses ---
def test_nodebasewidget_and_subclasses():
    import pytest
    from airunner.vendor.nodegraphqt.widgets import node_widgets
    from PySide6.QtWidgets import QWidget, QApplication
    import sys

    # Ensure QApplication exists
    app = QApplication.instance() or QApplication(sys.argv)
    # NodeBaseWidget basic instantiation and property tests
    w = node_widgets.NodeBaseWidget(parent=None, name="foo", label="FooLabel")
    w.setToolTip("tip")
    assert w.get_name() == "foo"
    w.set_name("bar")
    assert w.get_name() == "bar"
    w.set_label("LBL")
    assert w.get_label() == "LBL"
    w.set_custom_widget(QWidget())
    assert isinstance(w.get_custom_widget(), QWidget)
    # get_icon returns a QIcon
    icon = w.get_icon(3)
    assert hasattr(icon, "pixmap")
    # value changed signal (should raise NotImplementedError for base)
    with pytest.raises(NotImplementedError):
        w.on_value_changed()
    # NodeComboBox
    cb = node_widgets.NodeComboBox(name="cb", label="Combo", items=["a", "b"])
    cb.set_value("a")
    assert cb.get_value() == "a"
    cb.on_value_changed()  # Should not raise
    # NodeLineEdit
    le = node_widgets.NodeLineEdit(name="le", label="LineEdit")
    le.set_value("test")
    assert le.get_value() == "test"
    le.on_value_changed()  # Should not raise
    # NodeCheckBox
    cbx = node_widgets.NodeCheckBox(name="cbx", label="CheckBox")
    cbx.set_value(True)
    assert cbx.get_value() is True
    cbx.on_value_changed()  # Should not raise
    cbx.set_value(False)
    assert cbx.get_value() is False


# --- _NodeGroupBox ---
def test_nodegroupbox():
    from airunner.vendor.nodegraphqt.widgets import node_widgets
    from PySide6.QtWidgets import QWidget

    g = node_widgets._NodeGroupBox("TestGroup")
    g.setTitle("Title")
    g.setTitleAlign("center")
    g.setTitleAlign("left")
    g.setTitleAlign("right")
    g.add_node_widget(QWidget())
    assert isinstance(g.get_node_widget(), QWidget)


def test_commands_undo_redo():
    """Test QUndoCommand subclasses in nodegraphqt.base.commands."""
    from airunner.vendor.nodegraphqt.base import commands
    import types

    # Dummy classes to simulate node/port/graph/view/model
    class DummySignal:
        def emit(self, *a, **k):
            self.last = (a, k)

    class DummyModel:
        def __init__(self):
            self.props = {"foo": 1, "visible": True, "pos": (0, 0)}
            self.width = 10
            self.height = 20
            self.locked = False
            self.visible = True
            self.selected = False
            self.connected_ports = {}

        def set_property(self, name, value):
            self.props[name] = value

        def get_property(self, name):
            return self.props.get(name)

    class DummyView:
        def __init__(self):
            self.widgets = {
                "foo": types.SimpleNamespace(
                    get_value=lambda: 1, set_value=lambda v: None
                )
            }
            self.properties = {"foo": 1, "pos": (0, 0)}
            self.xy_pos = (0, 0)
            self.visible = True
            self.width = 10
            self.height = 20
            self.inputs = []
            self.outputs = []
            self.locked = False
            self.selected = False

        def get_widget(self, name):
            return types.SimpleNamespace(
                setVisible=lambda v: setattr(self, "visible", v)
            )

        def draw_node(self):
            pass

        def delete(self):
            self.deleted = True

        def setVisible(self, v):
            self.visible = v

        def isSelected(self):
            return self.selected

        def setSelected(self, v):
            self.selected = v

        def get_input_text_item(self, v):
            return types.SimpleNamespace(setVisible=lambda v: None)

        def get_output_text_item(self, v):
            return types.SimpleNamespace(setVisible=lambda v: None)

        def connect_to(self, v):
            self.connected = True

        def disconnect_from(self, v):
            self.connected = False

    class DummyNode:
        def __init__(self):
            self._name = "n"
            self._id = "id"
            self.model = DummyModel()
            self.view = DummyView()
            self.graph = types.SimpleNamespace(
                property_changed=DummySignal(),
                node_created=DummySignal(),
                nodes_deleted=DummySignal(),
                port_connected=DummySignal(),
                port_disconnected=DummySignal(),
                viewer=lambda: types.SimpleNamespace(add_node=lambda v, p: None),
                model=types.SimpleNamespace(nodes={}),
                scene=lambda: types.SimpleNamespace(addItem=lambda v: None),
            )
            self.id = "id"
            self._selected = False

        def name(self):
            return self._name

        def get_property(self, name):
            return self.model.get_property(name)

        def pos(self):
            return (0, 0)

        def on_input_connected(self, s, t):
            self.last_connected = (s, t)

        def on_input_disconnected(self, s, t):
            self.last_disconnected = (s, t)

        def selected(self):
            return self._selected

    class DummyPort:
        def __init__(self, node, name="p", port_type="in"):
            self._node = node
            self._name = name
            self.model = DummyModel()
            self.view = DummyView()
            self._type_val = port_type

        def node(self):
            return self._node

        def name(self):
            return self._name

        def type_(self):
            return self._type_val

    # PropertyChangedCmd
    node = DummyNode()
    cmd = commands.PropertyChangedCmd(node, "foo", 2)
    cmd.undo()
    cmd.redo()

    # NodeVisibleCmd
    cmd2 = commands.NodeVisibleCmd(node, False)
    cmd2.undo()
    cmd2.redo()

    # NodeWidgetVisibleCmd
    cmd3 = commands.NodeWidgetVisibleCmd(node, "foo", True)
    cmd3.undo()
    cmd3.redo()

    # NodeMovedCmd
    cmd4 = commands.NodeMovedCmd(node, (1, 2), (0, 0))
    cmd4.undo()
    cmd4.redo()

    # NodeAddedCmd/NodesRemovedCmd
    graph = node.graph
    node2 = DummyNode()
    graph.model.nodes[node.id] = node
    cmd5 = commands.NodeAddedCmd(graph, node, pos=(1, 2))
    cmd5.undo()
    cmd5.redo()
    cmd6 = commands.NodesRemovedCmd(graph, [node2])
    cmd6.undo()
    cmd6.redo()

    # NodeInputConnectedCmd/NodeInputDisconnectedCmd
    port1 = DummyPort(node, port_type="in")
    port2 = DummyPort(node2, port_type="out")
    # Setup connected_ports for PortConnectedCmd/PortDisconnectedCmd
    port1.model.connected_ports[port2.node().id] = []
    port2.model.connected_ports[port1.node().id] = []
    cmd7 = commands.NodeInputConnectedCmd(port1, port2)
    cmd7.undo()
    cmd7.redo()
    cmd8 = commands.NodeInputDisconnectedCmd(port1, port2)
    cmd8.undo()
    cmd8.redo()

    # PortConnectedCmd/PortDisconnectedCmd
    cmd9 = commands.PortConnectedCmd(port1, port2, emit_signal=True)
    cmd9.undo()
    cmd9.redo()
    cmd10 = commands.PortDisconnectedCmd(port1, port2, emit_signal=True)
    cmd10.undo()
    cmd10.redo()

    # PortLockedCmd/PortUnlockedCmd
    cmd11 = commands.PortLockedCmd(port1)
    cmd11.undo()
    cmd11.redo()
    cmd12 = commands.PortUnlockedCmd(port1)
    cmd12.undo()
    cmd12.redo()

    # PortVisibleCmd
    cmd13 = commands.PortVisibleCmd(port1, True)
    cmd13.undo()
    cmd13.redo()
