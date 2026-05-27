"""GUI resource metadata shared by settings and widget helpers."""

from airunner.daemon_client.resource_store import RESOURCE_TO_TABLE
from airunner.daemon_client.resource_store import TABLE_TO_RESOURCE


class_names = list(RESOURCE_TO_TABLE)
table_to_resource = dict(TABLE_TO_RESOURCE)
resource_to_table = dict(RESOURCE_TO_TABLE)

# Backwards-compatible name during migration.
table_to_class = table_to_resource
