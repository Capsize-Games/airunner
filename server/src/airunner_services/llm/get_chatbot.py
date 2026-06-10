"""Service-owned chatbot selection helper."""

from types import SimpleNamespace

from airunner_services.database.models.chatbot import Chatbot
from airunner_services.utils.application.get_logger import get_logger


def _fallback_chatbot() -> SimpleNamespace:
    """Return a minimal chatbot-like object for service-only runtimes."""
    return SimpleNamespace(
        id=None,
        name="Default",
        botname="Computer",
        gender="Male",
        voice_id=None,
        current=True,
        use_cache=True,
        model_version="",
        use_mood=True,
        use_weather_prompt=False,
        use_personality=True,
        use_guardrails=True,
        use_system_instructions=True,
        use_datetime=True,
        assign_names=True,
        use_tool_filter=False,
        use_gpu=True,
        skip_special_tokens=True,
        bot_personality="happy. He loves {{ username }}",
        system_instructions="",
        backstory="",
        use_backstory=True,
        top_p=900,
        min_length=1,
        max_new_tokens=1000,
        repetition_penalty=100,
        do_sample=True,
        early_stopping=True,
        num_beams=1,
        temperature=1000,
        ngram_size=2,
        top_k=10,
        eta_cutoff=10,
        num_return_sequences=1,
        decoder_start_token_id=None,
        length_penalty=100,
        return_result=True,
        prompt_template="Mistral 7B Instruct: Default Chatbot",
        sequences=1,
        model_type="llm",
        dtype="4bit",
        target_files=[],
        target_directories=[],
    )


def get_chatbot():
    """Return the current chatbot or create one default chatbot."""
    eager_load = ["target_files", "target_directories"]
    try:
        chatbot = Chatbot.objects.filter_by_first(
            eager_load=eager_load,
            current=True,
        )
        if chatbot is None:
            chatbot = Chatbot.objects.first(eager_load=eager_load)
        if chatbot is None:
            chatbot = Chatbot.objects.create(name="Foobar")
            if chatbot is not None:
                Chatbot.make_current(chatbot.id)
                chatbot = Chatbot.objects.first(eager_load=eager_load)
        return chatbot
    except Exception as exc:
        get_logger("get_chatbot").error(f"Error getting chatbot: {exc}")
        return _fallback_chatbot()
