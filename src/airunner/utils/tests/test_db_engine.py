"""
Unit tests for db.engine.py.
Covers all branches.
"""

from unittest.mock import MagicMock, patch
import airunner.utils.db.engine as dbengine


def test_get_connection():
    with patch("airunner.utils.db.engine.op.get_bind", return_value=42):
        assert dbengine.get_connection() == 42


def test_get_inspector():
    with patch("airunner.utils.db.engine.get_connection", return_value="conn"), patch(
        "airunner.utils.db.engine.sa.inspect", return_value="inspector"
    ):
        assert dbengine.get_inspector() == "inspector"
