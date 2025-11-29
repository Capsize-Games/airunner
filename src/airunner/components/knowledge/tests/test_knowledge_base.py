"""Tests for the KnowledgeBase class."""

import pytest
import tempfile
from pathlib import Path
from datetime import date

from airunner.components.knowledge.knowledge_base import KnowledgeBase


class TestKnowledgeBase:
    """Test the daily markdown knowledge base."""

    def setup_method(self):
        """Create a temporary knowledge base for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.kb = KnowledgeBase(knowledge_dir=Path(self.temp_dir))

    def test_add_fact_creates_file(self):
        """Test that adding a fact creates today's file."""
        self.kb.add_fact("Test fact", section="Notes")
        
        files = self.kb.list_files()
        assert len(files) == 1
        assert files[0].stem == date.today().isoformat()

    def test_add_fact_to_section(self):
        """Test that facts are added to the correct section."""
        self.kb.add_fact("User is John", section="Identity")
        self.kb.add_fact("User likes coding", section="Interests & Hobbies")
        
        content = self.kb.read_file()
        
        # Check Identity section has the fact
        assert "User is John" in content
        # Check Interests section has the fact
        assert "User likes coding" in content
        
        # Check facts are in correct sections by checking order
        identity_pos = content.find("## Identity")
        interests_pos = content.find("## Interests & Hobbies")
        john_pos = content.find("User is John")
        coding_pos = content.find("User likes coding")
        
        assert identity_pos < john_pos < interests_pos
        assert interests_pos < coding_pos

    def test_facts_have_bullets(self):
        """Test that facts without bullets get them added."""
        self.kb.add_fact("Fact without bullet", section="Notes")
        content = self.kb.read_file()
        assert "- Fact without bullet" in content

    def test_facts_separated_by_blank_lines(self):
        """Test that facts are separated by blank lines."""
        self.kb.add_fact("First fact", section="Notes")
        self.kb.add_fact("Second fact", section="Notes")
        
        content = self.kb.read_file()
        # Should have blank line between facts
        assert "- First fact\n\n- Second fact" in content or \
               "- Second fact\n\n- First fact" in content

    def test_update_fact(self):
        """Test updating a fact."""
        self.kb.add_fact("User lives in Seattle", section="Identity")
        
        success, count = self.kb.update_fact(
            "User lives in Seattle",
            "User lives in Portland"
        )
        
        assert success
        assert count == 1
        
        content = self.kb.read_file()
        assert "User lives in Portland" in content
        assert "User lives in Seattle" not in content

    def test_delete_fact(self):
        """Test deleting a fact."""
        self.kb.add_fact("Fact to delete", section="Notes")
        self.kb.add_fact("Fact to keep", section="Notes")
        
        success, count = self.kb.delete_fact("Fact to delete")
        
        assert success
        assert count == 1
        
        content = self.kb.read_file()
        assert "Fact to delete" not in content
        assert "Fact to keep" in content

    def test_search_keyword(self):
        """Test keyword search."""
        self.kb.add_fact("User works at Google", section="Work & Projects")
        self.kb.add_fact("User likes hiking", section="Interests & Hobbies")
        
        results = self.kb.search("Google")
        
        assert len(results) >= 1
        assert any("Google" in r['line'] for r in results)

    def test_get_context(self):
        """Test context generation for system prompt."""
        self.kb.add_fact("User is named Alice", section="Identity")
        self.kb.add_fact("User works at TechCorp", section="Work & Projects")
        
        context = self.kb.get_context(max_chars=500)
        
        assert "Alice" in context
        assert "TechCorp" in context

    def test_empty_context(self):
        """Test context when no facts exist."""
        context = self.kb.get_context()
        assert context == ""

    def test_regex_update(self):
        """Test regex-based update."""
        self.kb.add_fact("User age is 25", section="Identity")
        
        success, count = self.kb.update_fact(
            r"User age is \d+",
            "User age is 26",
            is_regex=True
        )
        
        assert success
        content = self.kb.read_file()
        assert "User age is 26" in content

    def test_regex_delete(self):
        """Test regex-based delete."""
        self.kb.add_fact("Temporary note 123", section="Notes")
        self.kb.add_fact("Temporary note 456", section="Notes")
        
        success, count = self.kb.delete_fact(
            r"Temporary note \d+",
            is_regex=True
        )
        
        assert success
        assert count == 2
