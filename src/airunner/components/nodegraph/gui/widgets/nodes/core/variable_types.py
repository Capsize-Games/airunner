from enum import Enum
from PySide6.QtGui import QColor


# Define variable types using an Enum
class VariableType(Enum):
    BOOLEAN = "Boolean"
    BYTE = "Byte"
    INTEGER = "Integer"
    INTEGER64 = "Integer64"
    FLOAT = "Float"
    DOUBLE = "Double"
    NAME = "Name"
    STRING = "String"
    TEXT = "Text"
    VECTOR = "Vector"
    ROTATOR = "Rotator"
    TRANSFORM = "Transform"
    OBJECT = "Object"
    CLASS = "Class"


# Define colors for each variable type (inspired by Unreal Engine)
VARIABLE_COLORS = {
    VariableType.BOOLEAN: QColor("#A80000"),
    VariableType.BYTE: QColor("#00A8A8"),
    VariableType.INTEGER: QColor("#1CA864"),
    VariableType.INTEGER64: QColor("#1CA864"),
    VariableType.FLOAT: QColor("#34A834"),
    VariableType.DOUBLE: QColor("#34A834"),
    VariableType.NAME: QColor("#C864C8"),
    VariableType.STRING: QColor("#C800C8"),
    VariableType.TEXT: QColor("#C800C8"),
    VariableType.VECTOR: QColor("#FFC800"),
    VariableType.ROTATOR: QColor("#9AC8FF"),
    VariableType.TRANSFORM: QColor("#E18032"),
    VariableType.OBJECT: QColor("#0064C8"),
    VariableType.CLASS: QColor("#8000FF"),
    None: QColor("#FFFFFF"),
}


def get_variable_color(var_type: VariableType | None) -> QColor:
    """
    Get the color associated with a variable type.

    Args:
        var_type (VariableType): The variable type.

    Returns:
        QColor: Color for the variable type.
    """
    if var_type not in VARIABLE_COLORS:
        return VARIABLE_COLORS[None]

    return VARIABLE_COLORS[var_type]


def get_variable_type_from_string(type_str: str) -> VariableType | None:
    """
    Convert a string representation of a variable type to the enum.

    Args:
        type_str (str): String representation of the variable type.

    Returns:
        VariableType or None: The corresponding variable type enum or None if not found.
    """
    if type_str is None:
        return None

    # Try direct matching with enum values
    for v_type in VariableType:
        if v_type.value == type_str:
            return v_type

    # Try case-insensitive matching as fallback
    for v_type in VariableType:
        if v_type.value.lower() == type_str.lower():
            return v_type

    return None
