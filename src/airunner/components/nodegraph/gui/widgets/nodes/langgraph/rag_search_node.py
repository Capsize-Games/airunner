"""RAG Search Node for LangGraph workflows.

This node performs RAG search using LlamaIndex.
"""

from typing import List
from airunner.vendor.nodegraphqt.constants import NodePropWidgetEnum
from airunner.components.nodegraph.gui.widgets.nodes.langgraph.base_langgraph_node import (
    BaseLangGraphNode,
)


class RAGSearchNode(BaseLangGraphNode):
    """Perform RAG search using LlamaIndex.

    This node retrieves relevant documents from a vector store
    and adds them to the workflow state.
    """

    NODE_NAME = "RAG Search"
    state_key = "rag_context"

    _input_ports = [
        dict(name="query", display_name="Query"),
    ]

    _output_ports = [
        dict(name="context", display_name="Context"),
        dict(name="documents", display_name="Documents"),
    ]

    _properties = [
        dict(
            name="top_k",
            value=5,
            widget_type=NodePropWidgetEnum.QSPIN_BOX,
            range=(1, 20),
            tab="search",
        ),
        dict(
            name="query_key",
            value="query",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="state",
        ),
        dict(
            name="context_key",
            value="rag_context",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="state",
        ),
        dict(
            name="docs_key",
            value="retrieved_docs",
            widget_type=NodePropWidgetEnum.QLINE_EDIT,
            tab="state",
        ),
    ]

    def get_node_type(self) -> str:
        """Get node type identifier."""
        return "rag"

    def get_description(self) -> str:
        """Get node description."""
        top_k = self.get_property("top_k")
        return f"RAG search (top {top_k})"

    def to_langgraph_code(self) -> str:
        """Generate Python code for RAG search.

        Returns:
            Python code string
        """
        top_k = self.get_property("top_k")
        query_key = self.get_property("query_key")
        context_key = self.get_property("context_key")
        docs_key = self.get_property("docs_key")

        func_name = self._sanitize_name(self.name())

        code = f'''def {func_name}(state: AgentState) -> AgentState:
    """{self.get_description()}"""
    # NOTE: RAG index must be provided externally
    # This is a bridge to existing LlamaIndex functionality
    
    query = state.get("{query_key}", "")
    if not query:
        # Try getting from messages
        messages = state.get("messages", [])
        query = messages[-1] if messages else ""
    
    if not query:
        logger.warning("No query found for RAG search")
        return state
    
    try:
        # Use LlamaIndex bridge (must be configured)
        from airunner.components.llm.langgraph.bridge import LlamaIndexBridge
        
        # This assumes a global rag_index is available
        # In practice, this would be passed via config
        if hasattr(state.get("metadata", {{}}), "rag_index"):
            rag_index = state["metadata"]["rag_index"]
            retriever = rag_index.as_retriever(similarity_top_k={top_k})
            nodes = retriever.retrieve(query)
            
            context_parts = [node.text for node in nodes]
            doc_metadata = [
                {{"text": node.text[:200], "score": node.score}}
                for node in nodes
            ]
            
            state["{context_key}"] = "\\n\\n".join(context_parts)
            state["{docs_key}"] = doc_metadata
            logger.info(f"Retrieved {{len(nodes)}} documents")
        else:
            logger.warning("No RAG index found in state metadata")
    
    except Exception as e:
        logger.error(f"RAG search error: {{e}}")
        state["error"] = str(e)
    
    return state'''

        return code

    def get_input_state_keys(self) -> List[str]:
        """Get state keys this node reads from."""
        return [self.get_property("query_key"), "messages"]

    def get_output_state_keys(self) -> List[str]:
        """Get state keys this node writes to."""
        return [
            self.get_property("context_key"),
            self.get_property("docs_key"),
        ]

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize node name to valid Python identifier."""
        sanitized = "".join(
            c if c.isalnum() or c == "_" else "_" for c in name
        )
        if sanitized and sanitized[0].isdigit():
            sanitized = f"node_{sanitized}"
        return sanitized or "rag_node"
