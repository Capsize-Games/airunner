"""Document task routing configuration for attached-document prompts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentTaskConfig:
    """Routing and response policy for one document task kind."""

    intent: str
    force_tool: str
    answer_mode: str
    direct_patterns: tuple[str, ...] = ()
    contextual_patterns: tuple[str, ...] = ()


DOCUMENT_SURFACE_PATTERNS = (
    r"\bdocument\b",
    r"\bfile\b",
    r"\bbook\b",
    r"\bpdf\b",
    r"\buploaded\b",
    r"\bloaded\b",
)


DOCUMENT_TASK_CONFIGS = (
    DocumentTaskConfig(
        intent="structure",
        force_tool="inspect_loaded_documents",
        answer_mode="deterministic",
        contextual_patterns=(
            r"\btable\s+of\s+contents\b",
            r"\bchapters?\b",
            r"\bsections?\b",
            r"\boutline\b",
            r"\bdocument\s+structure\b",
        ),
    ),
    DocumentTaskConfig(
        intent="compare",
        force_tool="rag_search",
        answer_mode="synthesized",
        contextual_patterns=(
            r"\bcompare\b",
            r"\bcontrast\b",
            r"\bdifferences?\b",
            r"\bsimilarit(?:y|ies)\b",
            r"\bversus\b",
            r"\bvs\.?\b",
        ),
    ),
    DocumentTaskConfig(
        intent="extract",
        force_tool="rag_search",
        answer_mode="synthesized",
        contextual_patterns=(
            r"\bextract\b",
            r"\bpull\s+out\b",
            r"\bcollect\b",
            r"\bcompile\b",
            r"\bfind\s+all\b",
            r"\blocate\b",
        ),
    ),
    DocumentTaskConfig(
        intent="list",
        force_tool="rag_search",
        answer_mode="synthesized",
        contextual_patterns=(
            r"\blist\b",
            r"\benumerate\b",
            r"\bitemi[sz]e\b",
            r"\bshow\s+me\s+all\b",
        ),
    ),
    DocumentTaskConfig(
        intent="transform",
        force_tool="rag_search",
        answer_mode="synthesized",
        direct_patterns=(
            r"\bsummar(?:ize|y)\b.*\bin\s+a\s+table\b",
            r"\bformat\b.*\bas\b",
        ),
        contextual_patterns=(
            r"\bin\s+a\s+table\b",
            r"\btabulate\b",
            r"\bformatted?\s+as\b",
            r"\borgani[sz]e\b",
            r"\brestructure\b",
            r"\bconvert\b",
            r"\bcsv\b",
            r"\bjson\b",
            r"\bmarkdown\b",
        ),
    ),
    DocumentTaskConfig(
        intent="summary",
        force_tool="rag_search",
        answer_mode="synthesized",
        contextual_patterns=(
            r"\bsummar(?:ize|y)\b",
            r"\boverview\b",
            r"\bmain\s+(?:idea|topic|theme)\b",
            r"\bwhat\s+is\s+(?:this|the)\s+(?:document|book)\s+about\b",
            r"\bwhat\s+is\s+the\s+premise(?:\s+and\s+theme[s]?)?\s+of\s+(?:this|the)\s+(?:document|book|novel|story|file)\b",
            r"\bwhat\s+are\s+the\s+premise\s+and\s+theme[s]?\s+of\s+(?:this|the)\s+(?:document|book|novel|story|file)\b",
            r"\bdescribe\s+the\s+premise(?:\s+and\s+theme[s]?)?\s+of\s+(?:this|the)\s+(?:document|book|novel|story|file)\b",
            r"\b(?:synopsis|plot)\s+of\s+(?:this|the)\s+(?:document|book|novel|story|file)\b",
            r"\bwhat\s+happens\s+in\s+(?:this|the)\s+(?:document|book|novel|story|file)\b",
            r"\btell\s+me\s+more\s+about\s+(?:this|the)\s+(?:document|book|file)\b",
            r"\bmore\s+about\s+(?:this|the)\s+(?:document|book|file)\b",
        ),
    ),
    DocumentTaskConfig(
        intent="identity",
        force_tool="inspect_loaded_documents",
        answer_mode="deterministic",
        direct_patterns=(
            r"\bwhat(?:'s| is)\s+(?:this|the)\s+(?:document|file|book)\b",
            r"\bwhat\s+(?:document|file|book)\s+is\s+this\b",
            r"\bwhich\s+(?:document|file|book)\s+is\s+this\b",
            r"\bidentify\s+(?:this|the)\s+(?:document|file|book)\b",
            r"\bwhat\s+documents?\s+(?:are\s+)?(?:loaded|uploaded|available)\b",
        ),
        contextual_patterns=(
            r"\btitle\b",
            r"\bauthor\b",
            r"\bwho\s+wrote\b",
            r"\bfile\s+type\b",
            r"\bformat\b",
            r"\bextension\b",
        ),
    ),
)


DEFAULT_DOCUMENT_TASK = DocumentTaskConfig(
    intent="retrieval",
    force_tool="rag_search",
    answer_mode="synthesized",
)


DOCUMENT_TASK_CONFIGS_BY_INTENT = {
    config.intent: config for config in DOCUMENT_TASK_CONFIGS
}


def get_document_task_config(intent: str | None) -> DocumentTaskConfig | None:
    """Return the configured task metadata for one document intent."""
    if not intent:
        return None
    return DOCUMENT_TASK_CONFIGS_BY_INTENT.get(intent)