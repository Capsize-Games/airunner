"""Service-owned model for LLM-generated custom tools."""

import ast

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from airunner_services.database.base import BaseModel


#: Builtins whose direct invocation can reach the interpreter, filesystem or
#: introspection machinery from inside a restricted namespace.
_DENYLISTED_CALLS = frozenset(
    {
        "exec",
        "eval",
        "compile",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "open",
        "input",
        "breakpoint",
        "help",
        "memoryview",
    }
)

#: Module roots that, if reachable through attribute chains, enable
#: subprocess/IO/socket escape hatches (defence in depth — imports are
#: already rejected).
_DENYLISTED_MODULE_ROOTS = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "socket",
        "ctypes",
        "pathlib",
        "importlib",
    }
)


def _dotted_attribute_chain(node: "ast.Attribute") -> tuple[str, str] | None:
    """Return ``(root, dotted_path)`` for one attribute chain, or None.

    ``os.system`` -> ``("os", "os.system")``; a non-chain attribute (e.g.
    ``x.y`` where ``x`` is not a Name) returns None.
    """
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    parts.reverse()
    return parts[0], ".".join(parts)


class LLMTool(BaseModel):
    """Persist custom LLM tools created by the user or the agent."""

    __tablename__ = "llm_tool"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    code = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True)
    created_by = Column(String, default="user")
    version = Column(Integer, default=1)
    safety_validated = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)

    @property
    def success_rate(self) -> float:
        """Calculate the success rate of tool usage."""
        if self.usage_count == 0:
            return 0.0
        return (self.success_count / self.usage_count) * 100

    def increment_usage(
        self,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Increment usage statistics after one execution."""
        self.usage_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            self.last_error = error
        self.save()

    def validate_code_safety(self) -> tuple[bool, str]:
        """Validate one tool payload with an AST analyzer (issue #2032).

        The previous lowercased-substring deny-list was trivially bypassable
        (``().__class__.__mro__[1].__subclasses__()``, ``getattr``,
        ``breakpoint``, obfuscated names) and produced false positives
        (``open(`` inside a string). This version parses the code and rejects
        dangerous *constructs* structurally, with a specific reason for each.
        It is not a subprocess sandbox — see ``code_sandbox.py`` — but it
        makes ``safety_validated=True`` meaningful.
        """
        try:
            tree = ast.parse(self.code)
        except (SyntaxError, ValueError) as exc:
            return False, f"Code contains syntax errors: {exc}"

        for node in ast.walk(tree):
            # Any import at all is disallowed: tools may only use the
            # restricted namespace provided by ToolManager.
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return False, "import statements are not allowed"

            # Direct calls to builtins that can reach the interpreter or
            # filesystem/introspection machinery.
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in _DENYLISTED_CALLS:
                    return (
                        False,
                        f"call to '{node.func.id}' is not allowed",
                    )

            # Dunder attribute access (__class__, __bases__, __subclasses__,
            # __mro__, __globals__, __builtins__, ...) is the classic escape
            # hatch from restricted namespaces.
            if isinstance(node, ast.Attribute):
                if node.attr.startswith("__") and node.attr.endswith("__"):
                    return (
                        False,
                        f"attribute access to '{node.attr}' is not allowed",
                    )
                chain = _dotted_attribute_chain(node)
                if chain is not None:
                    root, dotted = chain
                    if root in _DENYLISTED_MODULE_ROOTS:
                        return (
                            False,
                            f"access to '{dotted}' is not allowed",
                        )

            # Direct references to the import machinery / builtins mapping.
            if isinstance(node, ast.Name) and node.id in {
                "__builtins__",
                "__loader__",
            }:
                return (
                    False,
                    f"use of '{node.id}' is not allowed",
                )

        if "@tool" not in self.code:
            return False, "Code must use @tool decorator"

        return True, "Code appears safe"

    def validate_and_persist(self) -> tuple[bool, str]:
        """Run safety validation and persist the result.

        ``safety_validated`` is only ever set to True by an actual validation
        pass; anything else is persisted as False (fail closed).
        """
        is_safe, message = self.validate_code_safety()
        self.safety_validated = is_safe
        self.save()
        return is_safe, message

    def __repr__(self) -> str:
        """Return a readable representation for debug output."""
        return (
            f"<LLMTool(name='{self.name}', enabled={self.enabled}, "
            f"version={self.version})>"
        )


def validate_tool_code(code: str) -> tuple[bool, str]:
    """Validate one tool code payload without persisting a record.

    Provides a shared call site for the model's safety validation so GUI and
    API save paths never bypass ``validate_code_safety``.
    """
    return LLMTool(code=code or "").validate_code_safety()


__all__ = ["LLMTool", "validate_tool_code"]