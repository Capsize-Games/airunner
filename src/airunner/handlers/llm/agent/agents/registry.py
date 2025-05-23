"""
Tool and engine registry for dynamic registration and lookup.
"""

class ToolRegistry:
    _tools = {}

    @classmethod
    def register(cls, name):
        def decorator(tool):
            cls._tools[name] = tool
            return tool
        return decorator

    @classmethod
    def get(cls, name):
        return cls._tools.get(name)

    @classmethod
    def all(cls):
        return dict(cls._tools)

class EngineRegistry:
    _engines = {}

    @classmethod
    def register(cls, name):
        def decorator(engine):
            cls._engines[name] = engine
            return engine
        return decorator

    @classmethod
    def get(cls, name):
        return cls._engines.get(name)

    @classmethod
    def all(cls):
        return dict(cls._engines)
