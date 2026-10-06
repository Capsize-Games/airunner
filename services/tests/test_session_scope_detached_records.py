"""Records read inside session_scope remain usable after it closes."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from airunner_services.database.session import _get_engine, reset_engine, session_scope


class _Base(DeclarativeBase):
    pass


class _ProbeRecord(_Base):
    __tablename__ = "session_scope_probe"

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column()


@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "AIRUNNER_DATABASE_URL", f"sqlite:///{tmp_path / 'session-scope.sqlite3'}"
    )
    reset_engine()
    _Base.metadata.create_all(_get_engine("default"))
    yield
    reset_engine()


def test_loaded_record_attributes_survive_session_scope(isolated_database) -> None:
    with session_scope() as session:
        record = _ProbeRecord(value="available after close")
        session.add(record)
        session.flush()
        record_id = record.id

    with session_scope() as session:
        detached = session.get(_ProbeRecord, record_id)

    assert detached is not None
    assert detached.value == "available after close"

