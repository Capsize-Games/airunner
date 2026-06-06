"""Detach helpers for long-running project manager ORM objects."""

from __future__ import annotations

from typing import TypeVar

from sqlalchemy.orm import Session, make_transient

DetachedType = TypeVar("DetachedType")


def detach(
    db: Session,
    obj: DetachedType | None,
) -> DetachedType | None:
    """Detach one ORM object so it can be used after the session closes."""
    if obj is None:
        return None
    db.expunge(obj)
    make_transient(obj)
    return obj


def detach_all(
    db: Session,
    objects: list[DetachedType],
) -> list[DetachedType]:
    """Detach a list of ORM objects."""
    for obj in objects:
        detach(db, obj)
    return objects
