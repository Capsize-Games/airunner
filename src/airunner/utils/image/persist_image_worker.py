from typing import Optional, Dict, Any, Tuple
from PIL import Image
from airunner.components.art.data.controlnet_settings import ControlnetSettings
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.data.image_to_image_settings import ImageToImageSettings
from airunner.components.art.data.outpaint_settings import OutpaintSettings


SETTINGS_PERSISTENCE_MAP: Dict[str, Tuple[type, bool]] = {
    "drawing_pad_settings": (DrawingPadSettings, True),
    "controlnet_settings": (ControlnetSettings, True),
    "image_to_image_settings": (ImageToImageSettings, True),
    "outpaint_settings": (OutpaintSettings, True),
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

    model_class, layer_scoped = model_entry
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
        with session_scope() as session:
            if layer_scoped:
                query = session.query(model_class)
                if layer_id is not None:
                    query = query.filter(model_class.layer_id == layer_id)
                setting = query.first()
                if setting is None:
                    setting = model_class(layer_id=layer_id)
                    session.add(setting)
                setattr(setting, column_name, image_binary)
            else:
                setting = (
                    session.query(model_class)
                    .order_by(model_class.id.desc())
                    .first()
                )
                if setting is None:
                    setting = model_class()
                    session.add(setting)
                setattr(setting, column_name, image_binary)
    except Exception as exc:
        return {"error": f"db_error:{exc}", "generation": generation}

    return {
        "generation": generation,
        "table_name": model_class.__tablename__,
        "column_name": column_name,
        "binary": image_binary,
        "settings_key": settings_key,
        "layer_id": layer_id,
    }
