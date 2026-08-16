"""GUI-side re-export of the canonical daemon resource store."""

from airunner_services.daemon_client.resource_store import (
    GuiResourceStore,
    LAYER_RESOURCES,
    RESOURCE_DOMAINS,
    RESOURCE_TO_TABLE,
    ResourceRecord,
    SINGLETON_RESOURCES,
    TABLE_TO_RESOURCE,
    get_resource_store,
)

__all__ = [
    "GuiResourceStore",
    "get_resource_store",
    "LAYER_RESOURCES",
    "RESOURCE_DOMAINS",
    "RESOURCE_TO_TABLE",
    "ResourceRecord",
    "SINGLETON_RESOURCES",
    "TABLE_TO_RESOURCE",
]
