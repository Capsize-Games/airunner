"""Public list pagination contracts and migration recovery boundaries."""

from __future__ import annotations

import asyncio
import importlib
from contextlib import contextmanager
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.orm import Session, declarative_base


def test_domain_resource_query_has_default_cap_offset_and_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Public domain queries default and cap rows and honor offset pages."""
    from airunner_services.api.routes import domain_resource_store as store
    from airunner_services.api.routes.domain_resource_contracts import QueryRequest

    test_base = declarative_base()

    class ResourceRow(test_base):
        __tablename__ = "test_domain_page_rows"

        id = sa.Column(sa.Integer, primary_key=True)
        name = sa.Column(sa.String, nullable=False)

    engine = sa.create_engine(f"sqlite:///{tmp_path / 'domain.db'}")
    ResourceRow.__table__.create(engine)
    with engine.begin() as connection:
        connection.execute(
            sa.insert(ResourceRow),
            [{"id": number, "name": f"row-{number}"} for number in range(1, 106)],
        )

    @contextmanager
    def isolated_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(store, "model_class", lambda _domain, _name: ResourceRow)
    monkeypatch.setattr(store, "session_scope", isolated_session)
    try:
        default_page = store.query_records(
            "test", "rows", QueryRequest(order_by=[{"field": "id"}])
        )
        assert [row["id"] for row in default_page["records"]] == list(
            range(1, 101)
        )

        next_page = store.query_records(
            "test",
            "rows",
            QueryRequest(
                order_by=[{"field": "id"}], limit=3, offset=100
            ),
        )
        assert [row["id"] for row in next_page["records"]] == [101, 102, 103]

        capped = store.query_records(
            "test", "rows", QueryRequest(limit=1000, offset=0)
        )
        assert len(capped["records"]) == 105

        for request in (
            QueryRequest(limit=0),
            QueryRequest(limit=-1),
            QueryRequest(limit=1001),
            QueryRequest(offset=-1),
        ):
            with pytest.raises(store.HTTPException) as error:
                store.query_records("test", "rows", request)
            assert error.value.status_code == 400
            assert error.value.detail == "invalid_pagination"
    finally:
        engine.dispose()


def test_conversation_public_list_pages_in_sql_and_keeps_explicit_full_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Conversation list limit reaches SQL before rows are materialized."""
    import airunner_services.database.base_manager as base_manager
    from airunner_services.conversations.conversation_history_manager import (
        ConversationHistoryManager,
    )
    from airunner_services.database.base_manager import RealBaseManager
    from airunner_services.database.models.conversation import Conversation

    engine = sa.create_engine(f"sqlite:///{tmp_path / 'conversations.db'}")
    Conversation.__table__.create(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Conversation(
                    title=f"conversation-{index}",
                    summary=f"summary-{index}",
                    value=[],
                )
                for index in range(1, 6)
            ]
        )
        session.commit()

    @contextmanager
    def isolated_session():
        with Session(engine) as session:
            yield session

    old_manager = Conversation._objects
    monkeypatch.setattr(base_manager, "session_scope", isolated_session)
    Conversation._objects = RealBaseManager(Conversation)
    try:
        history = ConversationHistoryManager()
        page = history.list_conversations(limit=2, offset=1)
        assert [row["id"] for row in page] == [4, 3]

        # Internal callers can still explicitly request historical full reads.
        all_rows = history.list_conversations(limit=0)
        assert [row["id"] for row in all_rows] == [5, 4, 3, 2, 1]
    finally:
        Conversation._objects = old_manager
        engine.dispose()


def test_public_conversation_route_passes_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The HTTP route passes its bounded limit and offset to the manager."""
    from airunner_services.api.routes import conversations as routes

    calls = []

    class FakeManager:
        def list_conversations(self, *, limit, offset):
            calls.append((limit, offset))
            return []

    monkeypatch.setattr(routes, "_manager", FakeManager)
    response = asyncio.run(routes.list_conversations(limit=20, offset=40))
    assert response.conversations == []
    assert calls == [(20, 40)]


def test_event_conversation_lists_are_bounded_and_preview_queries_are_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Event list routes use bounded pages rather than an all-row preload."""
    from airunner_services.api.routes import events_handlers

    calls = []

    class FakeManager:
        def list_conversations(self, *, limit=50, offset=0, chatbot_id=None):
            calls.append((limit, offset, chatbot_id))
            if chatbot_id is None:
                return []
            return [{"chatbot_id": chatbot_id, "summary": "latest"}]

    monkeypatch.setattr(
        events_handlers, "ConversationHistoryManager", FakeManager
    )
    status, _ = events_handlers._conversations("", {"limit": 500, "offset": 3})
    assert status == 200
    assert calls == [(200, 3, None)]

    status, response = events_handlers._previews(
        "", {"chatbot_ids": [3, 5]}
    )
    assert status == 200
    assert response["previews"] == {
        "3": {"preview": "latest", "updated_at": None},
        "5": {"preview": "latest", "updated_at": None},
    }
    assert set(calls[-2:]) == {(1, 0, 3), (1, 0, 5)}

    status, _ = events_handlers._previews(
        "", {"chatbot_ids": list(range(101))}
    )
    assert status == 400



def test_scheduler_database_list_has_explicit_row_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The scheduler table fallback cannot materialize an unbounded table."""
    from contextlib import contextmanager

    from airunner_services.api.routes import art_schedulers

    seen = {}

    class FakeQuery:
        def limit(self, value):
            seen["limit"] = value
            return self

        @staticmethod
        def all():
            return [("Euler",), ("Euler",), ("DDIM",)]

    class FakeSession:
        @staticmethod
        def query(_column):
            return FakeQuery()

    @contextmanager
    def fake_scope():
        yield FakeSession()

    monkeypatch.setattr(art_schedulers, "session_scope", fake_scope)
    assert art_schedulers.stored_scheduler_names() == ["DDIM", "Euler"]
    assert seen["limit"] == art_schedulers._MAX_STORED_SCHEDULERS

def test_dffe_downgrade_rejects_empty_recreation_of_dropped_data(
    tmp_path: Path,
) -> None:
    """SpeechT5 rows remain absent when the downgrade rejects recovery."""
    migration = importlib.import_module(
        "airunner_services.database.alembic.versions."
        "dffe1636eeaf_add_xtts_settings_table"
    )
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'speech-settings.db'}")
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "CREATE TABLE speech_t5_settings "
                    "(id INTEGER PRIMARY KEY, voice TEXT)"
                )
            )
            connection.execute(
                sa.text("INSERT INTO speech_t5_settings VALUES (1, 'local-voice')")
            )
        with engine.connect() as connection:
            operations = MigrationContext.configure(connection)
            with Operations.context(operations):
                migration.upgrade()
                assert "speech_t5_settings" not in sa.inspect(
                    connection
                ).get_table_names()
                with pytest.raises(
                    RuntimeError,
                    match="speech_t5_settings was dropped",
                ):
                    migration.downgrade()
                assert "speech_t5_settings" not in sa.inspect(
                    connection
                ).get_table_names()
    finally:
        engine.dispose()
