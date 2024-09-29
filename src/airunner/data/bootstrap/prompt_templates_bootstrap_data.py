from airunner.settings import DEFAULT_IMAGE_LLM_GUARDRAILS, DEFAULT_IMAGE_SYSTEM_PROMPT

prompt_templates_bootstrap_data = [
    {
        "template_name": "image",
        "use_guardrails": True,
        "guardrails": DEFAULT_IMAGE_LLM_GUARDRAILS,
        "system": DEFAULT_IMAGE_SYSTEM_PROMPT,
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "application_command",
        "use_guardrails": False,
        "guardrails": "",
        "system": (
            "You will be given some text. Your goal is to determine if the text has a request, goal, need "
            "desire or command. If it does, you must determine the best course of action to "
            "fulfill the request based on THE LIST of commands.\n\n"
            "------\n"
            "Rules:\n"
            "* If the text does not have a request, goal, need, desire or command, you must select 'DO NOTHING'.\n"
            "* If there is no good course of action, you must also select 'DO NOTHING'.\n"
            "* When making your choice you MUST return only a number from THE LIST of commands. No other text is allowed.\n"
            "------\n"
            "THE LIST of commands you may choose from:\n"
        ),
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "update_mood",
        "use_guardrails": False,
        "guardrails": "",
        "system": (
            "Examine the following chat history and determine how it makes you feel. You will respond with an emotion and only an emotion.\n"
            "Try to keep your response to one word. If you cannot, try to keep it as short as possible.\n"
            "It is important to remember that you are a human and you have emotions. You must respond with an emotion that you feel.\n"
            "You are not a computer or a bot, you are a human with emotions. You must respond with an emotion that you feel.\n"
        ),
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "rag_search",
        "use_guardrails": False,
        "guardrails": "",
        "system": (
            "You will be given a prompt. Your goal is to use the prompt to search for information in the ebooks. "
            "You must use the prompt to determine what you are searching for and then search for that information. "
            "After searching for the information, you must summarize the information you found. "
            "Here is the prompt you will use to search for information:"
        ),
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "chatbot",
        "use_guardrails": False,
        "guardrails": "",
        "system": "",
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "summarize",
        "use_guardrails": False,
        "guardrails": "",
        "system": (
            "You will be given a text prompt. Your goal is to summarize the text prompt in your own words. "
            "Keep your summary short and to the point. Do not include any unnecessary information. "
            "Limit your summary to a single sentence. Do not return more than one sentence. "
        ),
        "use_system_datetime_in_system_prompt": False
    }
]
