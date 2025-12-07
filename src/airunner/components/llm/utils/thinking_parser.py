"""Parser for model thinking content.

Models can output reasoning in thinking blocks when enable_thinking=True.
This module provides utilities to extract and handle this content.

Supported formats:
- Qwen3: <think>...</think> (angle bracket format)
- Ministral 3 Reasoning: [THINK]...[/THINK] (bracket format)

Example response from Qwen3:
    <think>
    Let me break this down step by step...
    First, I need to consider...
    </think>
    Here is my final answer.

Example response from Ministral 3 Reasoning:
    [THINK]
    Let me reason through this problem...
    Step 1: Analyze the input...
    [/THINK]
    Here is my final answer.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple


# Thinking tag patterns
ANGLE_THINK_PATTERN = r"<think>(.*?)</think>"  # Qwen3 format
BRACKET_THINK_PATTERN = r"\[THINK\](.*?)\[/THINK\]"  # Ministral 3 Reasoning format
# Combined pattern that matches either format
COMBINED_THINK_PATTERN = r"(?:<think>(.*?)</think>|\[THINK\](.*?)\[/THINK\])"


@dataclass
class ThinkingResponse:
    """Parsed response with thinking content separated.
    
    Attributes:
        thinking_content: The reasoning inside think tags, or None.
        content: The main response after thinking.
        raw_response: The original unprocessed response.
        tag_format: The format detected ('angle', 'brackets', or None).
    """
    thinking_content: Optional[str]
    content: str
    raw_response: str
    tag_format: Optional[str] = None  # 'angle' for <think>, 'brackets' for [THINK]


# Token ID for </think> in Qwen3
THINK_END_TOKEN_ID = 151668


def parse_thinking_response(response: str, tag_format: str = "auto") -> ThinkingResponse:
    """Parse a model response and extract thinking content.
    
    Handles both complete and incomplete thinking blocks gracefully.
    Supports both Qwen3 (<think>...</think>) and Ministral 3 ([THINK]...[/THINK]).
    
    Args:
        response: Raw response string from model.
        tag_format: Tag format to look for:
            - "auto": Detect automatically (default)
            - "angle": Only look for <think>...</think>
            - "brackets": Only look for [THINK]...[/THINK]
        
    Returns:
        ThinkingResponse with separated thinking and content.
        
    Example:
        >>> result = parse_thinking_response(
        ...     "<think>reasoning here</think>final answer"
        ... )
        >>> result.thinking_content
        'reasoning here'
        >>> result.content
        'final answer'
        >>> result.tag_format
        'angle'
        
        >>> result = parse_thinking_response(
        ...     "[THINK]reasoning here[/THINK]final answer"
        ... )
        >>> result.thinking_content
        'reasoning here'
        >>> result.tag_format
        'brackets'
    """
    if not response:
        return ThinkingResponse(
            thinking_content=None,
            content="",
            raw_response=response or "",
            tag_format=None,
        )
    
    # Determine which patterns to try based on tag_format
    if tag_format == "angle":
        patterns = [(ANGLE_THINK_PATTERN, "angle")]
    elif tag_format == "brackets":
        patterns = [(BRACKET_THINK_PATTERN, "brackets")]
    else:  # auto - try both, angle first (more common)
        patterns = [
            (ANGLE_THINK_PATTERN, "angle"),
            (BRACKET_THINK_PATTERN, "brackets"),
        ]
    
    # Try each pattern
    for pattern, fmt in patterns:
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            thinking_content = match.group(1).strip()
            # Get content after the closing tag
            content = response[match.end():].strip()
            return ThinkingResponse(
                thinking_content=thinking_content,
                content=content,
                raw_response=response,
                tag_format=fmt,
            )
    
    # Check for incomplete thinking blocks
    incomplete_patterns = [
        ("<think>", "</think>", "angle"),
        ("[THINK]", "[/THINK]", "brackets"),
    ]
    
    for open_tag, close_tag, fmt in incomplete_patterns:
        if tag_format not in ("auto", fmt):
            continue
        # Case-insensitive check for brackets
        open_check = open_tag.lower() in response.lower() if fmt == "brackets" else open_tag in response
        close_check = close_tag.lower() in response.lower() if fmt == "brackets" else close_tag in response
        
        if open_check and not close_check:
            # Extract partial thinking content
            if fmt == "brackets":
                start_idx = response.lower().index(open_tag.lower()) + len(open_tag)
            else:
                start_idx = response.index(open_tag) + len(open_tag)
            thinking_content = response[start_idx:].strip()
            return ThinkingResponse(
                thinking_content=thinking_content,
                content="",  # Still thinking
                raw_response=response,
                tag_format=fmt,
            )
    
    # No thinking block found
    return ThinkingResponse(
        thinking_content=None,
        content=response.strip(),
        raw_response=response,
        tag_format=None,
    )


def parse_thinking_from_tokens(
    output_ids: list,
    tokenizer,
) -> Tuple[str, str]:
    """Parse thinking content from token IDs using </think> token position.
    
    This is the recommended method when working directly with token outputs,
    as it's more reliable than regex parsing.
    
    Args:
        output_ids: List of output token IDs from the model.
        tokenizer: The tokenizer used for decoding.
        
    Returns:
        Tuple of (thinking_content, main_content).
        
    Example:
        >>> thinking, content = parse_thinking_from_tokens(
        ...     output_ids, tokenizer
        ... )
    """
    try:
        # Find </think> token position from the end
        # rindex finds last occurrence
        reversed_ids = output_ids[::-1]
        index = len(output_ids) - reversed_ids.index(THINK_END_TOKEN_ID)
    except ValueError:
        # No </think> token found
        index = 0
    
    thinking_content = tokenizer.decode(
        output_ids[:index], 
        skip_special_tokens=True
    ).strip()
    
    content = tokenizer.decode(
        output_ids[index:], 
        skip_special_tokens=True
    ).strip()
    
    return thinking_content, content


def strip_thinking_tags(response: str) -> str:
    """Remove thinking blocks from a response.
    
    Supports both Qwen3 (<think>...</think>) and Ministral 3 ([THINK]...[/THINK]).
    Useful when you only want the final answer without reasoning.
    
    Args:
        response: Raw response that may contain thinking blocks.
        
    Returns:
        Response with thinking blocks removed.
    """
    # Remove complete thinking blocks - angle format
    cleaned = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)
    # Remove complete thinking blocks - bracket format (case-insensitive)
    cleaned = re.sub(r"\[THINK\].*?\[/THINK\]", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    # Remove any orphaned angle tags
    cleaned = cleaned.replace("<think>", "").replace("</think>", "")
    # Remove any orphaned bracket tags (case-insensitive)
    cleaned = re.sub(r"\[/?THINK\]", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def has_thinking_content(response: str) -> bool:
    """Check if a response contains thinking content.
    
    Supports both Qwen3 (<think>) and Ministral 3 ([THINK]) formats.
    
    Args:
        response: Response string to check.
        
    Returns:
        True if response contains thinking tags.
    """
    return "<think>" in response or "[THINK]" in response.upper()


def extract_thinking_and_response(response: str, tag_format: str = "auto") -> Tuple[Optional[str], str]:
    """Extract thinking content and main response separately.
    
    Supports both Qwen3 (<think>...</think>) and Ministral 3 ([THINK]...[/THINK]).
    
    Args:
        response: Raw response that may contain thinking blocks.
        tag_format: Tag format to look for:
            - "auto": Detect automatically (default)
            - "angle": Only look for <think>...</think>
            - "brackets": Only look for [THINK]...[/THINK]
        
    Returns:
        Tuple of (thinking_content, main_response).
        thinking_content is None if no thinking block found.
    """
    if not response:
        return None, ""
    
    # Determine which patterns to try
    if tag_format == "angle":
        patterns = [(ANGLE_THINK_PATTERN, "angle")]
    elif tag_format == "brackets":
        patterns = [(BRACKET_THINK_PATTERN, "brackets")]
    else:  # auto - try both
        patterns = [
            (ANGLE_THINK_PATTERN, "angle"),
            (BRACKET_THINK_PATTERN, "brackets"),
        ]
    
    # Try each pattern
    for pattern, _ in patterns:
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            thinking_content = match.group(1).strip()
            # Get content after the closing tag
            main_content = response[match.end():].strip()
            return thinking_content, main_content
    
    # No thinking block found
    return None, response.strip()


# Streaming detection helpers for chunked response processing
# These are used by node_functions_mixin.py during LLM streaming

def detect_thinking_open_tag(text: str) -> Tuple[bool, str, str, str]:
    """Detect if text contains an opening thinking tag.
    
    Supports both <think> (Qwen3) and [THINK] (Ministral 3) formats.
    
    Args:
        text: Chunk of streaming text to check.
        
    Returns:
        Tuple of (found, tag_format, before_tag, after_tag).
        - found: True if an opening tag was detected
        - tag_format: "angle" or "brackets" or "" if not found
        - before_tag: Text before the opening tag (if any)
        - after_tag: Text after the opening tag (if any)
    """
    # Check for angle bracket format first (more common)
    if "<think>" in text:
        parts = text.split("<think>", 1)
        return True, "angle", parts[0], parts[1] if len(parts) > 1 else ""
    
    # Check for bracket format (case-insensitive)
    text_upper = text.upper()
    if "[THINK]" in text_upper:
        # Find position case-insensitively
        idx = text_upper.index("[THINK]")
        return True, "brackets", text[:idx], text[idx + 7:]  # 7 = len("[THINK]")
    
    return False, "", "", ""


def detect_thinking_close_tag(text: str, tag_format: str = "auto") -> Tuple[bool, str, str]:
    """Detect if text contains a closing thinking tag.
    
    Args:
        text: Chunk of streaming text to check.
        tag_format: Expected format ("angle", "brackets", or "auto").
        
    Returns:
        Tuple of (found, before_tag, after_tag).
        - found: True if a closing tag was detected
        - before_tag: Text before the closing tag (if any)
        - after_tag: Text after the closing tag (if any)
    """
    # Check angle format
    if tag_format in ("auto", "angle") and "</think>" in text:
        parts = text.split("</think>", 1)
        return True, parts[0], parts[1] if len(parts) > 1 else ""
    
    # Check bracket format (case-insensitive)
    if tag_format in ("auto", "brackets"):
        text_upper = text.upper()
        if "[/THINK]" in text_upper:
            idx = text_upper.index("[/THINK]")
            return True, text[:idx], text[idx + 8:]  # 8 = len("[/THINK]")
    
    return False, "", ""


def get_close_tag_for_format(tag_format: str) -> str:
    """Get the closing tag string for a given format.
    
    Args:
        tag_format: "angle" or "brackets"
        
    Returns:
        The closing tag string.
    """
    if tag_format == "angle":
        return "</think>"
    elif tag_format == "brackets":
        return "[/THINK]"
    return ""

