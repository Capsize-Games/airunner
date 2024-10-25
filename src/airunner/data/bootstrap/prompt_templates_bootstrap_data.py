from airunner.settings import DEFAULT_IMAGE_LLM_GUARDRAILS, DEFAULT_IMAGE_SYSTEM_PROMPT, \
    DEFAULT_RAG_SEARCH_SYSTEM_PROMPT, DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT, DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT, \
    DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT, DEFAULT_CHATBOT_SYSTEM_PROMPT, DEFAULT_CHATBOT_GUARDRAILS_PROMPT

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
        "system": DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT,
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "update_mood",
        "use_guardrails": False,
        "guardrails": "",
        "system": DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT,
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "rag_search",
        "use_guardrails": False,
        "guardrails": "",
        "system": DEFAULT_RAG_SEARCH_SYSTEM_PROMPT,
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "chatbot",
        "use_guardrails": False,
        "guardrails": DEFAULT_CHATBOT_GUARDRAILS_PROMPT,
        "system": DEFAULT_CHATBOT_SYSTEM_PROMPT,
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "summarize",
        "use_guardrails": False,
        "guardrails": "",
        "system": DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT,
        "use_system_datetime_in_system_prompt": False
    }
]
