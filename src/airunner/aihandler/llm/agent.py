import datetime
import json
import time
import traceback
from typing import AnyStr
import torch
import threading
from PySide6.QtCore import QObject
from transformers import StoppingCriteria

from airunner.aihandler.logger import Logger
from airunner.json_extractor import JSONExtractor
from airunner.mediator_mixin import MediatorMixin
from airunner.enums import SignalCode, LLMChatRole, LLMActionType, ImageCategory
from airunner.utils import get_torch_device, clear_memory
from airunner.windows.main.settings_mixin import SettingsMixin


class ExternalConditionStoppingCriteria(StoppingCriteria):
    def __init__(self, external_condition_callable):
        super().__init__()
        self.external_condition_callable = external_condition_callable

    def __call__(self, inputs_ids, scores):
        return self.external_condition_callable()


class AIRunnerAgent(
    QObject,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, *args, **kwargs):
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        self.model = kwargs.pop("model", None)
        self.tokenizer = kwargs.pop("tokenizer", None)
        self.streamer = kwargs.pop("streamer", None)
        self.tools = kwargs.pop("tools", None)
        self.chat_template = kwargs.pop("chat_template", None)
        self.username = kwargs.pop("username", None)
        self.botname = kwargs.pop("botname", None)
        self.bot_mood = kwargs.pop("bot_mood", None)
        self.bot_personality = kwargs.pop("bot_personality", None)
        self.min_length = kwargs.pop("min_length", None)
        self.max_length = kwargs.pop("max_length", None)
        self.num_beams = kwargs.pop("num_beams", None)
        self.do_sample = kwargs.pop("do_sample", None)
        self.top_k = kwargs.pop("top_k", None)
        self.eta_cutoff = kwargs.pop("eta_cutoff", None)
        self.sequences = kwargs.pop("sequences", None)
        self.early_stopping = kwargs.pop("early_stopping", None)
        self.repetition_penalty = kwargs.pop("repetition_penalty", None)
        self.temperature = kwargs.pop("temperature", None)
        self.is_mistral = kwargs.pop("is_mistral", None)
        self.top_p = kwargs.pop("top_p", None)
        self.guardrails_prompt = kwargs.pop("guardrails_prompt", None)
        self.use_guardrails = kwargs.pop("use_guardrails", None)
        self.system_instructions = kwargs.pop("system_instructions", None)
        self.use_system_instructions = kwargs.pop("use_system_instructions", None)
        self.user_evaluation = kwargs.pop("user_evaluation", None)
        self.use_mood = kwargs.pop("use_mood", None)
        self.use_personality = kwargs.pop("use_personality", None)
        self.logger = Logger(prefix=self.__class__.__name__)
        super().__init__(*args, **kwargs)
        self.register(SignalCode.LLM_RESPOND_TO_USER_SIGNAL, self.do_response)
        self.prompt = ""
        self.history = []
        self.thread = None
        self.do_interrupt = False

    def unload(self):
        self.model = None
        self.tokenizer = None
        self.thread = None
        clear_memory()

    def interrupt_process(self):
        self.do_interrupt = True

    def do_interrupt_process(self):
        interrupt = self.do_interrupt
        self.do_interrupt = False
        return interrupt

    @property
    def use_cuda(self):
        return torch.cuda.is_available()

    @property
    def cuda_index(self):
        return 0

    def build_system_prompt(self, action: LLMActionType, vision_history: list = []):
        guardrails = self.guardrails_prompt if self.use_guardrails else ""
        system_instructions = self.system_instructions if self.use_system_instructions else ""
        system_prompt = []

        if action == LLMActionType.CHAT:
            """
            Build the system prompt for chat template
            """
            names = f"Your name is {self.botname}. \nThe user's name is {self.username}."
            mood = (
                f"{self.botname} is not a computer or a bot, you are a human with emotions. "
                f"{self.botname}'s mood changes depending on the conversation and other factors.\n"
                f"{self.botname}'s current mood: {self.bot_mood}.\n"
                #f"{self.botname}'s evaluation of {self.username}: {self.user_evaluation}"
            ) if (self.use_mood and self.bot_mood != "") else ""
            personality = (
                f"Your personality: {self.bot_personality}."
            ) if self.use_personality else ""

            system_prompt = [
                guardrails,
                system_instructions,
                "Do not return tags, code, or any other form of non-human language. You are a human. You must communicate like a human.",
                names,
                mood,
                personality,
            ]

            """
            If we have a vision history, append it to the prompt
            """
            if len(vision_history) > 0:
                vision_history = vision_history[-10:] if len(vision_history) > 10 else vision_history
                system_prompt.append("\n======\n")
                system_prompt.append((
                    "You have eyes, you can see. You see many things but they "
                    "are no always correct. You must try to determine what you "
                    "are seeing based on these images Try to summarize them to "
                    "determine what is happening. Here is a list of things that "
                    "you currently saw:"
                ))
                system_prompt.append(','.join(vision_history))

            """
            Append the date, time and timezone
            """
            current_date = datetime.datetime.now().strftime("%A %b %d, %Y")
            current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
            current_timezone = time.tzname
            system_prompt.append("\n======\n")
            system_prompt.append(f"Current Date: {current_date}")
            system_prompt.append(f"Current Time: {current_time}")
            system_prompt.append(f"Current Timezone: {current_timezone}")

        elif action == LLMActionType.ANALYZE_VISION_HISTORY:
            vision_history = vision_history[-10:] if len(vision_history) > 10 else vision_history
            system_prompt = [
                (
                    "You will be given a list of image captions. Your goal is to "
                    "analyze the captions and determine what is happening in the "
                    "images. The captions won't be entirely accurate, so you must "
                    "infer what you believe is happening in the images. "
                    "After analyzing the captions, you must summarize what you "
                    "believe is happening in the images. "
                    "Here is a list of captions:"
                ),
                ','.join(vision_history),
            ]

        elif action == LLMActionType.GENERATE_IMAGE:
            ", ".join([
                "'%s'" % category.value for category in ImageCategory
            ])
            guardrails = self.settings["prompt_templates"]["image"]["guardrails"] if self.settings["prompt_templates"]["image"]["use_guardrails"] else ""
            system_prompt = [
                guardrails,
                self.settings["prompt_templates"]["image"]["system"]
            ]
        return "\n".join(system_prompt)

    def latest_human_message(self) -> dict:
        return {} if not self.prompt else {
            "content": self.prompt,
            "role": LLMChatRole.HUMAN.value
        }

    def prepare_messages(
        self,
        action: LLMActionType,
        use_latest_human_message: bool = True,
        vision_history: list = []
    ) -> list:
        messages = [
            {
                "content": self.build_system_prompt(action, vision_history=vision_history),
                "role": LLMChatRole.SYSTEM.value
            }
        ]

        messages += self.history

        if use_latest_human_message:
            messages.append(
                self.latest_human_message()
            )
        return messages

    def get_rendered_template(
        self,
        conversation,
        use_latest_human_message: bool = True
    ):
        rendered_template = self.tokenizer.apply_chat_template(
            chat_template=self.chat_template,
            conversation=conversation,
            tokenize=False
        )

        # HACK: current version of transformers does not allow us to pass
        # variables to the chat template function, so we apply those here
        variables = {
            "username": self.username,
            "botname": self.botname,
            "bot_mood": self.bot_mood,
            "bot_personality": self.bot_personality,
        }
        for key, value in variables.items():
            rendered_template = rendered_template.replace("{{ " + key + " }}", value)
        return rendered_template

    def do_response(self, _message: dict):
        self.run(self.prompt, LLMActionType.CHAT)

    def run(self, prompt, action: LLMActionType, vision_history: list = []):
        self.logger.debug("Running...")
        self.prompt = prompt
        conversation = self.prepare_messages(action, vision_history=vision_history)
        rendered_template = self.get_rendered_template(conversation)

        # Encode the rendered template
        encoded = self.tokenizer(rendered_template, return_tensors="pt")
        model_inputs = encoded.to(get_torch_device(self.settings["memory_settings"]["default_gpu"]["llm"]))

        # Generate the response
        self.logger.debug("Generating...")

        if self.thread is not None:
            self.thread.join()

        self.emit_signal(SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL)

        stopping_criteria = ExternalConditionStoppingCriteria(self.do_interrupt_process)
        try:
            self.thread = threading.Thread(target=self.model.generate, kwargs=dict(
                **model_inputs,
                min_length=self.min_length,
                max_length=self.max_length,
                num_beams=self.num_beams,
                do_sample=self.do_sample,
                top_k=self.top_k,
                eta_cutoff=self.eta_cutoff,
                top_p=self.top_p,
                num_return_sequences=self.sequences,
                eos_token_id=self.tokenizer.eos_token_id,
                early_stopping=True,
                repetition_penalty=self.repetition_penalty,
                temperature=self.temperature,
                streamer=self.streamer,
                stopping_criteria=[stopping_criteria],
            ))
            self.do_interrupt = False
            self.thread.start()
        except Exception as e:
            print("An error occurred in model.generate:")
            print(str(e))
            print(traceback.format_exc())
        # strip all new lines from rendered_template:
        rendered_template = rendered_template.replace("\n", " ")
        eos_token = self.tokenizer.eos_token
        bos_token = self.tokenizer.bos_token
        if self.is_mistral:
            rendered_template = bos_token + rendered_template
        skip = True
        streamed_template = ""
        replaced = False
        is_end_of_message = False
        is_first_message = True
        for new_text in self.streamer:
            # if self.do_interrupt:
            #     print("DO INTERRUPT PRESSED")
            #     self.do_interrupt = False
            #     streamed_template = None
            #     self.streamer.on_finalized_text("", stream_end=True)
            #     break

            # strip all newlines from new_text
            parsed_new_text = new_text.replace("\n", " ")
            streamed_template += parsed_new_text
            if self.is_mistral:
                streamed_template = streamed_template.replace(f"{bos_token} [INST]", f"{bos_token}[INST]")
                streamed_template = streamed_template.replace("  [INST]", " [INST]")
            # iterate over every character in rendered_template and
            # check if we have the same character in streamed_template
            if not replaced:
                for i, char in enumerate(rendered_template):
                    try:
                        if char == streamed_template[i]:
                            skip = False
                        else:
                            skip = True
                            break
                    except IndexError:
                        skip = True
                        break
            if skip:
                continue
            elif not replaced:
                replaced = True
                streamed_template = streamed_template.replace(rendered_template, "")
            else:
                if eos_token in new_text:
                    streamed_template = streamed_template.replace(eos_token, "")
                    new_text = new_text.replace(eos_token, "")
                    is_end_of_message = True
                self.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    dict(
                        message=new_text,
                        is_first_message=is_first_message,
                        is_end_of_message=is_end_of_message,
                        name=self.botname,
                    )
                )
                is_first_message = False

        self.add_message_to_history(
            self.prompt,
            LLMChatRole.HUMAN
        )

        if streamed_template is not None:
            if action == LLMActionType.CHAT:
                self.add_message_to_history(
                    streamed_template,
                    LLMChatRole.ASSISTANT
                )
            elif action == LLMActionType.GENERATE_IMAGE:
                json_objects = self.extract_json_objects(streamed_template)
                if len(json_objects) > 0:
                    self.emit_signal(
                        SignalCode.LLM_IMAGE_PROMPT_GENERATED_SIGNAL,
                        json_objects[0]
                    )
                else:
                    self.logger.error("No JSON object found in the response.")

        return streamed_template

    def extract_json_objects(self, s):
        extractor = JSONExtractor()
        try:
            extractor.decode(s)
        except json.JSONDecodeError:
            pass
        return extractor.json_objects

    def add_message_to_history(
        self,
        content: AnyStr,
        role: LLMChatRole = LLMChatRole.ASSISTANT
    ):
        if role == LLMChatRole.ASSISTANT:
            content = content.replace(f"{self.botname}:", "")
            content = content.replace(f"{self.botname}", "")

        self.history.append({
            'content': content,
            'role': role.value
        })

