def current_chatbot(settings: dict):
    current_chatbot_name = settings["llm_generator_settings"]["current_chatbot"]
    try:
        current_chatbot = settings["llm_generator_settings"]["saved_chatbots"][current_chatbot_name]
    except KeyError:
        current_chatbot_name = "Default"
        current_chatbot = settings["llm_generator_settings"]["saved_chatbots"][current_chatbot_name]
    return current_chatbot


def update_chatbot(settings, chatbot):
    settings["llm_generator_settings"]["saved_chatbots"][settings["llm_generator_settings"]["current_chatbot"]] = chatbot
    return settings
