class ToolSingletonMixin:
    """Provides a DRY singleton property helper for tool/engine mixins."""

    def _get_or_create_singleton(self, attr_name, factory, *args, **kwargs):
        if not hasattr(self, attr_name) or getattr(self, attr_name) is None:
            setattr(self, attr_name, factory(*args, **kwargs))
        return getattr(self, attr_name)
