import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from airunner.gui.widgets.nodegraph.nodes.core.variable_types import (
    VariableType,
    get_variable_type_from_string,
)


@dataclass
class Variable:
    """Represents a variable within the node graph context."""

    name: str
    var_type: VariableType
    default_value: Any = None
    id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )  # Unique ID for potential future use

    def set_value(self, value: Any) -> None:
        """Sets the variable's value, converting to the appropriate type if needed.

        Args:
            value: The new value to set
        """
        # Try to convert the value to the appropriate type based on the variable type
        if self.var_type == VariableType.BOOLEAN:
            self.default_value = bool(value)
        elif self.var_type in [
            VariableType.BYTE,
            VariableType.INTEGER,
            VariableType.INTEGER64,
        ]:
            try:
                self.default_value = int(value)
            except (ValueError, TypeError):
                self.default_value = 0
        elif self.var_type in [VariableType.FLOAT, VariableType.DOUBLE]:
            try:
                self.default_value = float(value)
            except (ValueError, TypeError):
                self.default_value = 0.0
        elif self.var_type in [
            VariableType.NAME,
            VariableType.STRING,
            VariableType.TEXT,
        ]:
            self.default_value = str(value) if value is not None else ""
        else:
            # For more complex types, simply assign the value
            self.default_value = value

    def get_value(self) -> Any:
        """Gets the variable's current value.

        Returns:
            The variable's current value
        """
        return self.default_value

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the variable to a dictionary for saving."""
        return {
            "id": self.id,
            "name": self.name,
            "var_type": self.var_type.value,  # Store enum value (string)
            "default_value": self.default_value,  # Note: complex types might need custom serialization
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Variable | None":
        """Deserializes a variable from a dictionary."""
        var_type_str = data.get("var_type")
        var_type = get_variable_type_from_string(var_type_str)
        if not var_type:
            print(
                f"Warning: Unknown variable type '{var_type_str}' encountered during deserialization."
            )
            # Decide how to handle: return None, use a default type, or raise error
            return None  # Or fallback: var_type = VariableType.STRING

        return Variable(
            id=data.get("id", str(uuid.uuid4())),  # Generate new ID if missing
            name=data.get("name", "Unnamed Variable"),
            var_type=var_type,
            default_value=data.get("default_value"),
        )
