# Models

This directory contains the ORM models for the application.

## User

The `User` model represents a user in the system.

## ORM Return Policy

All BaseManager query methods (get, first, all, filter_by, filter_first, filter, filter_by_first) return dataclass representations of ORM objects for safe, sessionless use. 

**When you need to perform DB updates, flag_modified, or any SQLAlchemy session operation, use the new `get_orm(pk)` method to get a live ORM instance.**

- Use dataclasses for read-only, sessionless access.
- Use ORM objects (via `get_orm`) for mutation, flag_modified, or session-bound operations.

### Example

```python
# Read-only (safe, no session required)
user = User.objects.get(user_id)
print(user.username)

# For DB mutation or flag_modified
user_orm = User.objects.get_orm(user_id)
user_orm.username = "newname"
user_orm.save()
```

### Rationale

This pattern prevents DetachedInstanceError for all read operations, while still allowing safe DB mutation when needed.