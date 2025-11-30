"""Document editor tools for LLM-assisted document/code editing.

Provides tools for the LLM to interact with the document editor:
- Get document content (full or line ranges)
- Edit document content (replace lines, insert, delete)
- Search within document
- Get cursor position and selection
- Navigate to specific lines

These tools enable the LLM to assist with code editing in a manner
similar to modern AI coding assistants.
"""

import re
from typing import Optional, List, Tuple
from airunner.components.llm.core.tool_registry import tool, ToolCategory
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.enums import SignalCode

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _get_document_editor():
    """Get the active document editor widget if available.
    
    """
    try:
        # Access via the application's main window
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if not app:
            return None
            
        # Find the main window
        for widget in app.topLevelWidgets():
            if hasattr(widget, "ui") and hasattr(widget.ui, "document_editor_tab"):
                # Get the document editor container
                container = widget.ui.document_editor_tab.findChild(
                    type(widget.ui.document_editor_tab), 
                    recursive=False
                )
                # Try to get active editor from container
                for child in widget.ui.document_editor_tab.findChildren(object):
                    if hasattr(child, "editor") and hasattr(child, "current_file_path"):
                        return child
        return None
    except Exception as e:
        logger.debug(f"Could not get document editor: {e}")
        return None


def _get_active_document_content() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Get content from the active document editor.
    
    """
    editor_widget = _get_document_editor()
    if not editor_widget:
        return None, None, None
        
    try:
        content = editor_widget.editor.toPlainText()
        file_path = editor_widget.current_file_path
        
        # Determine language from file extension
        language = "plaintext"
        if file_path:
            ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
            lang_map = {
                "py": "python",
                "js": "javascript",
                "ts": "typescript",
                "html": "html",
                "css": "css",
                "json": "json",
                "md": "markdown",
                "sh": "bash",
                "yaml": "yaml",
                "yml": "yaml",
            }
            language = lang_map.get(ext, "plaintext")
        
        return content, file_path, language
    except Exception as e:
        logger.error(f"Error getting document content: {e}")
        return None, None, None


@tool(
    name="get_document_content",
    category=ToolCategory.CODE,
    description=(
        "Get the content of the currently open document in the document editor. "
        "Can retrieve the full document or a specific range of lines. "
        "Returns the content along with file path and detected language."
    ),
    keywords=["document", "code", "editor", "read", "content", "file"],
)
def get_document_content(
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> str:
    """
    Get content from the active document editor.
    
    Args:
        start_line: Optional starting line number (1-indexed). If None, starts from beginning.
        end_line: Optional ending line number (1-indexed, inclusive). If None, reads to end.
    
    """
    content, file_path, language = _get_active_document_content()
    
    if content is None:
        return "Error: No document is currently open in the document editor."
    
    lines = content.split("\n")
    total_lines = len(lines)
    
    # Handle line range
    if start_line is not None or end_line is not None:
        start_idx = (start_line - 1) if start_line else 0
        end_idx = end_line if end_line else total_lines
        
        # Clamp to valid range
        start_idx = max(0, min(start_idx, total_lines - 1))
        end_idx = max(start_idx + 1, min(end_idx, total_lines))
        
        selected_lines = lines[start_idx:end_idx]
        content = "\n".join(selected_lines)
        line_info = f"Lines {start_idx + 1}-{end_idx} of {total_lines}"
    else:
        line_info = f"Total lines: {total_lines}"
    
    result = [
        f"**File:** {file_path or '(Untitled)'}",
        f"**Language:** {language}",
        f"**{line_info}**",
        "",
        "```" + language,
        content,
        "```"
    ]
    
    return "\n".join(result)


@tool(
    name="get_document_info",
    category=ToolCategory.CODE,
    description=(
        "Get information about the currently open document without retrieving all content. "
        "Returns file path, language, line count, and cursor position."
    ),
    keywords=["document", "info", "metadata", "cursor", "position"],
)
def get_document_info() -> str:
    """
    Get metadata about the active document.
    
    """
    editor_widget = _get_document_editor()
    
    if not editor_widget:
        return "Error: No document is currently open in the document editor."
    
    try:
        content = editor_widget.editor.toPlainText()
        file_path = editor_widget.current_file_path or "(Untitled)"
        lines = content.split("\n")
        total_lines = len(lines)
        total_chars = len(content)
        
        # Get cursor position
        cursor = editor_widget.editor.textCursor()
        cursor_line = cursor.blockNumber() + 1
        cursor_col = cursor.positionInBlock() + 1
        
        # Check if modified
        is_modified = editor_widget.is_modified()
        
        # Determine language
        language = "plaintext"
        if file_path and "." in file_path:
            ext = file_path.rsplit(".", 1)[-1].lower()
            lang_map = {
                "py": "python", "js": "javascript", "ts": "typescript",
                "html": "html", "css": "css", "json": "json", 
                "md": "markdown", "sh": "bash", "yaml": "yaml",
            }
            language = lang_map.get(ext, "plaintext")
        
        return (
            f"**File:** {file_path}\n"
            f"**Language:** {language}\n"
            f"**Lines:** {total_lines}\n"
            f"**Characters:** {total_chars}\n"
            f"**Cursor:** Line {cursor_line}, Column {cursor_col}\n"
            f"**Modified:** {'Yes' if is_modified else 'No'}"
        )
    except Exception as e:
        logger.error(f"Error getting document info: {e}")
        return f"Error: Could not get document info: {e}"


@tool(
    name="edit_document_lines",
    category=ToolCategory.CODE,
    description=(
        "Replace a range of lines in the document editor. "
        "Provide the start and end line numbers (1-indexed, inclusive) and the new content. "
        "The new content will replace all lines from start_line to end_line."
    ),
    keywords=["edit", "replace", "lines", "modify", "code", "document"],
)
def edit_document_lines(
    start_line: int,
    end_line: int,
    new_content: str,
) -> str:
    """
    Replace lines in the active document.
    
    Args:
        start_line: Starting line number (1-indexed).
        end_line: Ending line number (1-indexed, inclusive).
        new_content: The new content to insert.
    
    """
    editor_widget = _get_document_editor()
    
    if not editor_widget:
        return "Error: No document is currently open in the document editor."
    
    try:
        content = editor_widget.editor.toPlainText()
        lines = content.split("\n")
        total_lines = len(lines)
        
        # Validate line numbers
        if start_line < 1 or start_line > total_lines:
            return f"Error: start_line {start_line} is out of range (1-{total_lines})"
        if end_line < start_line or end_line > total_lines:
            return f"Error: end_line {end_line} is out of range ({start_line}-{total_lines})"
        
        # Convert to 0-indexed
        start_idx = start_line - 1
        end_idx = end_line
        
        # Replace the lines
        new_lines = new_content.split("\n")
        lines[start_idx:end_idx] = new_lines
        
        # Update the document
        editor_widget.editor.setPlainText("\n".join(lines))
        
        return (
            f"✓ Replaced lines {start_line}-{end_line} with {len(new_lines)} lines. "
            f"Document now has {len(lines)} lines."
        )
    except Exception as e:
        logger.error(f"Error editing document: {e}")
        return f"Error: Could not edit document: {e}"


@tool(
    name="insert_document_lines",
    category=ToolCategory.CODE,
    description=(
        "Insert new lines at a specific position in the document. "
        "The new content will be inserted AFTER the specified line number. "
        "Use line 0 to insert at the beginning of the document."
    ),
    keywords=["insert", "add", "lines", "code", "document"],
)
def insert_document_lines(
    after_line: int,
    content: str,
) -> str:
    """
    Insert lines after a specific line in the document.
    
    Args:
        after_line: Insert after this line number (0 for beginning).
        content: The content to insert.
    
    """
    editor_widget = _get_document_editor()
    
    if not editor_widget:
        return "Error: No document is currently open in the document editor."
    
    try:
        doc_content = editor_widget.editor.toPlainText()
        lines = doc_content.split("\n")
        total_lines = len(lines)
        
        # Validate line number
        if after_line < 0 or after_line > total_lines:
            return f"Error: after_line {after_line} is out of range (0-{total_lines})"
        
        # Insert the new lines
        new_lines = content.split("\n")
        lines[after_line:after_line] = new_lines
        
        # Update the document
        editor_widget.editor.setPlainText("\n".join(lines))
        
        return (
            f"✓ Inserted {len(new_lines)} lines after line {after_line}. "
            f"Document now has {len(lines)} lines."
        )
    except Exception as e:
        logger.error(f"Error inserting lines: {e}")
        return f"Error: Could not insert lines: {e}"


@tool(
    name="delete_document_lines",
    category=ToolCategory.CODE,
    description=(
        "Delete a range of lines from the document. "
        "Provide the start and end line numbers (1-indexed, inclusive)."
    ),
    keywords=["delete", "remove", "lines", "code", "document"],
)
def delete_document_lines(
    start_line: int,
    end_line: int,
) -> str:
    """
    Delete lines from the active document.
    
    Args:
        start_line: Starting line number (1-indexed).
        end_line: Ending line number (1-indexed, inclusive).
    
    """
    editor_widget = _get_document_editor()
    
    if not editor_widget:
        return "Error: No document is currently open in the document editor."
    
    try:
        content = editor_widget.editor.toPlainText()
        lines = content.split("\n")
        total_lines = len(lines)
        
        # Validate line numbers
        if start_line < 1 or start_line > total_lines:
            return f"Error: start_line {start_line} is out of range (1-{total_lines})"
        if end_line < start_line or end_line > total_lines:
            return f"Error: end_line {end_line} is out of range ({start_line}-{total_lines})"
        
        # Convert to 0-indexed and delete
        start_idx = start_line - 1
        end_idx = end_line
        deleted_count = end_idx - start_idx
        del lines[start_idx:end_idx]
        
        # Update the document
        editor_widget.editor.setPlainText("\n".join(lines))
        
        return (
            f"✓ Deleted {deleted_count} lines ({start_line}-{end_line}). "
            f"Document now has {len(lines)} lines."
        )
    except Exception as e:
        logger.error(f"Error deleting lines: {e}")
        return f"Error: Could not delete lines: {e}"


@tool(
    name="search_document",
    category=ToolCategory.CODE,
    description=(
        "Search for text in the current document. "
        "Supports plain text search or regex patterns. "
        "Returns all matches with line numbers and context."
    ),
    keywords=["search", "find", "regex", "pattern", "document", "code"],
)
def search_document(
    query: str,
    is_regex: bool = False,
    case_sensitive: bool = False,
    max_results: int = 20,
) -> str:
    """
    Search for text in the active document.
    
    Args:
        query: The search query (text or regex pattern).
        is_regex: Whether to treat query as a regex pattern.
        case_sensitive: Whether the search should be case-sensitive.
        max_results: Maximum number of results to return.
    
    """
    content, file_path, _ = _get_active_document_content()
    
    if content is None:
        return "Error: No document is currently open in the document editor."
    
    try:
        lines = content.split("\n")
        matches = []
        
        # Compile the pattern
        flags = 0 if case_sensitive else re.IGNORECASE
        if is_regex:
            try:
                pattern = re.compile(query, flags)
            except re.error as e:
                return f"Error: Invalid regex pattern: {e}"
        else:
            # Escape special characters for literal search
            pattern = re.compile(re.escape(query), flags)
        
        # Search each line
        for line_num, line in enumerate(lines, 1):
            for match in pattern.finditer(line):
                matches.append({
                    "line": line_num,
                    "column": match.start() + 1,
                    "match": match.group(),
                    "context": line.strip()[:100],
                })
                if len(matches) >= max_results:
                    break
            if len(matches) >= max_results:
                break
        
        if not matches:
            return f"No matches found for '{query}' in {file_path or 'document'}"
        
        result = [f"**Found {len(matches)} matches for '{query}':**\n"]
        for m in matches:
            result.append(
                f"  Line {m['line']}, Col {m['column']}: `{m['match']}` in: {m['context']}"
            )
        
        if len(matches) >= max_results:
            result.append(f"\n(Results limited to {max_results} matches)")
        
        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error searching document: {e}")
        return f"Error: Could not search document: {e}"


@tool(
    name="goto_document_line",
    category=ToolCategory.CODE,
    description=(
        "Move the cursor to a specific line in the document editor. "
        "Optionally select a range of text on that line."
    ),
    keywords=["goto", "navigate", "cursor", "line", "document"],
)
def goto_document_line(
    line_number: int,
    column: int = 1,
) -> str:
    """
    Move cursor to a specific position in the document.
    
    Args:
        line_number: The line number to go to (1-indexed).
        column: The column to go to (1-indexed).
    
    """
    editor_widget = _get_document_editor()
    
    if not editor_widget:
        return "Error: No document is currently open in the document editor."
    
    try:
        content = editor_widget.editor.toPlainText()
        lines = content.split("\n")
        total_lines = len(lines)
        
        if line_number < 1 or line_number > total_lines:
            return f"Error: Line {line_number} is out of range (1-{total_lines})"
        
        # Move to the specified position
        cursor = editor_widget.editor.textCursor()
        
        # Find the block (line)
        block = editor_widget.editor.document().findBlockByLineNumber(line_number - 1)
        if block.isValid():
            cursor.setPosition(block.position())
            # Move to column
            line_length = len(block.text())
            col_pos = min(column - 1, line_length)
            cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.MoveAnchor, col_pos)
            editor_widget.editor.setTextCursor(cursor)
            editor_widget.editor.centerCursor()
            
            return f"✓ Cursor moved to line {line_number}, column {column}"
        else:
            return f"Error: Could not find line {line_number}"
    except Exception as e:
        logger.error(f"Error navigating to line: {e}")
        return f"Error: Could not navigate to line: {e}"


@tool(
    name="replace_in_document",
    category=ToolCategory.CODE,
    description=(
        "Find and replace text in the document. "
        "Supports plain text or regex replacement. "
        "Can replace all occurrences or a specific count."
    ),
    keywords=["replace", "find", "substitute", "regex", "document"],
)
def replace_in_document(
    find_text: str,
    replace_text: str,
    is_regex: bool = False,
    case_sensitive: bool = False,
    max_replacements: int = 0,
) -> str:
    """
    Find and replace text in the document.
    
    Args:
        find_text: The text or pattern to find.
        replace_text: The replacement text.
        is_regex: Whether find_text is a regex pattern.
        case_sensitive: Whether the search is case-sensitive.
        max_replacements: Max replacements (0 = all).
    
    """
    editor_widget = _get_document_editor()
    
    if not editor_widget:
        return "Error: No document is currently open in the document editor."
    
    try:
        content = editor_widget.editor.toPlainText()
        
        # Build the pattern
        flags = 0 if case_sensitive else re.IGNORECASE
        if is_regex:
            try:
                pattern = re.compile(find_text, flags)
            except re.error as e:
                return f"Error: Invalid regex pattern: {e}"
        else:
            pattern = re.compile(re.escape(find_text), flags)
        
        # Count matches first
        matches = list(pattern.finditer(content))
        if not matches:
            return f"No matches found for '{find_text}'"
        
        # Perform replacement
        count = max_replacements if max_replacements > 0 else len(matches)
        new_content, num_replaced = pattern.subn(replace_text, content, count=count)
        
        # Update document
        editor_widget.editor.setPlainText(new_content)
        
        return (
            f"✓ Replaced {num_replaced} occurrence(s) of '{find_text}' with '{replace_text}'"
        )
    except Exception as e:
        logger.error(f"Error replacing in document: {e}")
        return f"Error: Could not perform replacement: {e}"


@tool(
    name="save_document",
    category=ToolCategory.CODE,
    description=(
        "Save the current document to disk. "
        "If the document is new (untitled), you must provide a file path."
    ),
    keywords=["save", "write", "file", "document"],
)
def save_document(
    file_path: Optional[str] = None,
) -> str:
    """
    Save the current document.
    
    Args:
        file_path: Optional path to save as (required for new documents).
    
    """
    editor_widget = _get_document_editor()
    
    if not editor_widget:
        return "Error: No document is currently open in the document editor."
    
    try:
        target_path = file_path or editor_widget.current_file_path
        
        if not target_path:
            return "Error: No file path specified. Provide a file_path for new documents."
        
        success = editor_widget.save_file(target_path)
        
        if success:
            return f"✓ Document saved to: {target_path}"
        else:
            return f"Error: Failed to save document to {target_path}"
    except Exception as e:
        logger.error(f"Error saving document: {e}")
        return f"Error: Could not save document: {e}"
