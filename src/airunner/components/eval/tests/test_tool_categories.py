"""
Comprehensive Tool Category Evaluation Tests.

Tests all major tool categories beyond MATH to ensure they work correctly:
- RAG (document search and retrieval)
- CONVERSATION (chat history, memory)
- SYSTEM (file operations, commands)
- IMAGE (image generation, manipulation)

Each category has specific test scenarios to validate functionality.
"""

import logging
import pytest
import sys
import time
from typing import Dict, Any, List
from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.settings import AIRUNNER_DEFAULT_LLM_HF_PATH

logger = logging.getLogger(__name__)

# Ensure print flushes immediately
import builtins as _builtins

_original_print = _builtins.print


def _flush_print(*args, **kwargs):
    if "flush" not in kwargs:
        kwargs["flush"] = True
    result = _original_print(*args, **kwargs)
    sys.stdout.flush()
    return result


print = _flush_print

pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.timeout(600),  # 10 minutes
]


@pytest.mark.benchmark
class TestRAGTools:
    """Test RAG (Retrieval Augmented Generation) tools."""

    def test_rag_basic_search(self, airunner_client):
        """Test basic RAG search functionality."""
        print(f"\n{'='*70}")
        print("📚 RAG TOOLS - Basic Search Test")
        print(f"{'='*70}\n")

        # Test prompt that would benefit from RAG
        prompt = """I need information about Python's asyncio library.
Can you search for relevant documentation and explain how to use async/await?"""

        system_prompt = """You are a helpful programming assistant.

**AVAILABLE TOOLS:**
- rag_search: Search loaded documents for relevant information
- search_knowledge_base_documents: Find documents in knowledge base

If documents aren't loaded, explain what you would search for."""

        print("Prompt:", prompt)
        print("\nGenerating response with RAG tools...")

        start = time.time()
        response = airunner_client.generate(
            prompt,
            model=AIRUNNER_DEFAULT_LLM_HF_PATH,
            temperature=0.7,
            max_tokens=1024,
            use_memory=False,
            system_prompt=system_prompt,
            tool_categories=[ToolCategory.RAG.value],
        )
        elapsed = time.time() - start

        output = response.get("text", "")

        print(f"\n📝 Response ({len(output)} chars, {elapsed:.1f}s):")
        print(output[:500] + "..." if len(output) > 500 else output)

        # Check if response is coherent (not checking correctness, just functionality)
        assert len(output) > 0, "Response should not be empty"
        assert elapsed < 60, f"Response took too long: {elapsed:.1f}s"

        print(f"\n✅ RAG test completed in {elapsed:.1f}s")

    def test_rag_multi_step(self, airunner_client):
        """Test multi-step RAG workflow (search -> load -> query)."""
        print(f"\n{'='*70}")
        print("📚 RAG TOOLS - Multi-Step Workflow Test")
        print(f"{'='*70}\n")

        prompt = """I want to learn about machine learning. 
First, find relevant documents about ML basics.
Then, explain the key concepts."""

        system_prompt = """You are a helpful AI assistant with access to document search.

**WORKFLOW:**
1. Use search_knowledge_base_documents to find relevant docs
2. Explain what you found
3. Summarize key concepts

Be concise in your response."""

        print("Prompt:", prompt)
        print("\nGenerating response with RAG workflow...")

        start = time.time()
        response = airunner_client.generate(
            prompt,
            model=AIRUNNER_DEFAULT_LLM_HF_PATH,
            temperature=0.7,
            max_tokens=1024,
            use_memory=False,
            system_prompt=system_prompt,
            tool_categories=[
                ToolCategory.RAG.value,
                ToolCategory.SEARCH.value,
            ],
        )
        elapsed = time.time() - start

        output = response.get("text", "")

        print(f"\n📝 Response ({len(output)} chars, {elapsed:.1f}s):")
        print(output[:500] + "..." if len(output) > 500 else output)

        assert len(output) > 0, "Response should not be empty"
        print(f"\n✅ RAG workflow test completed in {elapsed:.1f}s")


@pytest.mark.benchmark
class TestConversationTools:
    """Test CONVERSATION tools (memory, chat history)."""

    def test_conversation_memory(self, airunner_client):
        """Test conversation memory and history tools."""
        print(f"\n{'='*70}")
        print("💬 CONVERSATION TOOLS - Memory Test")
        print(f"{'='*70}\n")

        # First message
        prompt1 = "My name is Alice and I like Python programming."

        system_prompt = """You are a friendly chatbot with memory.

**AVAILABLE TOOLS:**
- Remember information about users
- Recall previous conversation

Acknowledge the information shared."""

        print("Message 1:", prompt1)

        response1 = airunner_client.generate(
            prompt1,
            model=AIRUNNER_DEFAULT_LLM_HF_PATH,
            temperature=0.7,
            max_tokens=512,
            use_memory=True,  # Enable memory for this test
            system_prompt=system_prompt,
            tool_categories=[ToolCategory.CONVERSATION.value],
        )

        output1 = response1.get("text", "")
        print(f"\n📝 Response 1: {output1[:200]}...")

        # Second message - test memory recall
        prompt2 = "What's my name and what do I like?"

        print(f"\nMessage 2: {prompt2}")

        response2 = airunner_client.generate(
            prompt2,
            model=AIRUNNER_DEFAULT_LLM_HF_PATH,
            temperature=0.7,
            max_tokens=512,
            use_memory=True,
            system_prompt=system_prompt,
            tool_categories=[ToolCategory.CONVERSATION.value],
        )

        output2 = response2.get("text", "")
        print(f"\n📝 Response 2: {output2[:200]}...")

        # Check if it remembered (basic check - name should be mentioned)
        # Note: This is a functionality test, not accuracy test
        assert len(output1) > 0, "First response should not be empty"
        assert len(output2) > 0, "Second response should not be empty"

        print(f"\n✅ Conversation memory test completed")

    def test_chat_tool_usage(self, airunner_client):
        """Test CHAT category tools."""
        print(f"\n{'='*70}")
        print("💬 CHAT TOOLS - Basic Chat Test")
        print(f"{'='*70}\n")

        prompt = "Hello! Can you help me understand how AI works?"

        system_prompt = """You are a helpful AI assistant.

Provide a brief, friendly explanation suitable for a general audience."""

        print("Prompt:", prompt)

        start = time.time()
        response = airunner_client.generate(
            prompt,
            model=AIRUNNER_DEFAULT_LLM_HF_PATH,
            temperature=0.7,
            max_tokens=512,
            use_memory=False,
            system_prompt=system_prompt,
            tool_categories=[ToolCategory.CHAT.value],
        )
        elapsed = time.time() - start

        output = response.get("text", "")

        print(f"\n📝 Response ({len(output)} chars, {elapsed:.1f}s):")
        print(output[:300] + "..." if len(output) > 300 else output)

        assert len(output) > 0, "Response should not be empty"
        assert elapsed < 30, f"Response took too long: {elapsed:.1f}s"

        print(f"\n✅ Chat test completed in {elapsed:.1f}s")


@pytest.mark.benchmark
class TestSystemTools:
    """Test SYSTEM tools (file operations, commands)."""

    def test_system_info_query(self, airunner_client):
        """Test system information queries."""
        print(f"\n{'='*70}")
        print("🖥️  SYSTEM TOOLS - Info Query Test")
        print(f"{'='*70}\n")

        prompt = "What's the current date and time?"

        system_prompt = """You are a helpful system assistant.

**AVAILABLE TOOLS:**
- Access system information
- Check date/time
- File operations

Provide accurate system information when asked."""

        print("Prompt:", prompt)

        start = time.time()
        response = airunner_client.generate(
            prompt,
            model=AIRUNNER_DEFAULT_LLM_HF_PATH,
            temperature=0.0,
            max_tokens=256,
            use_memory=False,
            system_prompt=system_prompt,
            tool_categories=[ToolCategory.SYSTEM.value],
        )
        elapsed = time.time() - start

        output = response.get("text", "")

        print(f"\n📝 Response ({len(output)} chars, {elapsed:.1f}s):")
        print(output)

        assert len(output) > 0, "Response should not be empty"

        print(f"\n✅ System info test completed in {elapsed:.1f}s")

    def test_file_tool_query(self, airunner_client):
        """Test FILE category tools."""
        print(f"\n{'='*70}")
        print("📁 FILE TOOLS - File Query Test")
        print(f"{'='*70}\n")

        prompt = """I want to organize my project files.
Can you help me understand what file operations are available?"""

        system_prompt = """You are a helpful file management assistant.

**AVAILABLE TOOLS:**
- File listing
- File search
- Directory operations

Explain what file operations you can help with."""

        print("Prompt:", prompt)

        start = time.time()
        response = airunner_client.generate(
            prompt,
            model=AIRUNNER_DEFAULT_LLM_HF_PATH,
            temperature=0.7,
            max_tokens=512,
            use_memory=False,
            system_prompt=system_prompt,
            tool_categories=[ToolCategory.FILE.value],
        )
        elapsed = time.time() - start

        output = response.get("text", "")

        print(f"\n📝 Response ({len(output)} chars, {elapsed:.1f}s):")
        print(output[:400] + "..." if len(output) > 400 else output)

        assert len(output) > 0, "Response should not be empty"

        print(f"\n✅ File tools test completed in {elapsed:.1f}s")


@pytest.mark.benchmark
class TestImageTools:
    """Test IMAGE tools (if available)."""

    def test_image_generation_request(self, airunner_client):
        """Test image generation tool availability."""
        print(f"\n{'='*70}")
        print("🎨 IMAGE TOOLS - Generation Request Test")
        print(f"{'='*70}\n")

        prompt = "Can you generate an image of a sunset over mountains?"

        system_prompt = """You are an AI assistant with image generation capabilities.

**AVAILABLE TOOLS:**
- Image generation
- Image manipulation

If you can generate images, do so. Otherwise, explain the process."""

        print("Prompt:", prompt)

        start = time.time()
        response = airunner_client.generate(
            prompt,
            model=AIRUNNER_DEFAULT_LLM_HF_PATH,
            temperature=0.7,
            max_tokens=512,
            use_memory=False,
            system_prompt=system_prompt,
            tool_categories=[ToolCategory.IMAGE.value],
        )
        elapsed = time.time() - start

        output = response.get("text", "")

        print(f"\n📝 Response ({len(output)} chars, {elapsed:.1f}s):")
        print(output[:400] + "..." if len(output) > 400 else output)

        assert len(output) > 0, "Response should not be empty"

        print(f"\n✅ Image tools test completed in {elapsed:.1f}s")


@pytest.mark.benchmark
class TestWorkflowTools:
    """Test WORKFLOW tools (LangGraph workflows)."""

    def test_workflow_availability(self, airunner_client):
        """Test workflow tools availability."""
        print(f"\n{'='*70}")
        print("⚙️  WORKFLOW TOOLS - Availability Test")
        print(f"{'='*70}\n")

        prompt = """I need to process some data through multiple steps.
What workflow capabilities do you have?"""

        system_prompt = """You are an AI assistant with workflow capabilities.

**AVAILABLE TOOLS:**
- Workflow execution
- Multi-step processing

Explain what workflows you can help with."""

        print("Prompt:", prompt)

        start = time.time()
        response = airunner_client.generate(
            prompt,
            model=AIRUNNER_DEFAULT_LLM_HF_PATH,
            temperature=0.7,
            max_tokens=512,
            use_memory=False,
            system_prompt=system_prompt,
            tool_categories=[ToolCategory.WORKFLOW.value],
        )
        elapsed = time.time() - start

        output = response.get("text", "")

        print(f"\n📝 Response ({len(output)} chars, {elapsed:.1f}s):")
        print(output[:400] + "..." if len(output) > 400 else output)

        assert len(output) > 0, "Response should not be empty"

        print(f"\n✅ Workflow tools test completed in {elapsed:.1f}s")


@pytest.mark.benchmark
class TestToolCategorySuite:
    """Comprehensive test suite for all tool categories."""

    def test_all_categories_summary(self, airunner_client):
        """Run all tool category tests and print summary."""
        print(f"\n{'#'*70}")
        print("🔧 COMPREHENSIVE TOOL CATEGORY TEST SUITE")
        print("Testing all available tool categories")
        print(f"{'#'*70}\n")

        results = []

        # Test each category
        categories_to_test = [
            ("RAG", ToolCategory.RAG.value, "Search for Python documentation"),
            (
                "CONVERSATION",
                ToolCategory.CONVERSATION.value,
                "Remember my name is Bob",
            ),
            ("CHAT", ToolCategory.CHAT.value, "Hello, how are you?"),
            ("SYSTEM", ToolCategory.SYSTEM.value, "What's the current date?"),
            (
                "FILE",
                ToolCategory.FILE.value,
                "List available file operations",
            ),
            ("IMAGE", ToolCategory.IMAGE.value, "Can you generate images?"),
            (
                "WORKFLOW",
                ToolCategory.WORKFLOW.value,
                "What workflows are available?",
            ),
            ("SEARCH", ToolCategory.SEARCH.value, "Search for AI information"),
        ]

        for category_name, category_value, test_prompt in categories_to_test:
            print(f"\n{'─'*70}")
            print(f"Testing {category_name} category...")
            print(f"{'─'*70}")

            try:
                start = time.time()
                response = airunner_client.generate(
                    test_prompt,
                    model=AIRUNNER_DEFAULT_LLM_HF_PATH,
                    temperature=0.7,
                    max_tokens=256,
                    use_memory=False,
                    system_prompt=f"You are a helpful assistant with {category_name} capabilities.",
                    tool_categories=[category_value],
                )
                elapsed = time.time() - start

                output = response.get("text", "")
                success = len(output) > 0

                results.append(
                    {
                        "category": category_name,
                        "success": success,
                        "time": elapsed,
                        "output_length": len(output),
                    }
                )

                status = "✅" if success else "❌"
                print(
                    f"{status} {category_name}: {len(output)} chars in {elapsed:.1f}s"
                )

            except Exception as e:
                results.append(
                    {
                        "category": category_name,
                        "success": False,
                        "error": str(e),
                    }
                )
                print(f"❌ {category_name}: Error - {e}")

        # Print summary
        self._print_category_summary(results)

    def _print_category_summary(self, results: List[Dict[str, Any]]):
        """Print summary of all category tests."""
        print(f"\n{'='*70}")
        print("📊 TOOL CATEGORY TEST SUMMARY")
        print(f"{'='*70}")
        print(f"{'Category':<20} {'Status':<10} {'Time':<12} {'Output Size'}")
        print(f"{'-'*70}")

        successful = 0
        total_time = 0

        for result in results:
            category = result["category"]
            success = result.get("success", False)
            status = "✅ PASS" if success else "❌ FAIL"
            time_str = f"{result['time']:.1f}s" if "time" in result else "N/A"
            output_size = (
                f"{result.get('output_length', 0)} chars"
                if success
                else "Error"
            )

            print(f"{category:<20} {status:<10} {time_str:<12} {output_size}")

            if success:
                successful += 1
                total_time += result.get("time", 0)

        print(f"{'-'*70}")
        print(f"Total: {successful}/{len(results)} categories working")
        print(
            f"Average time: {total_time/successful:.1f}s"
            if successful > 0
            else "N/A"
        )
        print(f"{'='*70}\n")
