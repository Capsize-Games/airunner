from typing import Dict
from airunner.components.tools.search_tool import AggregatedSearchTool


def search(inp: Dict) -> Dict:
    """Perform an aggregated search across services and return deduplicated results.

    Args:
        inp (Dict): Input dictionary with keys 'prompt', 'query', and 'service'.

    Returns:
        Dict: Output dictionary including search results.
    """
    prompt = inp.get("prompt", None)
    query = inp.get("query", [])
    service = inp.get("service", "all")
    seen_items = set()
    all_results = {}
    consolidated_results = []
    for q in query:
        res = AggregatedSearchTool.aggregated_search_sync(q, service)
        if res and isinstance(res, dict):
            for svc, items in res.items():
                if svc not in all_results:
                    all_results[svc] = []
                for item in items:
                    key = (
                        item.get("title", ""),
                        item.get("link", ""),
                    )
                    if key not in seen_items:
                        seen_items.add(key)
                        all_results[svc].append(item)
                        consolidated_results.append(item)
    out = {
        "prompt": prompt,
        "query": query,
        "service": service,
        "results": all_results,
        "consolidated_results": consolidated_results,
    }
    return out
