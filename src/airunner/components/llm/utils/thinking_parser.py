"""Parser for Qwen3 thinking content.

Qwen3 models can output reasoning in <think>...</think> blocks when
enable_thinking=True. This module provides utilities to extract and
handle this content.

Example response from Qwen3:
    <think>
    Let me break this down step by step...
    First, I need to consider...
    </think>
    Here is my final answer.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class ThinkingResponse:
    """Parsed Qwen3 response with thinking content separated.
    
    Attributes:
        thinking_content: The reasoning inside <think> tags, or None.
        content: The main response after thinking.
        raw_response: The original unprocessed response.
    """
    thinking_content: Optional[str]
    content: str
    raw_response: str


# Token ID for </think> in Qwen3
THINK_END_TOKEN_ID = 151668


def parse_thinking_response(response: str) -> ThinkingResponse:
    """Parse a Qwen3 response and extract thinking content.
    
    Handles both complete and incomplete thinking blocks gracefully.
    
    Args:
        response: Raw response string from Qwen3.
        
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
    """
    if not response:
        return ThinkingResponse(
            thinking_content=None,
            content="",
            raw_response=response or "",
        )
    
    # Pattern to match <think>...</think> block
    pattern = r"<think>(.*?)</think>"
    match = re.search(pattern, response, re.DOTALL)
    
    if match:
        thinking_content = match.group(1).strip()
        # Get content after the </think> tag
        content = response[match.end():].strip()
        return ThinkingResponse(
            thinking_content=thinking_content,
            content=content,
            raw_response=response,
        )
    
    # Check for incomplete thinking block (opened but not closed)
    if "<think>" in response and "</think>" not in response:
        # Extract partial thinking content
        start_idx = response.index("<think>") + len("<think>")
        thinking_content = response[start_idx:].strip()
        return ThinkingResponse(
            thinking_content=thinking_content,
            content="",  # Still thinking
            raw_response=response,
        )
    
    # No thinking block found
    return ThinkingResponse(
        thinking_content=None,
        content=response.strip(),
        raw_response=response,
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
    """Remove <think>...</think> blocks from a response.
    
    Useful when you only want the final answer without reasoning.
    
    Args:
        response: Raw response that may contain thinking blocks.
        
    Returns:
        Response with thinking blocks removed.
    """
    # Remove complete thinking blocks
    cleaned = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)
    # Remove any orphaned tags
    cleaned = cleaned.replace("<think>", "").replace("</think>", "")
    return cleaned.strip()


def has_thinking_content(response: str) -> bool:
    """Check if a response contains thinking content.
    
    Args:
        response: Response string to check.
        
    Returns:
        True if response contains <think> tags.
    """
    return "<think>" in response


def extract_thinking_and_response(response: str) -> Tuple[Optional[str], str]:
    """Extract thinking content and main response separately.
    
    Args:
        response: Raw response that may contain thinking blocks.
        
    Returns:
        Tuple of (thinking_content, main_response).
        thinking_content is None if no thinking block found.
    """
    if not response:
        return None, ""
    
    # Pattern to match <think>...</think> block
    pattern = r"<think>(.*?)</think>"
    match = re.search(pattern, response, re.DOTALL)
    
    if match:
        thinking_content = match.group(1).strip()
        # Get content after the </think> tag
        main_content = response[match.end():].strip()
        return thinking_content, main_content
    
    # No thinking block found
    return None, response.strip()
