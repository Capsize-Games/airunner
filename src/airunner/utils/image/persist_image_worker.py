from typing import Optional, Dict, Any, Tuple
from PIL import Image

from airunner.daemon_client.resource_store import RESOURCE_TO_TABLE as resource_to_table
from airunner.daemon_client.resource_store import get_resource_store


SETTINGS_PERSISTENCE_MAP: Dict[str, Tuple[str, bool]] = {
    "drawing_pad_settings": ("DrawingPadSettings", True),
    "controlnet_settings": ("ControlnetSettings", True),
    "image_to_image_settings": ("ImageToImageSettings", True),
    "outpaint_settings": ("OutpaintSettings", True),
}


def persist_image_worker(
    settings_key: str,
    layer_id: Optional[int],
    column_name: str,
    pil_image: Optional[Image.Image],
    binary_data: Optional[bytes],
    raw_storage_enabled: bool,
    generation: int,
) -> Dict[str, Any]:
    model_entry = SETTINGS_PERSISTENCE_MAP.get(settings_key)
    if model_entry is None:
        return {
            "error": f"unsupported_settings_key:{settings_key}",
            "generation": generation,
        }

    resource_name, layer_scoped = model_entry
    resource_store = get_resource_store()
    image_binary = binary_data

    if image_binary is None and pil_image is not None:
        try:
            if raw_storage_enabled:
                rgba_image = (
                    pil_image
                    if pil_image.mode == "RGBA"
                    else pil_image.convert("RGBA")
                )
                width, height = rgba_image.size
                header = (
                    b"AIRAW1"
                    + width.to_bytes(4, "big")
                    + height.to_bytes(4, "big")
                )
                image_binary = header + rgba_image.tobytes()
            else:
                image_binary = convert_image_to_binary(pil_image)
        except Exception:
            try:
                image_binary = convert_image_to_binary(
                    pil_image.convert("RGBA")
                )
            except Exception as exc:
                return {
                    "error": f"image_conversion_failed:{exc}",
                    "generation": generation,
                }

    if image_binary is None:
        return {"error": "empty_binary", "generation": generation}

    try:
        if layer_scoped:
            filters = {"layer_id": layer_id}
            setting = resource_store.first(
                resource_name,
                filters=filters,
            )
            if setting is None:
                setting = resource_store.create(resource_name, filters)
        else:
            records = resource_store.query(resource_name)
            setting = max(
                records,
                key=lambda record: getattr(record, "id", 0) or 0,
                default=None,
            )
            if setting is None:
                setting = resource_store.create(resource_name, {})

        resource_store.update(
            resource_name,
            setting.id,
            {column_name: image_binary},
        )
    except Exception as exc:
        return {"error": f"db_error:{exc}", "generation": generation}

    return {
        "generation": generation,
        "table_name": resource_to_table[resource_name],
        "column_name": column_name,
        "binary": image_binary,
        "settings_key": settings_key,
        "layer_id": layer_id,
    }
