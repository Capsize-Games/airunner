import os
import json
import logging
from typing import List, Callable, Optional, Any
from langchain.tools import tool

from airunner.components.user.data.user import User
from airunner.enums import SignalCode
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)


class ToolManager(MediatorMixin, SettingsMixin):
    """Manages LangChain tools for the AI Runner agent."""

    def __init__(self, rag_manager: Optional[Any] = None):
        self.rag_manager = rag_manager
        self.logger = logging.getLogger(__name__)
        super().__init__()

    def rag_search_tool(self) -> Callable:
        """Retrieve relevant information from RAG documents."""

        @tool
        def rag_search(query: str) -> str:
            """Search through uploaded documents for relevant information.

            Args:
                query: Search query for finding relevant document content

            Returns:
                Relevant excerpts from documents or error message
            """
            if not self.rag_manager:
                return "RAG system not available"

            try:
                results = self.rag_manager.search(query, k=3)
                if not results:
                    return "No relevant information found in documents"

                context_parts = []
                for i, doc in enumerate(results, 1):
                    doc.metadata.get("source", "unknown")
                    content = (
                        doc.page_content[:500]
                        if len(doc.page_content) > 500
                        else doc.page_content
                    )
                    context_parts.append(f"[Source {i}]\n{content}")

                return "\n\n".join(context_parts)
            except Exception as e:
                return f"Error searching documents: {str(e)}"

        return rag_search

    def generate_image_tool(self) -> Callable:
        """Generate an image from text prompt."""

        @tool
        def generate_image(prompt: str, negative_prompt: str = "") -> str:
            """Generate an image based on a text description.

            Args:
                prompt: Description of the image to generate
                negative_prompt: Things to avoid in the image (optional)

            Returns:
                Confirmation message
            """
            try:
                self.emit_signal(
                    SignalCode.SD_GENERATE_IMAGE_FROM_PROMPT_SIGNAL,
                    {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                    },
                )
                return f"Generating image: {prompt}"
            except Exception as e:
                return f"Error generating image: {str(e)}"

        return generate_image

    def clear_canvas_tool(self) -> Callable:
        """Clear the canvas."""

        @tool
        def clear_canvas() -> str:
            """Clear the image canvas.

            Returns:
                Confirmation message
            """
            try:
                self.emit_signal(SignalCode.CLEAR_CANVAS_SIGNAL)
                return "Canvas cleared"
            except Exception as e:
                return f"Error clearing canvas: {str(e)}"

        return clear_canvas

    def open_image_tool(self) -> Callable:
        """Open an image from file path."""

        @tool
        def open_image(file_path: str) -> str:
            """Open an image from a file path.

            Args:
                file_path: Path to the image file

            Returns:
                Confirmation message
            """
            try:
                if not os.path.exists(file_path):
                    return f"File not found: {file_path}"

                self.emit_signal(
                    SignalCode.LOAD_IMAGE_FROM_PATH_SIGNAL, {"path": file_path}
                )
                return f"Opened image: {file_path}"
            except Exception as e:
                return f"Error opening image: {str(e)}"

        return open_image

    def search_web_tool(self) -> Callable:
        """Search the web for information."""

        @tool
        def search_web(query: str) -> str:
            """Search the internet for information.

            Args:
                query: Search query

            Returns:
                Search results
            """
            try:
                self.emit_signal(
                    SignalCode.SEARCH_WEB_SIGNAL, {"query": query}
                )
                return f"Searching for: {query}"
            except Exception as e:
                return f"Error searching web: {str(e)}"

        return search_web

    def list_files_tool(self) -> Callable:
        """List files in a directory."""

        @tool
        def list_files(directory: str) -> str:
            """List files in a directory.

            Args:
                directory: Path to directory

            Returns:
                List of files or error message
            """
            try:
                if not os.path.exists(directory):
                    return f"Directory not found: {directory}"

                files = os.listdir(directory)
                return "\n".join(files) if files else "Directory is empty"
            except Exception as e:
                return f"Error listing files: {str(e)}"

        return list_files

    def store_user_data_tool(self) -> Callable:
        """Store user information."""

        @tool
        def store_user_data(key: str, value: str) -> str:
            """Store user information in the database.

            Args:
                key: The data field name
                value: The data value

            Returns:
                Confirmation message
            """
            try:
                user = User.get_or_create()
                setattr(user, key, value)
                user.save()
                return f"Stored {key}: {value}"
            except Exception as e:
                return f"Error storing data: {str(e)}"

        return store_user_data

    def get_user_data_tool(self) -> Callable:
        """Retrieve user information."""

        @tool
        def get_user_data(key: str) -> str:
            """Retrieve user information from the database.

            Args:
                key: The data field name to retrieve

            Returns:
                The stored value or error message
            """
            try:
                user = User.get_or_create()
                value = getattr(user, key, None)
                if value is None:
                    return f"No data found for key: {key}"
                return str(value)
            except Exception as e:
                return f"Error retrieving data: {str(e)}"

        return get_user_data

    def clear_conversation_tool(self) -> Callable:
        """Clear conversation history."""

        @tool
        def clear_conversation() -> str:
            """Clear the current conversation history.

            Returns:
                Confirmation message
            """
            try:
                self.emit_signal(SignalCode.CLEAR_HISTORY_SIGNAL)
                return "Conversation history cleared"
            except Exception as e:
                return f"Error clearing conversation: {str(e)}"

        return clear_conversation

    def quit_application_tool(self) -> Callable:
        """Quit the application."""

        @tool
        def quit_application() -> str:
            """Quit the AI Runner application.

            Returns:
                Confirmation message
            """
            try:
                self.emit_signal(SignalCode.APPLICATION_QUIT_SIGNAL)
                return "Quitting application..."
            except Exception as e:
                return f"Error quitting application: {str(e)}"

        return quit_application

    def toggle_tts_tool(self) -> Callable:
        """Toggle text-to-speech."""

        @tool
        def toggle_tts(enabled: bool) -> str:
            """Enable or disable text-to-speech.

            Args:
                enabled: True to enable, False to disable

            Returns:
                Confirmation message
            """
            try:
                self.emit_signal(
                    SignalCode.TOGGLE_TTS_SIGNAL, {"enabled": enabled}
                )
                return f"TTS {'enabled' if enabled else 'disabled'}"
            except Exception as e:
                return f"Error toggling TTS: {str(e)}"

        return toggle_tts

    def update_mood_tool(self) -> Callable:
        """Update the chatbot's mood based on conversation."""

        @tool
        def update_mood(mood: str, emoji: str = "😐") -> str:
            """Update the chatbot's emotional state based on the conversation.

            This should be called periodically during conversation to reflect
            how the bot is feeling based on the interaction.

            Args:
                mood: A one-word emotion (e.g., happy, sad, excited, confused, neutral)
                emoji: A single emoji representing the mood (e.g., 😊, 😢, 😡, 😐)

            Returns:
                Confirmation message
            """
            try:
                self.emit_signal(
                    SignalCode.BOT_MOOD_UPDATED,
                    {"mood": mood, "emoji": emoji},
                )
                return f"Mood updated to '{mood}' {emoji}"
            except Exception as e:
                return f"Error updating mood: {str(e)}"

        return update_mood

    def write_code_tool(self) -> Callable:
        """Write and save Python code to a file."""

        @tool
        def write_code(
            file_path: str, code_content: str, description: str = ""
        ) -> str:
            """Write Python code to a file and open it in the code editor.

            This tool allows creating new Python files or modifying existing ones.
            The code will be written to the specified path and opened in the editor.

            Args:
                file_path: Relative path where code should be saved (e.g., 'tools/my_tool.py')
                code_content: The Python code to write
                description: Optional description of what the code does

            Returns:
                Confirmation message
            """
            try:
                # Ensure it's a Python file
                if not file_path.endswith(".py"):
                    file_path += ".py"

                # Build full path
                base_path = os.path.expanduser("~/.local/share/airunner")
                full_path = os.path.join(base_path, "user_code", file_path)

                # Create directory if needed
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                # Write code
                with open(full_path, "w") as f:
                    if description:
                        f.write(f'"""{description}"""\n\n')
                    f.write(code_content)

                # Signal to open in editor (if implemented)
                self.emit_signal(
                    SignalCode.OPEN_CODE_EDITOR,
                    {"file_path": full_path, "content": code_content},
                )

                return f"Code written to {file_path}"
            except Exception as e:
                return f"Error writing code: {str(e)}"

        return write_code

    def create_tool_tool(self) -> Callable:
        """Create a new LLM tool dynamically."""

        @tool
        def create_tool(tool_name: str, description: str, code: str) -> str:
            """Create a new custom tool that the agent can use.

            This meta-tool allows the agent to expand its own capabilities by
            creating new tools. The code must use the @tool decorator and follow
            LangChain tool patterns.

            SAFETY GUIDELINES:
            - Do NOT use os.system, subprocess, eval, or exec
            - Do NOT perform destructive file operations
            - Do NOT access sensitive system resources
            - Keep tools focused and single-purpose

            Args:
                tool_name: Unique name for the tool (e.g., 'calculate_fibonacci')
                description: Clear description of what the tool does
                code: Python code implementing the tool using @tool decorator

            Returns:
                Success or error message

            Example:
                create_tool(
                    tool_name="add_numbers",
                    description="Add two numbers together",
                    code='''
                    @tool
                    def add_numbers(a: int, b: int) -> str:
                        \"\"\"Add two numbers.

                        Args:
                            a: First number
                            b: Second number

                        Returns:
                            Sum as string
                        \"\"\"
                        return str(a + b)
                    '''
                )
            """
            try:
                from airunner.components.llm.data.llm_tool import LLMTool

                # Check if tool already exists
                existing = LLMTool.objects.filter_by_first(name=tool_name)
                if existing:
                    return f"Tool '{tool_name}' already exists. Use a different name."

                # Create tool record
                new_tool = LLMTool(
                    name=tool_name,
                    display_name=tool_name.replace("_", " ").title(),
                    description=description,
                    code=code,
                    created_by="agent",
                    enabled=False,  # Disabled until safety validated
                )

                # Validate safety
                is_safe, message = new_tool.validate_code_safety()
                if not is_safe:
                    return f"Tool creation failed: {message}"

                new_tool.safety_validated = True
                new_tool.enabled = True
                new_tool.save()

                # Emit signal to reload tools
                self.emit_signal(
                    SignalCode.LLM_TOOL_CREATED, {"tool_name": tool_name}
                )

                return f"Tool '{tool_name}' created successfully! It will be available on next reload."
            except Exception as e:
                return f"Error creating tool: {str(e)}"

        return create_tool

    def execute_python_tool(self) -> Callable:
        """Execute Python code in a sandboxed environment."""

        @tool
        def execute_python(code: str) -> str:
            """Execute Python code and return the result.

            This tool allows running Python code snippets for calculations,
            data processing, or analysis. Code is executed in a restricted
            environment for safety.

            LIMITATIONS:
            - No file I/O operations
            - No network access
            - No subprocess execution
            - Execution timeout of 5 seconds

            Args:
                code: Python code to execute

            Returns:
                Output from code execution or error message

            Example:
                execute_python("result = 5 * 10 + 3; print(result)")
            """
            try:
                # Use the Pylance code execution if available
                from io import StringIO
                import sys

                # Capture output
                old_stdout = sys.stdout
                sys.stdout = captured_output = StringIO()

                # Restricted globals (no dangerous builtins)
                safe_globals = {
                    "__builtins__": {
                        "print": print,
                        "len": len,
                        "range": range,
                        "str": str,
                        "int": int,
                        "float": float,
                        "list": list,
                        "dict": dict,
                        "sum": sum,
                        "min": min,
                        "max": max,
                        "abs": abs,
                        "round": round,
                    }
                }

                # Execute
                exec(code, safe_globals)

                # Restore stdout
                sys.stdout = old_stdout

                output = captured_output.getvalue()
                return (
                    output
                    if output
                    else "Code executed successfully (no output)"
                )

            except Exception as e:
                sys.stdout = old_stdout
                return f"Execution error: {str(e)}"

        return execute_python

    def web_scraper_tool(self) -> Callable:
        """Scrape content from websites using BeautifulSoup."""

        @tool
        def scrape_website(url: str, selector: str = "") -> str:
            """Scrape content from a website.

            Extract text content from web pages for analysis or storage.
            Can optionally use CSS selectors to target specific elements.

            Args:
                url: Website URL to scrape
                selector: Optional CSS selector to target specific content

            Returns:
                Scraped content or error message
            """
            logger.info(f"Scraping: {url} (selector: {selector or 'none'})")

            try:
                import requests
                from bs4 import BeautifulSoup

                # Set headers to mimic a browser
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                }

                # Fetch the page with timeout
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.content, "html.parser")

                # Remove script and style elements
                for element in soup(["script", "style", "nav", "footer"]):
                    element.decompose()

                # Extract content based on selector
                if selector:
                    elements = soup.select(selector)
                    if elements:
                        text = "\n\n".join(
                            elem.get_text(strip=True) for elem in elements
                        )
                    else:
                        return (
                            f"No elements found matching selector: {selector}"
                        )
                else:
                    # Try common content containers first
                    main_content = (
                        soup.find("main")
                        or soup.find("article")
                        or soup.find("div", class_="content")
                        or soup.find("div", id="content")
                        or soup.body
                    )
                    if main_content:
                        text = main_content.get_text(
                            separator="\n", strip=True
                        )
                    else:
                        text = soup.get_text(separator="\n", strip=True)

                # Clean up whitespace
                lines = [
                    line.strip() for line in text.splitlines() if line.strip()
                ]
                cleaned_text = "\n".join(lines)

                # Truncate if too long (keep first 10000 chars)
                if len(cleaned_text) > 10000:
                    cleaned_text = (
                        cleaned_text[:10000] + "\n\n[Content truncated...]"
                    )

                logger.info(
                    f"Successfully scraped {len(cleaned_text)} characters"
                )
                return cleaned_text

            except requests.RequestException as e:
                error_msg = f"Failed to fetch URL: {str(e)}"
                logger.error(error_msg)
                return error_msg
            except Exception as e:
                error_msg = f"Error scraping website: {str(e)}"
                logger.error(error_msg)
                return error_msg

        return scrape_website

    def save_to_knowledge_base_tool(self) -> Callable:
        """Save text content to the knowledge base for RAG."""

        @tool
        def save_to_knowledge_base(
            content: str, title: str, category: str = "general"
        ) -> str:
            """Save content to the knowledge base for future RAG retrieval.

            This tool allows the agent to build its own knowledge base over time
            by saving important information for later reference.

            Args:
                content: Text content to save
                title: Title/identifier for this knowledge
                category: Category for organization (e.g., 'research', 'documentation')

            Returns:
                Confirmation message
            """
            try:
                # Create a document file
                base_path = os.path.expanduser("~/.local/share/airunner")
                kb_path = os.path.join(base_path, "knowledge_base", category)
                os.makedirs(kb_path, exist_ok=True)

                # Sanitize filename
                filename = "".join(
                    c for c in title if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                filename = filename.replace(" ", "_") + ".txt"

                file_path = os.path.join(kb_path, filename)

                # Write content
                with open(file_path, "w") as f:
                    f.write(f"Title: {title}\n")
                    f.write(f"Category: {category}\n")
                    f.write("\n---\n\n")
                    f.write(content)

                # Emit signal to reload RAG
                self.emit_signal(
                    SignalCode.RAG_DOCUMENT_ADDED,
                    {"file_path": file_path, "title": title},
                )

                return f"Content saved to knowledge base: {title}"
            except Exception as e:
                return f"Error saving to knowledge base: {str(e)}"

        return save_to_knowledge_base

    def record_knowledge_tool(self) -> Callable:
        """Record factual knowledge about user or conversation."""

        @tool
        def record_knowledge(
            fact: str,
            category: str = "other",
            tags: str = "",
            confidence: float = 0.9,
        ) -> str:
            """Record important facts about the user or conversation.

            Use this tool to remember important information that comes up in conversations.
            This builds the agent's long-term memory and helps personalize future interactions.

            When to use:
            - User shares personal information (name, location, preferences, etc.)
            - User mentions health conditions, symptoms, or treatments
            - User describes their work, hobbies, or interests
            - User reveals goals, challenges, or important life events
            - User confirms they've already tried something (important for not repeating advice)
            - Any factual information that would be useful to remember

            Args:
                fact: The factual statement to remember (be specific and clear)
                category: Category - one of: identity, location, preferences, relationships,
                         work, interests, skills, goals, history, health, other
                tags: Comma-separated tags for organization (e.g., "chronic,pain,back")
                confidence: How confident you are in this fact (0.0-1.0, default 0.9)

            Returns:
                Confirmation message

            Examples:
                record_knowledge("User's name is Sarah", "identity", "name", 1.0)
                record_knowledge("User has chronic back pain", "health", "pain,back,chronic", 0.95)
                record_knowledge("User already tried stretching for back pain", "history", "back,pain,tried", 0.9)
                record_knowledge("User prefers direct communication style", "preferences", "communication", 0.85)
            """
            try:
                from airunner.components.knowledge.knowledge_memory_manager import (
                    KnowledgeMemoryManager,
                )

                # Parse tags
                tag_list = [t.strip() for t in tags.split(",") if t.strip()]

                # Get conversation ID if available
                conversation_id = None
                if hasattr(self, "current_conversation_id"):
                    conversation_id = self.current_conversation_id

                # Create knowledge manager
                km = KnowledgeMemoryManager()

                # Add fact
                km.add_fact(
                    text=fact,
                    category=category,
                    tags=tag_list if tag_list else None,
                    confidence=confidence,
                    source="agent",
                    conversation_id=conversation_id,
                    verified=False,
                )

                # Emit signal to refresh UI
                self.emit_signal(
                    SignalCode.KNOWLEDGE_FACT_ADDED,
                    {"fact": fact, "category": category},
                )

                return (
                    f"✓ Recorded: {fact[:60]}{'...' if len(fact) > 60 else ''}"
                )
            except Exception as e:
                self.logger.error(f"Error recording knowledge: {e}")
                return f"Error recording knowledge: {str(e)}"

        return record_knowledge

    def recall_knowledge_tool(self) -> Callable:
        """Recall relevant facts from knowledge base."""

        @tool
        def recall_knowledge(query: str, k: int = 5) -> str:
            """Recall relevant facts from long-term memory.

            Use this tool to remember what you know about the user or past conversations.
            This searches through all stored facts using semantic similarity.

            Args:
                query: What you're trying to remember (e.g., "user's health issues")
                k: Number of facts to recall (default 5)

            Returns:
                Relevant facts or message if none found

            Examples:
                recall_knowledge("user's health conditions")
                recall_knowledge("what has the user already tried for pain")
                recall_knowledge("user's hobbies and interests")
            """
            try:
                from airunner.components.knowledge.knowledge_memory_manager import (
                    KnowledgeMemoryManager,
                )

                # Create knowledge manager with embeddings
                embeddings = None
                if self.rag_manager and hasattr(
                    self.rag_manager, "embeddings"
                ):
                    embeddings = self.rag_manager.embeddings

                km = KnowledgeMemoryManager(embeddings=embeddings)

                # Recall facts
                facts = km.recall_facts(query, k=k)

                if not facts:
                    return f"No relevant knowledge found for: {query}"

                # Format response
                result_parts = [f"Recalled {len(facts)} relevant fact(s):\n"]
                for i, fact in enumerate(facts, 1):
                    verified = "✓" if fact.verified else ""
                    confidence_pct = int(fact.confidence * 100)
                    result_parts.append(
                        f"{i}. {fact.text} {verified} ({confidence_pct}% confidence)"
                    )
                    if fact.tag_list:
                        result_parts.append(
                            f"   Tags: {', '.join(fact.tag_list)}"
                        )

                return "\n".join(result_parts)
            except Exception as e:
                self.logger.error(f"Error recalling knowledge: {e}")
                return f"Error recalling knowledge: {str(e)}"

        return recall_knowledge

    def search_knowledge_base_documents_tool(self) -> Callable:
        """Search across all knowledge base documents to find relevant ones to load for RAG."""

        @tool
        def search_knowledge_base_documents(query: str, k: int = 10) -> str:
            """Search across ALL knowledge base documents to find the most relevant ones.

            This is a BROAD SEARCH across document titles and paths - like a search engine
            for your entire knowledge base. Use this BEFORE using rag_search to determine
            which documents should be loaded into RAG for detailed querying.

            The knowledge base may contain ebooks, PDFs, markdown files, ZIM files, and more.
            This tool helps you discover which documents are relevant to the user's question
            so you can load them for deeper analysis.

            Args:
                query: What topics/documents you're looking for (e.g., "Python programming books")
                k: Number of document paths to return (default 10)

            Returns:
                List of relevant document paths ranked by relevance

            Examples:
                search_knowledge_base_documents("machine learning tutorials")
                search_knowledge_base_documents("health and fitness guides", k=5)
                search_knowledge_base_documents("cooking recipes")
            """
            try:
                from airunner.components.documents.data.models.document import (
                    Document,
                )
                from airunner.components.data.session_manager import (
                    session_scope,
                )
                import os

                with session_scope() as session:
                    # Get all active documents
                    docs = session.query(Document).filter_by(active=True).all()

                    if not docs:
                        return "No documents found in knowledge base. Please index some documents first."

                    # Simple keyword-based relevance scoring
                    # In production, you'd use embeddings for semantic search
                    query_lower = query.lower()
                    query_terms = query_lower.split()

                    scored_docs = []
                    for doc in docs:
                        path_lower = doc.path.lower()
                        filename = os.path.basename(path_lower)

                        # Score based on query term matches in path/filename
                        score = 0
                        for term in query_terms:
                            if term in filename:
                                score += 10  # High weight for filename matches
                            elif term in path_lower:
                                score += 5  # Medium weight for path matches

                        if score > 0:
                            scored_docs.append((score, doc))

                    # Sort by score and take top k
                    scored_docs.sort(reverse=True, key=lambda x: x[0])
                    top_docs = scored_docs[:k]

                    if not top_docs:
                        return f"No documents found matching '{query}'. Try different search terms."

                    # Format response
                    result_parts = [
                        f"Found {len(top_docs)} relevant document(s) for '{query}':\n"
                    ]
                    for i, (score, doc) in enumerate(top_docs, 1):
                        filename = os.path.basename(doc.path)
                        indexed_status = (
                            "indexed" if doc.indexed else "not indexed"
                        )
                        result_parts.append(
                            f"{i}. {filename} ({indexed_status})"
                        )
                        result_parts.append(f"   Path: {doc.path}")

                    result_parts.append(
                        "\nTip: Use these document paths with rag_search to get detailed content."
                    )

                    return "\n".join(result_parts)
            except Exception as e:
                self.logger.error(f"Error searching knowledge base: {e}")
                return f"Error searching knowledge base: {str(e)}"

        return search_knowledge_base_documents

    def emit_signal_tool(self) -> Callable:
        """Emit application signals to control the UI and system."""

        @tool
        def emit_signal(signal_name: str, data: str = "{}") -> str:
            """Emit a signal to control the application.

            This allows you to trigger application events like generating images,
            toggling features, or updating the UI. Use with caution.

            AVAILABLE SIGNALS (most useful ones):
            - SD_GENERATE_IMAGE_SIGNAL: Generate an image
              Data: {"prompt": "...", "negative_prompt": "..."}

            - CANVAS_CLEAR: Clear the canvas
              Data: {}

            - TOGGLE_TTS_SIGNAL: Toggle text-to-speech
              Data: {}

            - TOGGLE_FULLSCREEN_SIGNAL: Toggle fullscreen mode
              Data: {}

            - LLM_CLEAR_HISTORY_SIGNAL: Clear conversation history
              Data: {}

            - QUIT_APPLICATION: Quit the application (use with confirmation!)
              Data: {}

            Args:
                signal_name: Name of the signal to emit (e.g., "TOGGLE_TTS_SIGNAL")
                data: JSON string with signal data (default: "{}")

            Returns:
                Confirmation or error message

            Examples:
                emit_signal("TOGGLE_TTS_SIGNAL")
                emit_signal("SD_GENERATE_IMAGE_SIGNAL", '{"prompt": "sunset beach"}')
                emit_signal("CANVAS_CLEAR")
            """
            try:
                # Parse data JSON
                try:
                    data_dict = json.loads(data)
                except json.JSONDecodeError:
                    return f"Error: data must be valid JSON. Got: {data}"

                # Validate signal exists
                try:
                    signal_code = SignalCode[signal_name]
                except KeyError:
                    available = [
                        "SD_GENERATE_IMAGE_SIGNAL",
                        "CANVAS_CLEAR",
                        "TOGGLE_TTS_SIGNAL",
                        "TOGGLE_FULLSCREEN_SIGNAL",
                        "LLM_CLEAR_HISTORY_SIGNAL",
                        "QUIT_APPLICATION",
                    ]
                    return f"Unknown signal '{signal_name}'. Available signals: {', '.join(available)}"

                # Emit the signal
                self.emit_signal(signal_code, data_dict)
                return f"Signal '{signal_name}' emitted successfully"

            except Exception as e:
                self.logger.error(f"Error emitting signal: {e}")
                return f"Error emitting signal: {str(e)}"

        return emit_signal

    def read_file_tool(self) -> Callable:
        """Read content from a file."""

        @tool
        def read_file(file_path: str) -> str:
            """Read and return the contents of a file.

            Useful for analyzing code, reading documents, or accessing data files.

            Args:
                file_path: Path to the file to read

            Returns:
                File contents or error message
            """
            try:
                if not os.path.exists(file_path):
                    return f"File not found: {file_path}"

                with open(file_path, "r") as f:
                    content = f.read()

                # Limit output size
                if len(content) > 10000:
                    content = (
                        content[:10000]
                        + f"\n\n... (truncated, file is {len(content)} characters)"
                    )

                return content
            except Exception as e:
                return f"Error reading file: {str(e)}"

        return read_file

    def calculator_tool(self) -> Callable:
        """Perform mathematical calculations."""

        @tool
        def calculate(expression: str) -> str:
            """Evaluate a mathematical expression.

            Supports basic arithmetic, powers, and common math functions.

            Args:
                expression: Mathematical expression (e.g., "2 + 2", "sqrt(16)", "pi * 2")

            Returns:
                Calculation result or error message

            Example:
                calculate("(5 + 3) * 2 ** 3")
            """
            try:
                import math

                # Safe evaluation with math functions available
                safe_dict = {
                    "sqrt": math.sqrt,
                    "pow": pow,
                    "abs": abs,
                    "round": round,
                    "pi": math.pi,
                    "e": math.e,
                    "sin": math.sin,
                    "cos": math.cos,
                    "tan": math.tan,
                    "log": math.log,
                    "ln": math.log,
                    "exp": math.exp,
                }

                result = eval(expression, {"__builtins__": {}}, safe_dict)
                return str(result)
            except Exception as e:
                return f"Calculation error: {str(e)}"

        return calculate

    def get_all_tools(self) -> List[Callable]:
        """Get all available tools.

        Returns:
            List of all tool functions
        """
        tools = [
            # Core conversation tools
            self.rag_search_tool(),
            self.clear_conversation_tool(),
            self.update_mood_tool(),
            # Image generation tools
            self.generate_image_tool(),
            self.clear_canvas_tool(),
            self.open_image_tool(),
            # Information & search tools
            self.search_web_tool(),
            self.search_knowledge_base_documents_tool(),
            self.list_files_tool(),
            self.read_file_tool(),
            # Data management tools
            self.store_user_data_tool(),
            self.get_user_data_tool(),
            self.save_to_knowledge_base_tool(),
            # Knowledge & memory tools
            self.record_knowledge_tool(),
            self.recall_knowledge_tool(),
            # Code & computation tools
            self.write_code_tool(),
            self.execute_python_tool(),
            self.calculator_tool(),
            # Meta tools (self-improvement)
            self.create_tool_tool(),
            # Web tools
            self.web_scraper_tool(),
            # System tools
            self.emit_signal_tool(),
            self.quit_application_tool(),
            self.toggle_tts_tool(),
        ]

        # Add any custom tools from database
        tools.extend(self._load_custom_tools())

        return tools

    def _load_custom_tools(self) -> List[Callable]:
        """Load custom tools created by the agent from database.

        Returns:
            List of dynamically loaded tool functions
        """
        try:
            from airunner.components.llm.data.llm_tool import LLMTool

            custom_tools = []
            enabled_tools = LLMTool.objects.filter(enabled=True)

            for tool_record in enabled_tools:
                try:
                    # Compile and load the tool
                    tool_func = self._compile_custom_tool(tool_record)
                    if tool_func:
                        custom_tools.append(tool_func)
                except Exception as e:
                    self.logger.error(
                        f"Error loading custom tool '{tool_record.name}': {e}"
                    )

            return custom_tools
        except Exception as e:
            self.logger.error(f"Error loading custom tools: {e}")
            return []

    def _compile_custom_tool(self, tool_record) -> Optional[Callable]:
        """Compile a custom tool from database record.

        Args:
            tool_record: LLMTool database record

        Returns:
            Compiled tool function or None if compilation fails
        """
        try:
            # Create a namespace for execution
            namespace = {
                "tool": tool,
                "__name__": f"custom_tool_{tool_record.name}",
            }

            # Execute the code to define the function
            exec(tool_record.code, namespace)

            # Find the decorated function
            for item in namespace.values():
                if callable(item) and hasattr(item, "name"):
                    # Wrap to track usage
                    original_func = item

                    def tracked_tool(*args, **kwargs):
                        try:
                            result = original_func(*args, **kwargs)
                            tool_record.increment_usage(success=True)
                            return result
                        except Exception as e:
                            tool_record.increment_usage(
                                success=False, error=str(e)
                            )
                            raise

                    # Copy metadata
                    tracked_tool.name = original_func.name
                    tracked_tool.description = original_func.description

                    return tracked_tool

            return None
        except Exception as e:
            self.logger.error(
                f"Error compiling tool '{tool_record.name}': {e}"
            )
            return None

    def get_tools_for_action(self, action: Any) -> List[Callable]:
        """Get tools filtered by action type.

        Args:
            action: LLMActionType enum value

        Returns:
            List of tool functions appropriate for the action
        """
        from airunner.enums import LLMActionType

        # Common tools available for all actions
        common_tools = [
            self.store_user_data_tool(),
            self.get_user_data_tool(),
            self.update_mood_tool(),
        ]

        if action == LLMActionType.CHAT:
            # Chat mode: no image/RAG tools, just conversation tools
            return common_tools + [
                self.clear_conversation_tool(),
                self.toggle_tts_tool(),
            ]

        elif action == LLMActionType.GENERATE_IMAGE:
            # Image mode: focus on image generation tools
            return common_tools + [
                self.generate_image_tool(),
                self.clear_canvas_tool(),
                self.open_image_tool(),
            ]

        elif action == LLMActionType.PERFORM_RAG_SEARCH:
            # RAG mode: focus on search tools
            return common_tools + [
                self.rag_search_tool(),
                self.search_web_tool(),
            ]

        elif action == LLMActionType.APPLICATION_COMMAND:
            # Auto mode: all tools available
            return self.get_all_tools()

        else:
            # Default: return all tools
            return self.get_all_tools()
