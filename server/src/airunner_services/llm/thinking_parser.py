"""Parser for model thinking content."""

import re
from dataclasses import dataclass
from typing import Optional, Tuple

ANGLE_THINK_PATTERN = r"<think>(.*?)</think>"
BRACKET_THINK_PATTERN = r"\[THINK\](.*?)\[/THINK\]"
COMBINED_THINK_PATTERN = r"(?:<think>(.*?)</think>|\[THINK\](.*?)\[/THINK\])"


@dataclass
class ThinkingResponse:
    """Parsed response with thinking content separated."""

    thinking_content: Optional[str]
    content: str
    raw_response: str
    tag_format: Optional[str] = None


THINK_END_TOKEN_ID = 151668


def parse_thinking_response(
    response: str,
    tag_format: str = "auto",
) -> ThinkingResponse:
    """Parse one model response and extract any thinking content."""
    if not response:
        return ThinkingResponse(
            thinking_content=None,
            content="",
            raw_response=response or "",
            tag_format=None,
        )

    if tag_format == "angle":
        patterns = [(ANGLE_THINK_PATTERN, "angle")]
    elif tag_format == "brackets":
        patterns = [(BRACKET_THINK_PATTERN, "brackets")]
    else:
        patterns = [
            (ANGLE_THINK_PATTERN, "angle"),
            (BRACKET_THINK_PATTERN, "brackets"),
        ]

    for pattern, fmt in patterns:
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            thinking_content = match.group(1).strip()
            content = response[match.end() :]
            return ThinkingResponse(
                thinking_content=thinking_content,
                content=content,
                raw_response=response,
                tag_format=fmt,
            )

    incomplete_patterns = [
        ("<think>", "</think>", "angle"),
        ("[THINK]", "[/THINK]", "brackets"),
    ]
    for open_tag, close_tag, fmt in incomplete_patterns:
        if tag_format not in ("auto", fmt):
            continue
        open_check = (
            open_tag.lower() in response.lower()
            if fmt == "brackets"
            else open_tag in response
        )
        close_check = (
            close_tag.lower() in response.lower()
            if fmt == "brackets"
            else close_tag in response
        )
        if open_check and not close_check:
            if fmt == "brackets":
                start_idx = response.lower().index(open_tag.lower())
                start_idx += len(open_tag)
            else:
                start_idx = response.index(open_tag) + len(open_tag)
            thinking_content = response[start_idx:].strip()
            return ThinkingResponse(
                thinking_content=thinking_content,
                content="",
                raw_response=response,
                tag_format=fmt,
            )

    return ThinkingResponse(
        thinking_content=None,
        content=response,
        raw_response=response,
        tag_format=None,
    )


def parse_thinking_from_tokens(output_ids: list, tokenizer) -> Tuple[str, str]:
    """Parse thinking content from token IDs using the close-tag token."""
    try:
        reversed_ids = output_ids[::-1]
        index = len(output_ids) - reversed_ids.index(THINK_END_TOKEN_ID)
    except ValueError:
        index = 0

    thinking_content = tokenizer.decode(
        output_ids[:index],
        skip_special_tokens=True,
    ).strip()
    content = tokenizer.decode(
        output_ids[index:],
        skip_special_tokens=True,
    ).strip()
    return thinking_content, content


def strip_thinking_tags(response: str) -> str:
    """Remove thinking blocks from one response string."""
    cleaned = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)
    cleaned = re.sub(
        r"\[THINK\].*?\[/THINK\]",
        "",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )
    cleaned = cleaned.replace("<think>", "").replace("</think>", "")
    cleaned = re.sub(r"\[/?THINK\]", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def has_thinking_content(response: str) -> bool:
    """Return True when one response contains thinking markers."""
    return "<think>" in response or "[THINK]" in response.upper()


def extract_thinking_and_response(
    response: str,
    tag_format: str = "auto",
) -> Tuple[Optional[str], str]:
    """Extract thinking content and the visible response separately."""
    parsed = parse_thinking_response(response, tag_format=tag_format)
    return parsed.thinking_content, parsed.content


def _compact_text(text: str) -> str:
    """Return text without whitespace for fuzzy prefix matching."""
    return "".join((text or "").split())


def _content_after_compact_prefix(content: str, compact_prefix: str) -> str:
    """Return content after consuming one compact prefix."""
    seen = 0
    prefix_length = len(compact_prefix)
    for index, char in enumerate(content):
        if char.isspace():
            continue
        seen += 1
        if seen >= prefix_length:
            return content[index + 1 :]
    return ""


def normalize_thinking_content(
    thinking_content: Optional[str],
) -> Optional[str]:
    """Return one trimmed thinking string or None when blank."""
    if thinking_content is None:
        return None
    cleaned = thinking_content.strip()
    return cleaned or None


def strip_stored_thinking_prefix(
    content: str,
    thinking_content: Optional[str],
) -> str:
    """Remove duplicated leading thinking text from one saved response."""
    raw_content = content or ""
    tagged_thinking, tagged_content = extract_thinking_and_response(
        raw_content
    )
    if tagged_thinking:
        return tagged_content
    cleaned = strip_thinking_tags(raw_content)
    compact_thinking = _compact_text(
        normalize_thinking_content(thinking_content) or ""
    )
    if not cleaned or not compact_thinking:
        return cleaned
    if not _compact_text(cleaned).startswith(compact_thinking):
        return cleaned
    return _content_after_compact_prefix(cleaned, compact_thinking)


def detect_thinking_open_tag(text: str) -> Tuple[bool, str, str, str]:
    """Detect one opening thinking tag in streamed text."""
    if "<think>" in text:
        parts = text.split("<think>", 1)
        return True, "angle", parts[0], parts[1] if len(parts) > 1 else ""

    text_upper = text.upper()
    if "[THINK]" in text_upper:
        idx = text_upper.index("[THINK]")
        return True, "brackets", text[:idx], text[idx + 7 :]

    return False, "", "", ""


def detect_thinking_close_tag(
    text: str,
    tag_format: str = "auto",
) -> Tuple[bool, str, str]:
    """Detect one closing thinking tag in streamed text."""
    if tag_format in ("auto", "angle") and "</think>" in text:
        parts = text.split("</think>", 1)
        return True, parts[0], parts[1] if len(parts) > 1 else ""

    if tag_format in ("auto", "brackets"):
        text_upper = text.upper()
        if "[/THINK]" in text_upper:
            idx = text_upper.index("[/THINK]")
            return True, text[:idx], text[idx + 8 :]

    return False, "", ""


def get_close_tag_for_format(tag_format: str) -> str:
    """Return the closing tag string for one thinking-tag format."""
    if tag_format == "angle":
        return "</think>"
    if tag_format == "brackets":
        return "[/THINK]"
    return ""
