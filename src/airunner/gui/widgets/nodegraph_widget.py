from PySide6.QtWidgets import QWidget, QVBoxLayout
from NodeGraphQt import NodeGraph, BaseNode, NodesPaletteWidget


class SimpleAgentNode(BaseNode):
    __identifier__ = "ai_runner.nodes"
    NODE_NAME = "SimpleAgentNode"

    def __init__(self):
        super().__init__()
        self.add_input("input")
        self.add_output("output")

    def execute(self, input_data):
        node_name = self.name()
        # Dummy logic for demonstration
        output_data = f"{node_name} executed on {input_data}"
        return output_data


class NodeGraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Set layout
        layout = QVBoxLayout(self)

        # Initialize node graph
        self.graph = NodeGraph()

        # Register a custom node
        self.graph.register_node(SimpleAgentNode)

        # Set up viewer widget from NodeGraphQt
        viewer = self.graph.widget
        layout.addWidget(viewer)

        # Node palette widget for adding nodes interactively
        self.nodes_palette = NodesPaletteWidget(
            parent=None, node_graph=self.graph
        )
        self.nodes_palette.show()

        # Basic example node creation
        node1 = self.graph.create_node(
            "ai_runner.nodes.SimpleAgentNode",
            name="Analyze Conversation",
            pos=[100, 100],
        )
        node2 = self.graph.create_node(
            "ai_runner.nodes.SimpleAgentNode",
            name="Update Mood",
            pos=[400, 100],
        )

        # Connect nodes
        node1.set_output(0, node2.input(0))

    def execute_workflow(self, initial_input="Initial Data"):
        nodes = self.graph.all_nodes()
        executed_data = initial_input
        executed_order = []

        # Simple linear execution based on connections
        # Find the root node (node with no inputs connected from other nodes in the graph)
        root_node = None
        for node in nodes:
            inputs = node.inputs()
            is_root = True
            for port_name, port in inputs.items():
                if port.connected_ports():
                    is_root = False
                    break
            if is_root:
                root_node = node
                break

        current_node = (
            root_node if root_node else (nodes[0] if nodes else None)
        )

        visited = set()
        while current_node and current_node.id not in visited:
            visited.add(current_node.id)
            # Ensure the node has the execute method before calling
            if hasattr(current_node, "execute") and callable(
                getattr(current_node, "execute")
            ):
                executed_data = current_node.execute(executed_data)
                executed_order.append(current_node.name())
            else:
                print(
                    f"Node {current_node.name()} does not have an execute method."
                )
                # Optionally handle nodes without execute method, e.g., skip or stop workflow

            outputs = current_node.outputs()
            # Check if the node has outputs and the first output is connected
            if (
                outputs
                and outputs.get(list(outputs.keys())[0])
                and outputs[list(outputs.keys())[0]].connected_ports()
            ):
                # Get the first connected port from the first output port
                next_port = outputs[list(outputs.keys())[0]].connected_ports()[
                    0
                ]
                current_node = next_port.node()
            else:
                # No further connections from this node's first output port
                break

        print("Workflow executed in order:", executed_order)
        print("Final output:", executed_data)
