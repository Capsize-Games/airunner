__all__ = [
    "create_worker",
    "get_lat_lon",
    "get_torch_device",
    "get_version",
    "open_file_path",
    "parse_template",
    "get_platform_name",
    "is_linux",
    "is_bsd",
    "is_darwin",
    "is_windows",
    "random_seed",
    "set_widget_state",
    "snap_to_grid",
    "strip_names_from_message",
    "prepare_text_for_tts",
    "replace_unspeakable_characters",
    "strip_emoji_characters",
    "replace_numbers_with_words",
    "replace_misc_with_words",
    "roman_to_int",
]


def __getattr__(name):
    if name == "create_worker":
        from .application.create_worker import create_worker

        return create_worker
    elif name == "get_lat_lon":
        from .location.get_lat_lon import get_lat_lon

        return get_lat_lon
    elif name == "get_torch_device":
        from .application.get_torch_device import get_torch_device

        return get_torch_device
    elif name == "get_version":
        from .application.get_version import get_version

        return get_version
    elif name == "open_file_path":
        from .os.open_file_path import open_file_path

        return open_file_path
    elif name == "parse_template":
        from .llm.parse_template import parse_template

        return parse_template
    elif name == "get_platform_name":
        from .application.platform_info import get_platform_name

        return get_platform_name
    elif name == "is_linux":
        from .application.platform_info import is_linux

        return is_linux
    elif name == "is_bsd":
        from .application.platform_info import is_bsd

        return is_bsd
    elif name == "is_darwin":
        from .application.platform_info import is_darwin

        return is_darwin
    elif name == "is_windows":
        from .application.platform_info import is_windows

        return is_windows
    elif name == "random_seed":
        from .application.random_seed import random_seed

        return random_seed
    elif name == "set_widget_state":
        from .application.set_widget_state import set_widget_state

        return set_widget_state
    elif name == "snap_to_grid":
        from .application.snap_to_grid import snap_to_grid

        return snap_to_grid
    elif name == "strip_names_from_message":
        from .llm.strip_names_from_message import strip_names_from_message

        return strip_names_from_message
    elif name == "prepare_text_for_tts":
        from .llm.text_preprocessing import prepare_text_for_tts

        return prepare_text_for_tts
    elif name == "replace_unspeakable_characters":
        from .llm.text_preprocessing import replace_unspeakable_characters

        return replace_unspeakable_characters
    elif name == "strip_emoji_characters":
        from .llm.text_preprocessing import strip_emoji_characters

        return strip_emoji_characters
    elif name == "replace_numbers_with_words":
        from .llm.text_preprocessing import replace_numbers_with_words

        return replace_numbers_with_words
    elif name == "replace_misc_with_words":
        from .llm.text_preprocessing import replace_misc_with_words

        return replace_misc_with_words
    elif name == "roman_to_int":
        from .llm.text_preprocessing import roman_to_int

        return roman_to_int
    raise AttributeError(f"module {__name__} has no attribute {name}")
