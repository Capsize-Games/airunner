"""
Tests for knowledge browser utilities.
"""

import json
import csv
import tempfile
from pathlib import Path
from datetime import datetime
import pytest

from airunner.components.knowledge.knowledge_browser_utils import (
    KnowledgeExporter,
    KnowledgeBulkOperations,
)
from airunner.components.knowledge.data.models import KnowledgeFact
from airunner.components.data.session_manager import session_scope


@pytest.fixture
def sample_facts():
    """Create sample facts for testing."""
    with session_scope() as session:
        facts = [
            KnowledgeFact(
                text="Python is a programming language",
                category="technology",
                tags="python,programming",
                confidence=0.9,
                verified=True,
                source="test",
                access_count=5,
                enabled=True,
            ),
            KnowledgeFact(
                text="AI Runner is a local AI application",
                category="technology",
                tags="ai,application",
                confidence=0.95,
                verified=True,
                source="test",
                access_count=10,
                enabled=True,
            ),
            KnowledgeFact(
                text="The sky is blue",
                category="nature",
                tags="sky,color",
                confidence=0.8,
                verified=False,
                source="test",
                access_count=2,
                enabled=True,
            ),
        ]
        session.add_all(facts)
        session.flush()
        fact_ids = [f.id for f in facts]

    yield fact_ids

    # Cleanup
    with session_scope() as session:
        session.query(KnowledgeFact).filter(
            KnowledgeFact.id.in_(fact_ids)
        ).delete(synchronize_session=False)


class TestKnowledgeExporter:
    """Test KnowledgeExporter class."""

    def test_export_to_json_all_facts(self, sample_facts):
        """Test exporting all facts to JSON."""
        exporter = KnowledgeExporter()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            output_path = f.name

        try:
            count = exporter.export_to_json(output_path)

            assert count == 3

            # Verify file contents
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert len(data) == 3
            assert data[0]["text"] == "Python is a programming language"
            assert data[0]["category"] == "technology"
            assert data[0]["verified"] is True
            assert "python" in data[0]["tags"]

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_export_to_json_filtered_by_category(self, sample_facts):
        """Test exporting facts filtered by category."""
        exporter = KnowledgeExporter()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            output_path = f.name

        try:
            count = exporter.export_to_json(output_path, category="technology")

            assert count == 2

            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert len(data) == 2
            assert all(fact["category"] == "technology" for fact in data)

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_export_to_json_verified_only(self, sample_facts):
        """Test exporting only verified facts."""
        exporter = KnowledgeExporter()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            output_path = f.name

        try:
            count = exporter.export_to_json(output_path, verified_only=True)

            assert count == 2

            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert len(data) == 2
            assert all(fact["verified"] for fact in data)

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_export_to_csv_all_facts(self, sample_facts):
        """Test exporting all facts to CSV."""
        exporter = KnowledgeExporter()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            output_path = f.name

        try:
            count = exporter.export_to_csv(output_path)

            assert count == 3

            # Verify file contents
            with open(output_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 4  # Header + 3 data rows
            assert rows[0][0] == "ID"
            assert rows[1][1] == "Python is a programming language"
            assert rows[1][2] == "technology"

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_export_to_csv_filtered(self, sample_facts):
        """Test exporting CSV with filters."""
        exporter = KnowledgeExporter()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            output_path = f.name

        try:
            count = exporter.export_to_csv(
                output_path, category="nature", verified_only=False
            )

            assert count == 1

            with open(output_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 2  # Header + 1 data row
            assert rows[1][1] == "The sky is blue"

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_create_backup(self, sample_facts):
        """Test creating a timestamped backup."""
        exporter = KnowledgeExporter()

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = exporter.create_backup(backup_dir=temp_dir)

            assert Path(backup_path).exists()
            assert "knowledge_backup_" in backup_path
            assert backup_path.endswith(".json")

            # Verify backup contents
            with open(backup_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert len(data) == 3


class TestKnowledgeBulkOperations:
    """Test KnowledgeBulkOperations class."""

    def test_bulk_delete(self, sample_facts):
        """Test bulk deleting facts."""
        ops = KnowledgeBulkOperations()

        # Delete first two facts
        deleted_count = ops.bulk_delete(sample_facts[:2])

        assert deleted_count == 2

        # Verify deletion
        with session_scope() as session:
            remaining = (
                session.query(KnowledgeFact)
                .filter(KnowledgeFact.id.in_(sample_facts))
                .count()
            )

            assert remaining == 1

    def test_bulk_verify(self, sample_facts):
        """Test bulk verifying facts."""
        ops = KnowledgeBulkOperations()

        # Verify all facts
        updated_count = ops.bulk_verify(sample_facts, verified=True)

        assert updated_count == 3

        # Check verification status
        with session_scope() as session:
            facts = (
                session.query(KnowledgeFact)
                .filter(KnowledgeFact.id.in_(sample_facts))
                .all()
            )

            assert all(f.verified for f in facts)

    def test_bulk_unverify(self, sample_facts):
        """Test bulk unverifying facts."""
        ops = KnowledgeBulkOperations()

        # Unverify all facts
        updated_count = ops.bulk_verify(sample_facts, verified=False)

        assert updated_count == 3

        # Check verification status
        with session_scope() as session:
            facts = (
                session.query(KnowledgeFact)
                .filter(KnowledgeFact.id.in_(sample_facts))
                .all()
            )

            assert all(not f.verified for f in facts)

    def test_bulk_categorize(self, sample_facts):
        """Test bulk categorizing facts."""
        ops = KnowledgeBulkOperations()

        # Change category for all facts
        updated_count = ops.bulk_categorize(sample_facts, "general_knowledge")

        assert updated_count == 3

        # Verify category change
        with session_scope() as session:
            facts = (
                session.query(KnowledgeFact)
                .filter(KnowledgeFact.id.in_(sample_facts))
                .all()
            )

            assert all(f.category == "general_knowledge" for f in facts)

    def test_bulk_enable_disable(self, sample_facts):
        """Test bulk enabling/disabling facts."""
        ops = KnowledgeBulkOperations()

        # Disable all facts
        updated_count = ops.bulk_enable_disable(sample_facts, enabled=False)

        assert updated_count == 3

        # Verify disabled status
        with session_scope() as session:
            facts = (
                session.query(KnowledgeFact)
                .filter(KnowledgeFact.id.in_(sample_facts))
                .all()
            )

            assert all(not f.enabled for f in facts)

        # Re-enable facts
        updated_count = ops.bulk_enable_disable(sample_facts, enabled=True)

        assert updated_count == 3

        # Verify enabled status
        with session_scope() as session:
            facts = (
                session.query(KnowledgeFact)
                .filter(KnowledgeFact.id.in_(sample_facts))
                .all()
            )

            assert all(f.enabled for f in facts)

    def test_bulk_operations_with_empty_list(self):
        """Test bulk operations with empty fact list."""
        ops = KnowledgeBulkOperations()

        assert ops.bulk_delete([]) == 0
        assert ops.bulk_verify([]) == 0
        assert ops.bulk_categorize([], "test") == 0
        assert ops.bulk_enable_disable([]) == 0

    def test_bulk_operations_with_nonexistent_ids(self):
        """Test bulk operations with nonexistent IDs."""
        ops = KnowledgeBulkOperations()

        # Use IDs that don't exist
        fake_ids = [999999, 999998, 999997]

        assert ops.bulk_delete(fake_ids) == 0
        assert ops.bulk_verify(fake_ids) == 0
        assert ops.bulk_categorize(fake_ids, "test") == 0
        assert ops.bulk_enable_disable(fake_ids) == 0
