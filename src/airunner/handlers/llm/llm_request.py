from dataclasses import dataclass
from typing import Optional, Dict
from airunner.data.models import Chatbot, LLMGeneratorSettings
from airunner.data.session_manager import session_scope


@dataclass
class LLMRequest:
    do_sample: bool = True
    early_stopping: bool = True
    eta_cutoff: int = 200
    length_penalty: float = 1.0
    max_new_tokens: int = 200
    min_length: int = 1
    no_repeat_ngram_size: int = 2
    num_beams: int = 1
    num_return_sequences: int = 1
    repetition_penalty: float = 1.0
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 0.9
    use_cache: bool = True

    def to_dict(self) -> Dict:
        min_val = 0.0001

        length_penalty = self.length_penalty
        repetition_penalty = self.repetition_penalty
        top_p = self.top_p
        temperature = self.temperature

        if length_penalty < min_val:
            length_penalty = min_val

        if repetition_penalty < min_val:
            repetition_penalty = min_val

        if top_p < min_val:
            top_p = min_val

        if temperature < min_val:
            temperature = min_val

        return {
            "do_sample": self.do_sample,
            "early_stopping": self.early_stopping,
            "eta_cutoff": self.eta_cutoff,
            "length_penalty": length_penalty,
            "max_new_tokens": self.max_new_tokens,
            "min_length": self.min_length,
            "no_repeat_ngram_size": self.no_repeat_ngram_size,
            "num_beams": self.num_beams,
            "num_return_sequences": self.num_return_sequences,
            "repetition_penalty": repetition_penalty,
            "temperature": temperature,
            "top_k": self.top_k,
            "top_p": top_p,
            "use_cache": self.use_cache,
        }

    @classmethod
    def from_values(
        cls,
        do_sample: bool,
        early_stopping: bool,
        eta_cutoff: int,
        length_penalty: float,
        max_new_tokens: int,
        min_length: int,
        no_repeat_ngram_size: int,
        num_beams: int,
        num_return_sequences: int,
        repetition_penalty: float,
        temperature: float,
        top_k: int,
        top_p: float,
        use_cache: bool,
    ) -> 'LLMRequest':
        return cls(
            do_sample = do_sample,
            early_stopping = early_stopping,
            eta_cutoff = eta_cutoff,
            length_penalty = length_penalty / 1000.0,
            max_new_tokens = max_new_tokens,
            min_length = min_length,
            no_repeat_ngram_size = no_repeat_ngram_size,
            num_beams = num_beams,
            num_return_sequences = num_return_sequences,
            repetition_penalty = repetition_penalty / 100.0,
            temperature = temperature / 10000.0,
            top_k = top_k,
            top_p = top_p / 1000.0,
            use_cache = use_cache,
        )
        

    @classmethod
    def from_chatbot(
        cls, 
        chatbot_id: int = None
    ) -> 'LLMRequest':
        with session_scope() as session:
            with session.begin():
                query = session.query(
                    Chatbot
                )
                if chatbot_id:
                    query = query.filter(
                        Chatbot.id == chatbot_id
                    )
                chatbot = query.first()
                return cls.from_values(
                    do_sample=chatbot.do_sample,
                    early_stopping=chatbot.early_stopping,
                    eta_cutoff=chatbot.eta_cutoff,
                    length_penalty=chatbot.length_penalty,
                    max_new_tokens=chatbot.max_new_tokens,
                    min_length=chatbot.min_length,
                    no_repeat_ngram_size=chatbot.ngram_size,
                    num_beams=chatbot.num_beams,
                    num_return_sequences=chatbot.num_return_sequences,
                    repetition_penalty=chatbot.repetition_penalty,
                    temperature=chatbot.temperature,
                    top_k=chatbot.top_k,
                    top_p=chatbot.top_p,
                    use_cache=chatbot.use_cache
                )

    @classmethod
    def from_llm_settings(
        cls, 
        llm_settings_id: Optional[int] = None
    ) -> 'LLMRequest':
        with session_scope() as session:
            with session.begin():
                query = llm_settings = session.query(
                    LLMGeneratorSettings
                )
                if llm_settings_id:
                    query = query.filter(
                        LLMGeneratorSettings.id == llm_settings_id
                    )
                llm_settings = query.first()
                if llm_settings.override_parameters:
                    return cls.from_values(
                        do_sample=llm_settings.do_sample,
                        early_stopping=llm_settings.early_stopping,
                        eta_cutoff=llm_settings.eta_cutoff,
                        length_penalty=llm_settings.length_penalty,
                        max_new_tokens=llm_settings.max_new_tokens,
                        min_length=llm_settings.min_length,
                        no_repeat_ngram_size=llm_settings.ngram_size,
                        num_beams=llm_settings.num_beams,
                        num_return_sequences=llm_settings.sequences,
                        repetition_penalty=llm_settings.repetition_penalty,
                        temperature=llm_settings.temperature,
                        top_k=llm_settings.top_k,
                        top_p=llm_settings.top_p,
                        use_cache=llm_settings.use_cache
                    )
                else:
                    return cls.from_chatbot(
                        llm_settings.current_chatbot
                    )

    @classmethod
    def from_default(cls) -> 'LLMRequest':
        return cls.from_llm_settings()