"""
Nodegraph workflow management tools.

LangChain tools for creating, modifying, and executing LangGraph workflows.
"""

from typing import Annotated, Any, Optional, Dict, List

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.components.nodegraph.data.workflow import Workflow
from airunner.components.nodegraph.data.workflow_node import WorkflowNode
from airunner.components.nodegraph.data.workflow_connection import (
    WorkflowConnection,
)


@tool(
    name="create_workflow",
    category=ToolCategory.WORKFLOW,
    description=("Create a new LangGraph workflow with nodes and connections"),
    return_direct=False,
    requires_api=True,
)
def create_workflow(
    name: Annotated[str, "Workflow name"],
    description: Annotated[str, "Workflow description"],
    nodes: Annotated[
        List[Dict],
        "List of nodes with keys: node_identifier, name, properties",
    ],
    connections: Annotated[
        List[Dict],
        "List of connections with keys: output_node_name, output_port, input_node_name, input_port",
    ],
    variables: Annotated[
        Optional[Dict], "Workflow variables (optional)"
    ] = None,
    api: Any = None,
) -> str:
    """Create a new workflow and save to database.

    Args:
        name: Workflow name (must be unique)
        description: Workflow description
        nodes: List of node definitions
        connections: List of node connections
        variables: Optional workflow variables
        api: API instance (injected)

    Returns:
        Success message with workflow ID

    Example nodes:
        [
            {
                "node_identifier": "ai_runner.nodes.InputNode",
                "name": "input",
                "properties": {"label": "User Input"}
            },
            {
                "node_identifier": "ai_runner.nodes.AgentNode",
                "name": "agent",
                "properties": {"agent_name": "research_expert"}
            }
        ]

    Example connections:
        [
            {
                "output_node_name": "input",
                "output_port": "output",
                "input_node_name": "agent",
                "input_port": "input"
            }
        ]
    """
    try:
        # Check if workflow with name already exists
        existing = Workflow.objects.filter_by(name=name)
        if existing and len(existing) > 0:
            return f"Error: Workflow '{name}' already exists (ID: {existing[0].id})"

        # Create workflow
        workflow = Workflow.objects.create(
            name=name,
            description=description,
            variables=variables or {},
        )

        # Create nodes
        node_map = {}  # name -> WorkflowNode
        for idx, node_def in enumerate(nodes):
            node = WorkflowNode.objects.create(
                workflow_id=workflow.id,
                node_identifier=node_def.get(
                    "node_identifier", "ai_runner.nodes.GenericNode"
                ),
                name=node_def.get("name", f"node_{idx}"),
                pos_x=node_def.get("pos_x", idx * 200.0),
                pos_y=node_def.get("pos_y", 0.0),
                properties=node_def.get("properties", {}),
            )
            node_map[node.name] = node

        # Create connections
        for conn_def in connections:
            output_node = node_map.get(conn_def.get("output_node_name"))
            input_node = node_map.get(conn_def.get("input_node_name"))

            if not output_node or not input_node:
                return f"Error: Invalid node name in connection: {conn_def}"

            WorkflowConnection.objects.create(
                workflow_id=workflow.id,
                output_node_id=output_node.id,
                output_port_name=conn_def.get("output_port", "output"),
                input_node_id=input_node.id,
                input_port_name=conn_def.get("input_port", "input"),
            )

        return (
            f"Successfully created workflow '{name}' (ID: {workflow.id}) "
            f"with {len(nodes)} nodes and {len(connections)} connections"
        )

    except Exception as e:
        return f"Error creating workflow: {str(e)}"


@tool(
    name="list_workflows",
    category=ToolCategory.WORKFLOW,
    description="List all saved workflows",
    return_direct=False,
    requires_api=False,
)
def list_workflows() -> str:
    """List all workflows with their IDs, names, and descriptions.

    Returns:
        Formatted list of workflows
    """
    try:
        workflows = Workflow.objects.all()

        if not workflows:
            return "No workflows found. Create one with create_workflow tool."

        result = ["Available Workflows:", ""]
        for wf in workflows:
            # Query nodes separately since dataclass doesn't have relationships
            nodes = WorkflowNode.objects.filter_by(workflow_id=wf.id)
            node_count = len(nodes) if nodes else 0
            result.append(f"ID: {wf.id}")
            result.append(f"  Name: {wf.name}")
            result.append(
                f"  Description: {wf.description or '(no description)'}"
            )
            result.append(f"  Nodes: {node_count}")
            result.append("")

        return "\n".join(result)

    except Exception as e:
        return f"Error listing workflows: {str(e)}"


@tool(
    name="get_workflow",
    category=ToolCategory.WORKFLOW,
    description="Get detailed information about a specific workflow",
    return_direct=False,
    requires_api=False,
)
def get_workflow(
    workflow_id: Annotated[int, "Workflow ID to retrieve"],
) -> str:
    """Get workflow details including nodes and connections.

    Args:
        workflow_id: ID of the workflow

    Returns:
        Detailed workflow information
    """
    try:
        workflow = Workflow.objects.get(workflow_id)
        if not workflow:
            return f"Error: Workflow with ID {workflow_id} not found"

        # Query nodes and connections separately since dataclass doesn't have relationships
        nodes = WorkflowNode.objects.filter_by(workflow_id=workflow.id)
        connections = WorkflowConnection.objects.filter_by(
            workflow_id=workflow.id
        )

        result = [
            f"Workflow: {workflow.name} (ID: {workflow.id})",
            f"Description: {workflow.description or '(no description)'}",
            "",
            f"Variables: {workflow.variables or {}}",
            "",
            "Nodes:",
        ]

        for node in nodes:
            result.append(f"  - {node.name} ({node.node_identifier})")
            if node.properties:
                result.append(f"    Properties: {node.properties}")

        result.append("")
        result.append("Connections:")

        for conn in connections:
            output_node = next(
                (n for n in nodes if n.id == conn.output_node_id),
                None,
            )
            input_node = next(
                (n for n in nodes if n.id == conn.input_node_id),
                None,
            )

            if output_node and input_node:
                result.append(
                    f"  - {output_node.name}.{conn.output_port_name} -> "
                    f"{input_node.name}.{conn.input_port_name}"
                )

        return "\n".join(result)

    except Exception as e:
        return f"Error retrieving workflow: {str(e)}"


@tool(
    name="delete_workflow",
    category=ToolCategory.WORKFLOW,
    description="Delete a workflow by ID",
    return_direct=False,
    requires_api=False,
)
def delete_workflow(
    workflow_id: Annotated[int, "Workflow ID to delete"],
) -> str:
    """Delete a workflow and all its nodes/connections.

    Args:
        workflow_id: ID of the workflow to delete

    Returns:
        Success or error message
    """
    try:
        workflow = Workflow.objects.get(workflow_id)
        if not workflow:
            return f"Error: Workflow with ID {workflow_id} not found"

        name = workflow.name
        Workflow.objects.delete(workflow_id)

        return f"Successfully deleted workflow '{name}' (ID: {workflow_id})"

    except Exception as e:
        return f"Error deleting workflow: {str(e)}"


@tool(
    name="modify_workflow",
    category=ToolCategory.WORKFLOW,
    description="Modify an existing workflow (add/remove nodes or connections)",
    return_direct=False,
    requires_api=False,
)
def modify_workflow(
    workflow_id: Annotated[int, "Workflow ID to modify"],
    add_nodes: Annotated[
        Optional[List[Dict]], "Nodes to add (optional)"
    ] = None,
    remove_node_names: Annotated[
        Optional[List[str]], "Node names to remove (optional)"
    ] = None,
    add_connections: Annotated[
        Optional[List[Dict]], "Connections to add (optional)"
    ] = None,
    remove_connections: Annotated[
        Optional[List[Dict]], "Connections to remove (optional)"
    ] = None,
    update_description: Annotated[
        Optional[str], "New description (optional)"
    ] = None,
) -> str:
    """Modify workflow structure.

    Args:
        workflow_id: ID of the workflow to modify
        add_nodes: List of node definitions to add
        remove_node_names: List of node names to remove
        add_connections: List of connections to add
        remove_connections: List of connections to remove
        update_description: New workflow description

    Returns:
        Success message with changes made
    """
    try:
        workflow = Workflow.objects.get(workflow_id)
        if not workflow:
            return f"Error: Workflow with ID {workflow_id} not found"

        changes = []

        # Update description
        if update_description is not None:
            Workflow.objects.update(
                workflow_id, description=update_description
            )
            changes.append("updated description")

        # Query nodes and connections separately since dataclass doesn't have relationships
        nodes = WorkflowNode.objects.filter_by(workflow_id=workflow.id)
        connections = WorkflowConnection.objects.filter_by(
            workflow_id=workflow.id
        )

        # Add nodes
        if add_nodes:
            node_map = {n.name: n for n in nodes}
            for node_def in add_nodes:
                node = WorkflowNode.objects.create(
                    workflow_id=workflow.id,
                    node_identifier=node_def.get(
                        "node_identifier", "ai_runner.nodes.GenericNode"
                    ),
                    name=node_def.get("name", f"new_node_{len(node_map)}"),
                    pos_x=node_def.get("pos_x", 0.0),
                    pos_y=node_def.get("pos_y", 0.0),
                    properties=node_def.get("properties", {}),
                )
                node_map[node.name] = node
            changes.append(f"added {len(add_nodes)} node(s)")

        # Remove nodes
        if remove_node_names:
            for node_name in remove_node_names:
                node = next((n for n in nodes if n.name == node_name), None)
                if node:
                    WorkflowNode.objects.delete(node.id)
            changes.append(f"removed {len(remove_node_names)} node(s)")

        # Add connections
        if add_connections:
            node_map = {n.name: n for n in nodes}
            for conn_def in add_connections:
                output_node = node_map.get(conn_def.get("output_node_name"))
                input_node = node_map.get(conn_def.get("input_node_name"))

                if output_node and input_node:
                    WorkflowConnection.objects.create(
                        workflow_id=workflow.id,
                        output_node_id=output_node.id,
                        output_port_name=conn_def.get("output_port", "output"),
                        input_node_id=input_node.id,
                        input_port_name=conn_def.get("input_port", "input"),
                    )
            changes.append(f"added {len(add_connections)} connection(s)")

        # Remove connections (by node names and ports)
        if remove_connections:
            node_map = {n.name: n for n in nodes}
            for conn_def in remove_connections:
                output_node = node_map.get(conn_def.get("output_node_name"))
                input_node = node_map.get(conn_def.get("input_node_name"))

                if output_node and input_node:
                    conn = next(
                        (
                            c
                            for c in connections
                            if c.output_node_id == output_node.id
                            and c.output_port
                            == conn_def.get("output_port", "output")
                            and c.input_node_id == input_node.id
                            and c.input_port
                            == conn_def.get("input_port", "input")
                        ),
                        None,
                    )
                    if conn:
                        WorkflowConnection.objects.delete(conn.id)
            changes.append(f"removed {len(remove_connections)} connection(s)")

        if not changes:
            return "No changes made to workflow"

        return f"Successfully modified workflow '{workflow.name}': {', '.join(changes)}"

    except Exception as e:
        return f"Error modifying workflow: {str(e)}"


@tool(
    name="execute_workflow",
    category=ToolCategory.WORKFLOW,
    description="Execute a workflow with input data",
    return_direct=False,
    requires_api=True,
)
def execute_workflow(
    workflow_id: Annotated[int, "Workflow ID to execute"],
    input_data: Annotated[Dict, "Input data for the workflow"],
    api: Any = None,
) -> str:
    """Execute a workflow and return results.

    Args:
        workflow_id: ID of the workflow to execute
        input_data: Input data dictionary
        api: API instance (injected)

    Returns:
        Execution results or error message
    """
    try:
        workflow = Workflow.objects.get(workflow_id)
        if not workflow:
            return f"Error: Workflow with ID {workflow_id} not found"

        # Load and execute workflow via API
        result = {"status": "pending"}

        def on_complete(execution_result):
            result.update(execution_result)

        api.nodegraph.load_workflow(workflow, on_complete)

        # Note: This is a simplified version. In reality, workflow execution
        # is asynchronous and would need proper result handling.
        return (
            f"Workflow '{workflow.name}' execution started. "
            f"Input: {input_data}"
        )

    except Exception as e:
        return f"Error executing workflow: {str(e)}"


@tool(
    name="switch_mode",
    category=ToolCategory.WORKFLOW,
    description=("Switch between AI Runner mode and LangGraph workflow mode"),
    return_direct=False,
    requires_api=True,
)
def switch_mode(
    mode: Annotated[str, "Mode to switch to: 'airunner' or 'langgraph'"],
    api: Any = None,
) -> str:
    """Switch application mode.

    Args:
        mode: Target mode ('airunner' or 'langgraph')
        api: API instance (injected)

    Returns:
        Success message
    """
    if mode.lower() not in ["airunner", "langgraph"]:
        return "Error: Mode must be 'airunner' or 'langgraph'"

    # This would trigger a mode switch in the application
    # For now, just acknowledge the request
    return f"Switching to {mode} mode..."
