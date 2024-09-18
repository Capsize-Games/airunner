from typing import (
    Any,
    Union,
    List
)

from airunner.settings import DEFAULT_CHATBOT


def get_current_chatbot(
    settings: dict
) -> dict:
    """
    Get the current chatbot from the settings dictionary.
    :param settings:
    :return:
    """
    current_bot = settings["llm_generator_settings"]["current_chatbot"]
    try:
        return settings["llm_generator_settings"]["saved_chatbots"][current_bot]
    except KeyError:
        return DEFAULT_CHATBOT


def set_current_chatbot(
    settings: dict,
    current_bot: dict
) -> dict:
    """
    Set the current chatbot in the settings dictionary.
    :param settings:
    :param current_bot:
    :return:
    """
    settings["llm_generator_settings"]["saved_chatbots"][current_bot["botname"]] = current_bot
    return settings


def get_current_chatbot_property(
    settings: dict,
    property_name: Union[str,
    List[str]]
) -> Any:
    """
    Get a property of the current chatbot from the settings dictionary.
    :param settings:
    :param property_name:
    :return:
    """
    current_bot = get_current_chatbot(settings)
    if isinstance(property_name, list):
        for key in property_name:
            current_bot = current_bot[key]
        return current_bot
    else:
        try:
            return current_bot[property_name]
        except KeyError:
            return current_bot["generator_settings"][property_name]


def set_current_chatbot_property(
    settings: dict,
    property_name: Union[str, List[str]],
    value: Any
) -> dict:
    """
    Set a property of the current chatbot in the settings dictionary.
    :param settings:
    :param property_name:
    :param value:
    :return:
    """
    current_bot = get_current_chatbot(settings)
    if isinstance(property_name, list):
        temp = current_bot
        for key in property_name[:-1]:
            temp = temp[key]
        temp[property_name[-1]] = value
    else:
        current_bot[property_name] = value
    return set_current_chatbot(settings, current_bot)
