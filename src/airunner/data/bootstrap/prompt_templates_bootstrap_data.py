from airunner.settings import AIRUNNER_DEFAULT_IMAGE_LLM_GUARDRAILS, AIRUNNER_DEFAULT_IMAGE_SYSTEM_PROMPT, \
    AIRUNNER_DEFAULT_RAG_SEARCH_SYSTEM_PROMPT, AIRUNNER_DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT, AIRUNNER_DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT, \
    AIRUNNER_DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT, AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT, AIRUNNER_DEFAULT_CHATBOT_GUARDRAILS_PROMPT

prompt_templates_bootstrap_data = [
    {
        "template_name": "image",
        "use_guardrails": True,
        "guardrails": AIRUNNER_DEFAULT_IMAGE_LLM_GUARDRAILS,
        "system": AIRUNNER_DEFAULT_IMAGE_SYSTEM_PROMPT,
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "application_command",
        "use_guardrails": False,
        "guardrails": "",
        "system": AIRUNNER_DEFAULT_APPLICATION_COMMAND_SYSTEM_PROMPT,
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "update_mood",
        "use_guardrails": False,
        "guardrails": "",
        "system": AIRUNNER_DEFAULT_UPDATE_MOOD_SYSTEM_PROMPT,
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "rag_search",
        "use_guardrails": False,
        "guardrails": "",
        "system": AIRUNNER_DEFAULT_RAG_SEARCH_SYSTEM_PROMPT,
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "chatbot",
        "use_guardrails": False,
        "guardrails": AIRUNNER_DEFAULT_CHATBOT_GUARDRAILS_PROMPT,
        "system": AIRUNNER_DEFAULT_CHATBOT_SYSTEM_PROMPT,
        "use_system_datetime_in_system_prompt": False
    },
    {
        "template_name": "summarize",
        "use_guardrails": False,
        "guardrails": "",
        "system": AIRUNNER_DEFAULT_SUMMARIZE_CHAT_SYSTEM_PROMPT,
        "use_system_datetime_in_system_prompt": False
    }
]
