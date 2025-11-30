"""
Tool search tool for on-demand tool discovery.

This meta-tool allows the LLM to search for additional tools when the
initially loaded tools don't meet its needs. This significantly reduces
the initial context token count by deferring rarely-used tools.
"""

import json
from typing import Annotated

from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.components.llm.core.tool_search import get_tool_search_engine
from airunner.components.llm.core.tool_schema import get_tool_schema_with_examples
from airunner.utils.application import get_logger


logger = get_logger(__name__)


@tool(
    name="search_tools",
    category=ToolCategory.SYSTEM,
    description=(
        "Search for additional tools by query. Use this when you need a tool "
        "that isn't already available in your current context. Returns tool "
        "definitions that you can then use to accomplish your task."
    ),
    return_direct=False,
    defer_loading=False,  # Always available
    keywords=["find", "discover", "lookup", "tool", "capability", "function"],
    input_examples=[
        {"query": "generate images"},
        {"query": "search web for information"},
        {"query": "read and write files"},
        {"query": "calendar and scheduling"},
    ],
)
def search_tools(
    query: Annotated[str, "Natural language query describing the tool you need"],
    limit: Annotated[int, "Maximum number of tools to return"] = 5,
) -> str:
    """Search for tools matching the query using BM25 + keyword search.
    
    This tool searches through all deferred tools (tools not loaded into
    the initial context) to find relevant capabilities on-demand.
    
    Args:
        query: Natural language query describing needed functionality
        limit: Maximum results to return (default 5)
        
    """
    logger.info(f"🔍 Searching for tools: {query}")
    
    # Get the search engine
    engine = get_tool_search_engine(include_immediate=False)
    
    # Search for matching tools
    results = engine.search(query, limit=limit)
    
    if not results:
        logger.info(f"No tools found matching: {query}")
        return json.dumps({
            "message": "No matching tools found. Try a different query.",
            "tools": [],
        })
    
    # Format results as tool schemas
    tool_schemas = []
    for tool_info in results:
        schema = get_tool_schema_with_examples(tool_info)
        schema["category"] = tool_info.category.value
        tool_schemas.append(schema)
    
    logger.info(f"Found {len(tool_schemas)} tools matching: {query}")
    
    return json.dumps({
        "message": f"Found {len(tool_schemas)} matching tools.",
        "tools": tool_schemas,
    }, indent=2)


@tool(
    name="list_available_tools",
    category=ToolCategory.SYSTEM,
    description=(
        "List all currently available tools grouped by category. "
        "Use this to see what tools are ready to use without searching."
    ),
    return_direct=False,
    defer_loading=False,
    keywords=["list", "show", "available", "tools", "capabilities"],
)
def list_available_tools() -> str:
    """List all immediately available tools by category.
    
    """
    from airunner.components.llm.core.tool_registry import ToolRegistry
    
    immediate = ToolRegistry.get_immediate_tools()
    
    # Group by category
    by_category: dict = {}
    for name, info in immediate.items():
        cat_name = info.category.value
        if cat_name not in by_category:
            by_category[cat_name] = []
        by_category[cat_name].append({
            "name": info.name,
            "description": info.description[:100] + "..." if len(info.description) > 100 else info.description,
        })
    
    # Count deferred tools
    deferred_count = len(ToolRegistry.get_deferred_tools())
    
    return json.dumps({
        "available_tools": by_category,
        "total_available": len(immediate),
        "deferred_tools_count": deferred_count,
        "message": f"Use 'search_tools' to discover {deferred_count} additional tools.",
    }, indent=2)
