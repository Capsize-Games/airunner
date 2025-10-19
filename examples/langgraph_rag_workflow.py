"""Example: RAG workflow with LangGraph and LlamaIndex.

This example shows how to integrate LangGraph with existing
LlamaIndex RAG functionality.
"""

import logging
from typing import Dict, Any
from airunner.components.llm.langgraph.state import RAGAgentState
from airunner.components.llm.langgraph.graph_builder import LangGraphBuilder
from airunner.components.llm.langgraph.bridge import LlamaIndexBridge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def prepare_query(state: RAGAgentState) -> RAGAgentState:
    """Extract and prepare query from messages."""
    logger.info("Preparing query")

    messages = state.get("messages", [])
    if messages:
        state["query"] = messages[-1]
    else:
        state["query"] = "What is AI Runner?"

    state["next_action"] = "search"
    return state


def generate_response(state: RAGAgentState) -> RAGAgentState:
    """Generate response using RAG context."""
    logger.info("Generating response with RAG context")

    query = state.get("query", "")
    context = state.get("rag_context", "")

    # Simulate LLM response using context
    response = f"Based on the context, here's the answer to '{query}':\n\n{context[:200]}..."

    state["messages"].append(response)
    state["next_action"] = "end"

    return state


def main():
    """Run the RAG workflow example."""
    print("=" * 60)
    print("LangGraph Integration Example: RAG Workflow")
    print("=" * 60)

    # Build workflow
    print("\n1. Building RAG workflow...")
    builder = LangGraphBuilder(RAGAgentState)

    builder.add_node("prepare_query", prepare_query)
    builder.add_node("generate_response", generate_response)

    # Note: In a real implementation, you would add a RAG search node
    # created using LlamaIndexBridge.create_rag_node(rag_index)
    # For this example, we'll simulate it

    def mock_rag_search(state: RAGAgentState) -> RAGAgentState:
        """Mock RAG search for demonstration."""
        logger.info("Performing RAG search (mock)")
        query = state.get("query", "")

        # Simulate retrieved documents
        state["rag_context"] = (
            f"AI Runner is a powerful tool for managing AI workflows. It supports Stable Diffusion, LLMs, and more. Query: {query}"
        )
        state["retrieved_docs"] = [
            {"text": "AI Runner documentation snippet 1", "score": 0.95},
            {"text": "AI Runner documentation snippet 2", "score": 0.87},
        ]
        state["next_action"] = "generate"
        return state

    builder.add_node("rag_search", mock_rag_search)

    # Connect nodes
    builder.add_edge("prepare_query", "rag_search")
    builder.add_edge("rag_search", "generate_response")
    builder.add_edge("generate_response", "END")
    builder.set_entry_point("prepare_query")

    # Validate
    print("\n2. Validating workflow...")
    if not builder.validate():
        print("❌ Validation failed")
        return

    print("✅ Workflow valid")
    info = builder.get_graph_info()
    print(f"   Nodes: {info['num_nodes']}")
    print(f"   Edges: {info['num_edges']}")
    print(f"   Entry point: {info['entry_point']}")

    # Compile and execute
    print("\n3. Compiling workflow...")
    app = builder.compile()
    print("✅ Workflow compiled")

    # Execute workflow
    print("\n4. Executing RAG workflow...")
    initial_state = {
        "messages": ["What are the main features of AI Runner?"],
        "next_action": "",
        "error": None,
        "metadata": {},
        "rag_context": "",
        "retrieved_docs": [],
        "query": "",
    }

    result = app.invoke(initial_state)

    print("\n5. Results:")
    print(f"   Query: {result['query']}")
    print(f"   Retrieved docs: {len(result['retrieved_docs'])}")
    print(f"   Context length: {len(result['rag_context'])} chars")
    print(f"   Final response: {result['messages'][-1][:200]}...")

    # Demonstrate bridge usage
    print("\n6. LlamaIndex Bridge Example:")
    print(
        "   The LlamaIndexBridge can create RAG nodes from existing indexes:"
    )
    print("   ")
    print("   from llama_index.core import VectorStoreIndex")
    print("   rag_node = LlamaIndexBridge.create_rag_node(")
    print("       rag_index=my_index,")
    print("       top_k=5")
    print("   )")
    print("   builder.add_node('rag_search', rag_node)")

    print("\n" + "=" * 60)
    print("RAG workflow example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
