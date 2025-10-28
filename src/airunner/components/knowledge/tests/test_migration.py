"""Tests for knowledge migration CLI."""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from airunner.bin.airunner_migrate_knowledge import (
    KnowledgeMigrator,
    KnowledgeMigrationError,
)
from airunner.components.knowledge.data.models import KnowledgeFact
from airunner.components.data.session_manager import session_scope


class TestKnowledgeMigrator:
    """Test cases for KnowledgeMigrator."""

    @pytest.fixture(autouse=True)
    def clean_database(self):
        """Clean knowledge facts from database before each test."""
        with session_scope() as session:
            session.query(KnowledgeFact).delete()
            session.commit()
        yield
        # Clean up after test as well
        with session_scope() as session:
            session.query(KnowledgeFact).delete()
            session.commit()

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_json_path(self, temp_dir):
        """Create sample JSON file with facts."""
        json_path = temp_dir / "user_facts.json"
        facts = [
            {
                "text": "User's name is John",
                "category": "identity",
                "confidence": 0.95,
                "source": "conversation",
                "timestamp": "2024-01-15T10:30:00",
                "metadata": {"verified": True},
            },
            {
                "text": "User lives in Seattle",
                "category": "location",
                "confidence": 0.90,
                "source": "conversation",
                "timestamp": "2024-01-15T10:35:00",
                "metadata": {},
            },
            {
                "text": "User prefers dark mode",
                "category": "preferences",
                "confidence": 0.85,
            },
        ]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(facts, f, indent=2)
        return json_path

    @pytest.fixture
    def empty_json_path(self, temp_dir):
        """Create empty JSON array file."""
        json_path = temp_dir / "empty_facts.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        return json_path

    @pytest.fixture
    def invalid_json_path(self, temp_dir):
        """Create invalid JSON file."""
        json_path = temp_dir / "invalid.json"
        with open(json_path, "w", encoding="utf-8") as f:
            f.write("{invalid json")
        return json_path

    def test_migrator_initialization(self, sample_json_path):
        """Test creating migrator with custom path."""
        migrator = KnowledgeMigrator(json_path=sample_json_path)
        assert migrator.json_path == sample_json_path
        assert migrator.backup_path == sample_json_path.with_suffix(
            ".json.backup"
        )
        assert migrator.migrated_count == 0
        assert migrator.skipped_count == 0
        assert migrator.error_count == 0

    def test_migrator_auto_detect_path(self):
        """Test auto-detecting JSON path from settings."""
        migrator = KnowledgeMigrator()
        assert "knowledge" in str(migrator.json_path)
        assert "user_facts.json" in str(migrator.json_path)

    def test_validate_json_file_success(self, sample_json_path):
        """Test validating valid JSON file."""
        migrator = KnowledgeMigrator(json_path=sample_json_path)
        assert migrator.validate_json_file() is True

    def test_validate_json_file_not_found(self, temp_dir):
        """Test validation fails for missing file."""
        migrator = KnowledgeMigrator(json_path=temp_dir / "nonexistent.json")
        with pytest.raises(
            KnowledgeMigrationError, match="JSON file not found"
        ):
            migrator.validate_json_file()

    def test_validate_json_file_invalid_json(self, invalid_json_path):
        """Test validation fails for invalid JSON."""
        migrator = KnowledgeMigrator(json_path=invalid_json_path)
        with pytest.raises(
            KnowledgeMigrationError, match="Invalid JSON format"
        ):
            migrator.validate_json_file()

    def test_validate_json_file_not_array(self, temp_dir):
        """Test validation fails if JSON is not an array."""
        json_path = temp_dir / "not_array.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"not": "an array"}, f)

        migrator = KnowledgeMigrator(json_path=json_path)
        with pytest.raises(
            KnowledgeMigrationError, match="must contain an array"
        ):
            migrator.validate_json_file()

    def test_create_backup(self, sample_json_path):
        """Test creating backup file."""
        migrator = KnowledgeMigrator(json_path=sample_json_path)
        backup_path = migrator.create_backup()

        assert backup_path.exists()
        assert backup_path == migrator.backup_path

        # Verify backup content matches original
        with open(sample_json_path, "r", encoding="utf-8") as f:
            original = json.load(f)
        with open(backup_path, "r", encoding="utf-8") as f:
            backup = json.load(f)
        assert original == backup

    def test_parse_json_facts(self, sample_json_path):
        """Test parsing facts from JSON."""
        migrator = KnowledgeMigrator(json_path=sample_json_path)
        facts = migrator.parse_json_facts()

        assert len(facts) == 3
        assert facts[0]["text"] == "User's name is John"
        assert facts[1]["category"] == "location"

    def test_parse_json_facts_empty(self, empty_json_path):
        """Test parsing empty JSON array."""
        migrator = KnowledgeMigrator(json_path=empty_json_path)
        facts = migrator.parse_json_facts()
        assert facts == []

    def test_fact_exists_in_db(self, sample_json_path):
        """Test checking if fact exists in database."""
        migrator = KnowledgeMigrator(json_path=sample_json_path)

        # Add a fact to database
        with session_scope() as session:
            fact = KnowledgeFact(
                text="Test fact", category="test", confidence=0.9
            )
            session.add(fact)
            session.commit()

        assert migrator.fact_exists_in_db("Test fact") is True
        assert migrator.fact_exists_in_db("Non-existent fact") is False

    def test_migrate_fact_success(self, sample_json_path):
        """Test migrating single fact."""
        migrator = KnowledgeMigrator(json_path=sample_json_path)

        fact_data = {
            "text": "New fact to migrate",
            "category": "test",
            "confidence": 0.88,
            "source": "test",
            "timestamp": "2024-01-15T12:00:00",
            "metadata": {"key": "value"},
        }

        result = migrator.migrate_fact(fact_data)

        assert result is not None
        assert result.text == "New fact to migrate"
        assert result.category == "test"
        assert result.confidence == 0.88
        assert result.source == "test"
        assert migrator.migrated_count == 1

        # Verify in database
        with session_scope() as session:
            db_fact = (
                session.query(KnowledgeFact)
                .filter_by(text="New fact to migrate")
                .first()
            )
            assert db_fact is not None
            assert db_fact.metadata_json == {"key": "value"}

    def test_migrate_fact_skip_empty_text(self, sample_json_path):
        """Test skipping fact with empty text."""
        migrator = KnowledgeMigrator(json_path=sample_json_path)

        fact_data = {"text": "   ", "category": "test"}
        result = migrator.migrate_fact(fact_data)

        assert result is None
        assert migrator.skipped_count == 1
        assert migrator.migrated_count == 0

    def test_migrate_fact_skip_duplicate(self, sample_json_path):
        """Test skipping fact that already exists."""
        migrator = KnowledgeMigrator(json_path=sample_json_path)

        # Add fact to database first
        with session_scope() as session:
            fact = KnowledgeFact(
                text="Duplicate fact", category="test", confidence=0.9
            )
            session.add(fact)
            session.commit()

        # Try to migrate same fact
        fact_data = {"text": "Duplicate fact", "category": "test"}
        result = migrator.migrate_fact(fact_data)

        assert result is None
        assert migrator.skipped_count == 1

    def test_migrate_fact_handles_timestamp_parsing(self, sample_json_path):
        """Test handling various timestamp formats."""
        migrator = KnowledgeMigrator(json_path=sample_json_path)

        # Valid ISO format
        fact1 = {
            "text": "Fact 1",
            "timestamp": "2024-01-15T10:30:00",
        }
        result1 = migrator.migrate_fact(fact1)
        assert result1 is not None

        # No timestamp (should use current time)
        fact2 = {"text": "Fact 2"}
        result2 = migrator.migrate_fact(fact2)
        assert result2 is not None

        # Invalid timestamp (should use current time)
        fact3 = {"text": "Fact 3", "timestamp": "invalid"}
        result3 = migrator.migrate_fact(fact3)
        assert result3 is not None

    def test_migrate_all_dry_run(self, sample_json_path):
        """Test dry run migration."""
        migrator = KnowledgeMigrator(json_path=sample_json_path)
        stats = migrator.migrate_all(dry_run=True, skip_backup=True)

        assert stats["total"] == 3
        assert stats["migrated"] == 3
        assert stats["skipped"] == 0
        assert stats["errors"] == 0

        # Verify no facts were actually migrated
        with session_scope() as session:
            count = session.query(KnowledgeFact).count()
            assert count == 0  # No facts should be in DB

    def test_migrate_all_success(self, sample_json_path):
        """Test full migration."""
        migrator = KnowledgeMigrator(json_path=sample_json_path)
        stats = migrator.migrate_all(dry_run=False, skip_backup=True)

        assert stats["total"] == 3
        assert stats["migrated"] == 3
        assert stats["skipped"] == 0
        assert stats["errors"] == 0

        # Verify facts were migrated
        with session_scope() as session:
            facts = session.query(KnowledgeFact).all()
            assert len(facts) == 3
            texts = [f.text for f in facts]
            assert "User's name is John" in texts
            assert "User lives in Seattle" in texts
            assert "User prefers dark mode" in texts

    def test_migrate_all_with_backup(self, sample_json_path):
        """Test migration creates backup."""
        migrator = KnowledgeMigrator(json_path=sample_json_path)
        stats = migrator.migrate_all(dry_run=False, skip_backup=False)

        assert stats["migrated"] == 3
        assert migrator.backup_path.exists()

    def test_migrate_all_empty_file(self, empty_json_path):
        """Test migrating empty file."""
        migrator = KnowledgeMigrator(json_path=empty_json_path)
        stats = migrator.migrate_all(dry_run=False, skip_backup=True)

        assert stats["total"] == 0
        assert stats["migrated"] == 0

    def test_migrate_all_handles_errors(self, temp_dir):
        """Test migration handles malformed facts gracefully."""
        json_path = temp_dir / "malformed.json"
        facts = [
            {"text": "Valid fact", "category": "test"},
            {"invalid": "no text field"},  # Missing 'text'
            {"text": "", "category": "test"},  # Empty text
            {"text": "Another valid fact", "category": "test"},
        ]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(facts, f)

        migrator = KnowledgeMigrator(json_path=json_path)
        stats = migrator.migrate_all(dry_run=False, skip_backup=True)

        # Should migrate valid facts and skip/error on invalid ones
        assert stats["total"] == 4
        assert stats["migrated"] == 2  # Only the 2 valid facts
        assert stats["skipped"] >= 1  # Empty text
