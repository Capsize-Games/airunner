

def create_foreign_key(
    cls,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    constraint_name: str | None = None,
    ondelete: str | None = None,
    onupdate: str | None = None,
) -> None:
    """Create a foreign key constraint from a model class to another table, using batch_alter_table for SQLite compatibility.

    Args:
        cls: SQLAlchemy model class (source table).
        referent_table (str): Name of the referenced table.
        local_cols (list[str]): Local column names.
        remote_cols (list[str]): Referenced column names.
        constraint_name (str|None): Name of the constraint (optional).
        ondelete (str|None): ON DELETE action.
        onupdate (str|None): ON UPDATE action.
    """
    from alembic import op

    # Alembic batch mode requires a constraint name
    if not constraint_name:
        constraint_name = f"fk_{cls.__tablename__}_{'_'.join(local_cols)}_{referent_table}_{'_'.join(remote_cols)}"
    with op.batch_alter_table(
        cls.__tablename__, recreate="always"
    ) as batch_op:
        batch_op.create_foreign_key(
            constraint_name,
            referent_table,
            local_cols,
            remote_cols,
            ondelete=ondelete,
            onupdate=onupdate,
        )
