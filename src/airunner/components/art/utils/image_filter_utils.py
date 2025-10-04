"""Shared utilities for working with image filters across the application."""

import importlib
from typing import Any, Dict, List, Optional
import logging

from airunner.components.art.data.image_filter import ImageFilter
from airunner.components.art.data.image_filter_value import ImageFilterValue

LOG = logging.getLogger(__name__)


class FilterValueData:
    """Data class to hold filter value information without ORM attachment issues."""

    def __init__(self, filter_value: ImageFilterValue):
        self.id = filter_value.id
        self.name = filter_value.name
        self.value = filter_value.value
        self.value_type = filter_value.value_type
        self.min_value = filter_value.min_value
        self.max_value = filter_value.max_value
        self.image_filter_id = filter_value.image_filter_id

    def save(self):
        """Save the current value back to the database."""
        ImageFilterValue.objects.update(self.id, value=self.value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "value": self.value,
            "value_type": self.value_type,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "image_filter_id": self.image_filter_id,
        }


def get_filter_values(image_filter_id: int) -> List[FilterValueData]:
    """
    Get all filter values for a given image filter.

    Args:
        image_filter_id: The ID of the image filter

    Returns:
        List of FilterValueData objects
    """
    try:
        filter_values = ImageFilterValue.objects.filter_by(
            image_filter_id=image_filter_id
        )
        return [FilterValueData(fv) for fv in filter_values]
    except Exception:
        LOG.exception(
            f"Failed to get filter values for filter {image_filter_id}"
        )
        return []


def get_filter_by_name(filter_name: str) -> Optional[ImageFilter]:
    """
    Get an ImageFilter by name.

    Args:
        filter_name: The name of the filter

    Returns:
        ImageFilter object or None
    """
    try:
        print(f"[get_filter_by_name] Querying for filter: '{filter_name}'")
        results = ImageFilter.objects.filter_by(name=filter_name)
        print(f"[get_filter_by_name] Query results type: {type(results)}")
        print(
            f"[get_filter_by_name] Query results length: {len(results) if results else 0}"
        )

        # filter_by returns a list, not a query object
        result = results[0] if results else None

        if result:
            print(
                f"[get_filter_by_name] Found filter with name='{result.name}', id={result.id}"
            )
        else:
            # Debug: Let's see what filters are actually in the database
            all_filters = ImageFilter.objects.all()
            print(f"[get_filter_by_name] No filter found. All filters in DB:")
            for f in all_filters:
                print(
                    f"  - id={f.id}, name='{f.name}', display_name='{f.display_name}'"
                )
        return result
    except Exception as e:
        print(f"[get_filter_by_name] EXCEPTION: {e}")
        LOG.exception(f"Failed to get filter by name: {filter_name}")
        return None


def build_filter_kwargs(
    filter_values: List[FilterValueData],
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build keyword arguments for filter instantiation from filter values.

    Args:
        filter_values: List of FilterValueData objects
        overrides: Optional dictionary of parameter overrides

    Returns:
        Dictionary of kwargs ready for filter instantiation
    """
    kwargs: Dict[str, Any] = {}
    overrides = overrides or {}

    for fv in filter_values:
        # Start with the database value
        value = fv.value

        # Apply type conversion
        if fv.value_type == "int":
            try:
                value = int(value)
            except (ValueError, TypeError):
                pass
        elif fv.value_type == "float":
            try:
                value = float(value)
            except (ValueError, TypeError):
                pass
        elif fv.value_type == "bool":
            value = value == "True" if isinstance(value, str) else bool(value)

        # Apply override if provided
        if fv.name in overrides:
            value = overrides[fv.name]

        kwargs[fv.name] = value

    return kwargs


def build_filter_instance(
    filter_name: str, overrides: Optional[Dict[str, Any]] = None
) -> Optional[Any]:
    """
    Build a filter instance from its name and optional parameter overrides.

    Args:
        filter_name: The name of the filter to instantiate
        overrides: Optional dictionary of parameter overrides

    Returns:
        Filter instance or None if failed
    """
    try:
        # Get the filter definition
        imgf = get_filter_by_name(filter_name)
        if not imgf:
            LOG.warning(f"Filter not found: {filter_name}")
            return None

        # Get filter values
        filter_values = get_filter_values(imgf.id)

        # Build kwargs
        kwargs = build_filter_kwargs(filter_values, overrides)

        # Import and instantiate
        module = importlib.import_module(
            f"airunner.components.art.filters.{imgf.name}"
        )
        filter_class = getattr(module, imgf.filter_class)
        return filter_class(**kwargs)

    except Exception:
        LOG.exception(f"Failed to build filter instance: {filter_name}")
        return None


def get_all_filter_names() -> List[str]:
    """
    Get a list of all available filter names.

    Returns:
        List of filter names
    """
    try:
        filters = ImageFilter.objects.all() or []
        return [f.name for f in filters]
    except Exception:
        LOG.exception("Failed to get filter names")
        return []


def build_filter_object_from_model(image_filter: ImageFilter) -> Any:
    """Construct and return a filter instance from an ImageFilter model.

    This mirrors the logic currently in FilterWindow.filter_object but is
    factored out so other code (like auto-apply on generation) can reuse it.
    """
    if not image_filter:
        return None

    module = importlib.import_module(
        f"airunner.components.art.filters.{image_filter.name}"
    )
    class_ = getattr(module, image_filter.filter_class)
    kwargs = {}

    filter_values = ImageFilterValue.objects.filter_by(
        image_filter_id=image_filter.id
    )

    for image_filter_value in filter_values:
        val_type = image_filter_value.value_type
        val = image_filter_value.value
        if val_type == "int":
            val = int(val)
        elif val_type == "float":
            val = float(val)
        elif val_type == "bool":
            val = val == "True"
        kwargs[image_filter_value.name] = val

    return class_(**kwargs)
