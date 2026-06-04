import base64
import io
import PIL
from PIL import Image

RAW_MAGIC = b"AIRAW1"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _validate_or_none(binary_data: bytes):
    """Quick sanity filter: if not raw or PNG signature, skip libpng parse.

    Prevents libpng read errors by avoiding attempts to decode clearly invalid data.
    """
    if not binary_data or len(binary_data) < 10:
        return None
    if binary_data.startswith(RAW_MAGIC) or binary_data.startswith(PNG_MAGIC):
        # For PNG, do additional validation to prevent libpng errors
        if binary_data.startswith(PNG_MAGIC):
            # Check for minimum PNG file size and IHDR chunk
            if len(binary_data) < 33:  # PNG header + IHDR minimum
                return None
            # Verify IHDR chunk exists at position 8
            if binary_data[12:16] != b"IHDR":
                return None
            # Check for IEND chunk (PNG must end with this)
            if not binary_data.endswith(b"\x00\x00\x00\x00IEND\xaeB`\x82"):
                # Try to find IEND chunk anywhere in the data
                if b"IEND\xaeB`\x82" not in binary_data:
                    return None
        return binary_data
    # Allow small headers of other PIL-supported formats (JPEG etc.) if they match
    if binary_data[:2] in (b"\xff\xd8",):  # JPEG
        return binary_data
    return None


def _try_raw_decode(binary_data: bytes):
    """Attempt to decode the custom raw format.

    Format: b"AIRAW1" + 4B width (big endian) + 4B height + RGBA bytes.
    """
    if not binary_data or not isinstance(binary_data, (bytes, bytearray)):
        return None
    if not binary_data.startswith(RAW_MAGIC) or len(binary_data) < 14:
        return None
    try:
        w = int.from_bytes(binary_data[6:10], "big")
        h = int.from_bytes(binary_data[10:14], "big")
        rgba = binary_data[14:]
        if len(rgba) != w * h * 4:
            return None
        # Use frombuffer then copy to detach from original bytes (prevents Qt null issues)
        img = Image.frombuffer("RGBA", (w, h), rgba, "raw", "RGBA", 0, 1)
        return img.copy()
    except Exception:
        return None


def _maybe_base64_decode(binary_data):
    """If the data looks like base64 text, attempt to decode it.

    This supports legacy storage paths where images were base64 encoded.
    """
    if isinstance(binary_data, str):
        # Treat as base64 string
        try:
            return base64.b64decode(
                binary_data.encode("utf-8"), validate=False
            )
        except Exception:
            return None
    # Heuristic: ASCII-only and length reasonable/mod 4 -> try decode
    if isinstance(binary_data, (bytes, bytearray)):
        head = binary_data[:64]
        if (
            all(chr(b).isalnum() or chr(b) in "+/=\n\r" for b in head)
            and len(binary_data) % 4 == 0
        ):
            try:
                decoded = base64.b64decode(binary_data, validate=False)
                # Only accept if decoded resembles raw or PNG
                if decoded.startswith(RAW_MAGIC) or decoded.startswith(
                    PNG_MAGIC
                ):
                    return decoded
            except Exception:
                return None
    return None


def _validate_or_none(binary_data: bytes):
    """Quick sanity filter: if not raw or PNG signature, skip libpng parse.

    Prevents libpng read errors by avoiding attempts to decode clearly invalid data.
    """
    if not binary_data or len(binary_data) < 10:
        return None
    if binary_data.startswith(RAW_MAGIC) or binary_data.startswith(PNG_MAGIC):
        # For PNG, do additional validation to prevent libpng errors
        if binary_data.startswith(PNG_MAGIC):
            # Check for minimum PNG file size and IHDR chunk
            if len(binary_data) < 33:  # PNG header + IHDR minimum
                return None
            # Verify IHDR chunk exists at position 8
            if binary_data[12:16] != b"IHDR":
                return None
        return binary_data
    # Allow small headers of other PIL-supported formats (JPEG etc.) if they match
    if binary_data[:2] in (b"\xff\xd8",):  # JPEG
        return binary_data
    return None


def convert_binary_to_image(binary_data) -> Image:  # type: ignore[override]
    if binary_data is None:
        return None

    # Normalize to bytes
    if isinstance(binary_data, memoryview):
        binary_data = binary_data.tobytes()

    if isinstance(binary_data, str):
        maybe = _maybe_base64_decode(binary_data)
        binary_data = (
            maybe if maybe is not None else binary_data.encode("utf-8")
        )

    # Try raw fast path
    raw_img = _try_raw_decode(binary_data)
    if raw_img is not None:
        return raw_img

    # Maybe legacy base64 in bytes
    if not (
        binary_data.startswith(PNG_MAGIC) or binary_data.startswith(RAW_MAGIC)
    ):
        maybe = _maybe_base64_decode(binary_data)
        if maybe:
            binary_data = maybe
            raw_img = _try_raw_decode(binary_data)
            if raw_img is not None:
                return raw_img

    # Validate before PNG decode to avoid libpng spew
    validated = _validate_or_none(binary_data)
    if validated is None:
        # Debug trace for invalid header
        try:
            snippet = binary_data[:16]
        except Exception:
            pass
        return None

    try:
        bytes_ = io.BytesIO(validated)
        img = Image.open(bytes_)
        # Additional validation: try to access basic properties
        _ = img.size  # This will trigger libpng read if needed
        img.load()  # Force decode to raise early if corrupt
        return img
    except PIL.UnidentifiedImageError as e:
        print(
            f"[convert_binary_to_image] UnidentifiedImageError len={len(validated)} msg={e}"
        )
        return None
    except OSError as e:
        # This catches libpng errors and other image format errors
        print(
            f"[convert_binary_to_image] OSError (likely libpng/format issue) len={len(validated)} msg={e}"
        )
        return None
    except Exception as e:
        print(
            f"[convert_binary_to_image] Generic decode failure len={len(validated)} msg={e} type={type(e).__name__}"
        )
        return None
