"""Foreign-key migration helpers owned by the service package."""

from __future__ import annotations


def create_foreign_key(
    cls,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    constraint_name: str | None = None,
    ondelete: str | None = None,
    onupdate: str | None = None,
) -> None:
    """Create one foreign key."""
    from alembic import op

    dialect_name = getattr(getattr(op.get_bind(), "dialect", None), "name", "")
    if not constraint_name:
        constraint_name = (
            f"fk_{cls.__tablename__}_{'_'.join(local_cols)}_"
            f"{referent_table}_{'_'.join(remote_cols)}"
        )

    op.create_foreign_key(
        constraint_name,
        cls.__tablename__,
        referent_table,
        local_cols,
        remote_cols,
        ondelete=ondelete,
        onupdate=onupdate,
    )


__all__ = ["create_foreign_key"]
