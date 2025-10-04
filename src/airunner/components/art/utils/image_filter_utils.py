import importlib
from typing import Any

from airunner.components.art.data.image_filter import ImageFilter
from airunner.components.art.data.image_filter_value import ImageFilterValue


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
