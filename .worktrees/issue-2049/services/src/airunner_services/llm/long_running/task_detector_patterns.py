"""Pattern tables for task-complexity detection."""

from __future__ import annotations


MULTI_ITEM_PATTERNS = [
    r"(\d+)\s+(papers?|topics?|items?|features?|functions?|tests?|files?|endpoints?|components?|modules?|reports?|articles?)",
    r"write\s+(\d+)\s+(?:research\s+)?(?:papers?|reports?|articles?)",
    r"research\s+.+(?:,\s*.+)+(?:,?\s+and\s+.+)",
    r"(?:following|these)[:.]?\s*(?:\d+[.)]\s*.+){2,}",
    r"[-•]\s*.+(?:\n[-•]\s*.+)+",
]

CODING_PROJECT_KEYWORDS = [
    "implement",
    "refactor",
    "build",
    "create",
    "develop",
    "add feature",
    "add test",
    "write test",
    "unit test",
    "fix bug",
    "debug",
    "optimize",
    "migrate",
    "upgrade",
    "port",
    "convert",
    "integrate",
]

CODING_COMPOUND_PATTERNS = [
    r"refactor.*and.*(?:add|write|create)",
    r"(?:add|write|create).*(?:test|feature).*and",
    r"implement.*(?:with|including).*test",
]

MULTI_STEP_KEYWORDS = [
    "step by step",
    "steps",
    "first.*then",
    "after that",
    "following steps",
    "process",
    "workflow",
    "pipeline",
]

ANALYSIS_KEYWORDS = [
    "analyze",
    "investigate",
    "compare",
    "evaluate",
    "assess",
    "review",
    "audit",
    "examine",
    "comprehensive",
    "thorough",
    "in-depth",
    "detailed analysis",
]

RESEARCH_PATTERNS = [
    r"research\s+(\d+)",
    r"write\s+(\d+)\s+(?:papers?|reports?|articles?)",
    r"investigate\s+(?:multiple|several|\d+)",
    r"compare\s+(?:multiple|several|\d+)",
]