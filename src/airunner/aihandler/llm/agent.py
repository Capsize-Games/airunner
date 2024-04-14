import datetime
import json
import time
import traceback
from typing import AnyStr
import torch
from PySide6.QtCore import QObject
from transformers import StoppingCriteria
from airunner.aihandler.logger import Logger
from airunner.json_extractor import JSONExtractor
from airunner.mediator_mixin import MediatorMixin
from airunner.enums import SignalCode, LLMChatRole, LLMActionType, ImageCategory, QueueType
from airunner.utils import get_torch_device, clear_memory, create_worker
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.workers.agent_worker import AgentWorker


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

        self.rendered_template = None
        self.model = kwargs.pop("model", None)
        self.tokenizer = kwargs.pop("tokenizer", None)
        self.streamer = kwargs.pop("streamer", None)
        self.tools = kwargs.pop("tools", None)
        self.chat_template = kwargs.pop("chat_template", "")
        self.bot_mood = kwargs.pop("bot_mood", None)
        self.bot_personality = kwargs.pop("bot_personality", None)
        self.max_new_tokens = kwargs.pop("max_new_tokens", self.settings["llm_generator_settings"]["max_new_tokens"])
        self.min_length = kwargs.pop("min_length", self.settings["llm_generator_settings"]["min_length"])
        #self.max_length = kwargs.pop("max_length", self.settings["llm_generator_settings"]["max_length"])
        self.num_beams = kwargs.pop("num_beams", self.settings["llm_generator_settings"]["num_beams"])
        self.do_sample = kwargs.pop("do_sample", self.settings["llm_generator_settings"]["do_sample"])
        self.top_k = kwargs.pop("top_k", self.settings["llm_generator_settings"]["top_k"])
        self.eta_cutoff = kwargs.pop("eta_cutoff", self.settings["llm_generator_settings"]["eta_cutoff"])
        self.sequences = kwargs.pop("sequences", self.settings["llm_generator_settings"]["sequences"])
        self.early_stopping = kwargs.pop("early_stopping", self.settings["llm_generator_settings"]["early_stopping"])
        self.repetition_penalty = kwargs.pop("repetition_penalty", self.settings["llm_generator_settings"]["repetition_penalty"])
        self.temperature = kwargs.pop("temperature", self.settings["llm_generator_settings"]["temperature"])
        self.is_mistral = kwargs.pop("is_mistral", True)
        self.top_p = kwargs.pop("top_p", self.settings["llm_generator_settings"]["top_p"])
        self.guardrails_prompt = kwargs.pop("guardrails_prompt", "")
        self.use_guardrails = kwargs.pop("use_guardrails", True)
        self.system_instructions = kwargs.pop("system_instructions", "")
        self.use_system_instructions = kwargs.pop("use_system_instructions", True)
        self.user_evaluation = kwargs.pop("user_evaluation", None)
        self.use_mood = kwargs.pop("use_mood", True)
        self.use_personality = kwargs.pop("use_personality", True)
        self.logger = Logger(prefix=self.__class__.__name__)
        super().__init__(*args, **kwargs)
        self.register(SignalCode.LLM_RESPOND_TO_USER_SIGNAL, self.do_response)
        self.register(SignalCode.ADD_CHATBOT_MESSAGE_SIGNAL, self.add_chatbot_response_to_history)
        self.prompt = ""
        self.history = []
        self.thread = None
        self.do_interrupt = False
        self.response_worker = create_worker(AgentWorker)
        #self.summarize_worker = create_worker(AgentWorker)

    @property
    def chatbot(self):
        return self.settings["llm_generator_settings"]["current_chatbot"]

    @property
    def username(self):
        return self.settings["llm_generator_settings"]["saved_chatbots"][self.chatbot]["username"]

    @property
    def botname(self):
        return self.settings["llm_generator_settings"]["saved_chatbots"][self.chatbot]["botname"]

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

    def build_system_prompt(
        self,
        action: LLMActionType,
        vision_history: list = [],
        username: str = "",
        botname: str = "",
        bot_mood: str = "",
        bot_personality: str = "",
        guardrails_prompt: str = "",
        system_instructions: str = "",
        use_guardrails: bool = True,
        use_system_instructions: bool = True,
        user_evaluation: str = "",
        use_mood: bool = True,
        use_personality: bool = True,
        use_names: bool = True
    ):
        use_guardrails = self.use_guardrails if use_guardrails is None else use_guardrails
        use_system_instructions = self.use_system_instructions if use_system_instructions is None else use_system_instructions
        system_instructions = system_instructions if use_system_instructions else ""
        if not use_system_instructions:
            system_instructions = ""
        if not use_guardrails:
            guardrails_prompt = ""
        system_prompt = []
        username = self.username if username == "" or not username is None else username
        botname = self.botname if botname == "" or not botname else botname
        bot_mood = self.bot_mood if bot_mood == "" or not bot_mood else bot_mood
        bot_personality = self.bot_personality if bot_personality == "" or not bot_personality else bot_personality

        if action == LLMActionType.CHAT:
            """
            Build the system prompt for chat template
            """
            names = f"Your name is {botname}. \nThe user's name is {username}." if use_names else ""
            mood = (
                f"{botname} is not a computer or a bot, you are a human with emotions. "
                f"{botname}'s mood changes depending on the conversation and other factors.\n"
                f"{botname}'s current mood: {bot_mood}.\n"
                #f"{botname}'s evaluation of {username}: {self.user_evaluation}"
            ) if (use_mood and bot_mood != "") else ""
            personality = (
                f"Your personality: {bot_personality}."
            ) if use_personality else ""

            system_prompt = [
                guardrails_prompt,
                system_instructions,
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
            if self.settings["prompt_templates"]["chatbot"]["use_system_datetime_in_system_prompt"]:
                current_date = datetime.datetime.now().strftime("%A %b %d, %Y")
                current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
                current_timezone = time.tzname
                system_prompt.append("\n======\n")
                system_prompt.append(f"Use the following information to help you with your response, but do not include it in your response or reference it directly unless asked.")
                system_prompt.append(f"Date: {current_date}, Time: {current_time}, Timezone: {current_timezone}")

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
        vision_history: list = [],
        username: str = "",
        botname: str = "",
        bot_mood: str = "",
        bot_personality: str = "",
        guardrails_prompt: str = "",
        system_instructions: str = "",
        use_guardrails: bool = True,
        use_system_instructions: bool = True,
        user_evaluation: str = "",
        use_mood: bool = True,
        use_personality: bool = True,
        use_names: bool = True
    ) -> list:
        messages = [
            {
                "content": self.build_system_prompt(
                    action,
                    vision_history=vision_history,
                    username=username,
                    botname=botname,
                    bot_mood=bot_mood,
                    bot_personality=bot_personality,
                    guardrails_prompt=guardrails_prompt,
                    system_instructions=system_instructions,
                    use_guardrails=use_guardrails,
                    use_system_instructions=use_system_instructions,
                    user_evaluation=user_evaluation,
                    use_mood=use_mood,
                    use_personality=use_personality,
                    use_names=use_names
                ),
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
        use_latest_human_message: bool = True,
        chat_template: str = ""
    ):
        rendered_template = self.tokenizer.apply_chat_template(
            chat_template=chat_template,
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
            value = value or ""
            rendered_template = rendered_template.replace("{{ " + key + " }}", value)
        return rendered_template

    def do_response(self, message):
        self.run(
            prompt=self.prompt,
            action=LLMActionType.CHAT,
            max_new_tokens=message["args"][0]
        )

    def get_model_inputs(
        self,
        action,
        vision_history,
        **kwargs
    ):
        self.chat_template = kwargs.get("chat_template", self.chat_template)
        self.bot_mood = kwargs.get("bot_mood", self.bot_mood)
        self.bot_personality = kwargs.get("bot_personality", self.bot_personality)
        self.max_new_tokens = kwargs.get("max_new_tokens", self.max_new_tokens)
        self.min_length = kwargs.get("min_length", self.min_length)
        #self.max_length = kwargs.get("max_length", self.max_length)
        self.num_beams = kwargs.get("num_beams", self.num_beams)
        self.do_sample = kwargs.get("do_sample", self.do_sample)
        self.top_k = kwargs.get("top_k", self.top_k)
        self.eta_cutoff = kwargs.get("eta_cutoff", self.eta_cutoff)
        self.sequences = kwargs.get("sequences", self.sequences)
        self.early_stopping = kwargs.get("early_stopping", self.early_stopping)
        self.repetition_penalty = kwargs.get("repetition_penalty", self.repetition_penalty)
        self.temperature = kwargs.get("temperature", self.temperature)
        self.top_p = kwargs.get("top_p", self.top_p)
        self.guardrails_prompt = kwargs.get("guardrails_prompt", self.guardrails_prompt)
        self.use_guardrails = kwargs.get("use_guardrails", self.use_guardrails)
        self.system_instructions = kwargs.get("system_instructions", self.system_instructions)
        self.use_system_instructions = kwargs.get("use_system_instructions", self.use_system_instructions)
        self.user_evaluation = kwargs.get("user_evaluation", self.user_evaluation)
        self.use_mood = kwargs.get("use_mood", self.use_mood)
        self.use_personality = kwargs.get("use_personality", self.use_personality)
        self.seed = kwargs.get("seed", 42)
        self.no_repeat_ngram_size = kwargs.get("no_repeat_ngram_size", 2)
        self.return_result = kwargs.get("return_result", True)
        self.skip_special_tokens = kwargs.get("skip_special_tokens", True)
        self.sequences = kwargs.get("sequences", 1)
        self.ngram_size = kwargs.get("ngram_size", 2)
        self.length_penalty = kwargs.get("length_penalty", 0.5)
        self.use_cache = kwargs.get("use_cache", True)
        self.decoder_start_token_id = kwargs.get("decoder_start_token_id", None)
        self.skip_special_tokens = kwargs.get("skip_special_tokens", True)
        self.no_repeat_ngram_size = kwargs.get("no_repeat_ngram_size", 2)
        self.use_names = kwargs.get("use_names", True)

        conversation = self.prepare_messages(
            action,
            vision_history=vision_history,
            username=self.username,
            botname=self.botname,
            bot_mood=self.bot_mood,
            bot_personality=self.bot_personality,
            guardrails_prompt=self.guardrails_prompt,
            system_instructions=self.system_instructions,
            use_guardrails=self.use_guardrails,
            use_system_instructions=self.use_system_instructions,
            user_evaluation=self.user_evaluation,
            use_mood=self.use_mood,
            use_personality=self.use_personality,
            use_names=self.use_names
        )

        self.rendered_template = self.get_rendered_template(
            conversation,
            chat_template=self.chat_template
        )

        # Encode the rendered template
        encoded = self.tokenizer(
            self.rendered_template,
            return_tensors="pt"
        )
        model_inputs = encoded.to(
            get_torch_device(
                self.settings["memory_settings"]["default_gpu"]["llm"]
            )
        )
        return model_inputs

    def run(
        self,
        prompt: str,
        action: LLMActionType = LLMActionType.CHAT,
        vision_history: list = [],
        **kwargs
    ):
        self.logger.debug("Running...")
        self.prompt = prompt
        streamer = self.streamer
        system_instructions = kwargs.get("system_instructions", self.system_instructions)

        # res = self.do_run(
        #     action,
        #     vision_history,
        #     **kwargs,
        #     system_instructions=(
        #         "You will evaluate the conversation and determine the approximate "
        #         "word length that is required to respond to {{ username }}. "
        #     ),
        #     do_add_response_to_history=False,
        #     streamer=None,
        #     do_emit_response=False,
        #     use_names=False,
        # )

        return self.do_run(
            action,
            vision_history,
            **kwargs,
            system_instructions=system_instructions,
            do_add_response_to_history=False,
            use_names=True,
            streamer=streamer
        )

    def do_run(
        self,
        prompt: str,
        action: LLMActionType = LLMActionType.CHAT,
        vision_history: list = [],
        do_add_response_to_history: bool = True,
        streamer=None,
        do_emit_response: bool = True,
        use_names: bool = True,
        **kwargs
    ):
        model_inputs = self.get_model_inputs(
            LLMActionType.CHAT,
            vision_history,
            use_names=use_names,
            **kwargs
        )

        if streamer:
            self.run_with_thread(
                model_inputs,
                action=LLMActionType.CHAT,
                do_add_response_to_history=do_add_response_to_history,
                streamer=streamer,
                do_emit_response=do_emit_response,
                **kwargs
            )
        else:
            self.emit_signal(SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL)
            stopping_criteria = ExternalConditionStoppingCriteria(self.do_interrupt_process)
            data = self.prepare_generate_data(model_inputs, stopping_criteria)
            res = self.model.generate(
                **data
            )
            response = self.tokenizer.decode(res[0])
            if do_emit_response:
                self.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    dict(
                        message=response,
                        is_first_message=True,
                        is_end_of_message=True,
                        name=self.botname,
                    )
                )
            return response

    def prepare_generate_data(self, model_inputs, stopping_criteria):
        return dict(
            **model_inputs,
            no_repeat_ngram_size=self.no_repeat_ngram_size,
            decoder_start_token_id=self.decoder_start_token_id,
            use_cache=self.use_cache,
            length_penalty=self.length_penalty,
            min_length=self.min_length,
            max_new_tokens=self.max_new_tokens,
            num_beams=self.num_beams,
            do_sample=self.do_sample,
            top_k=self.top_k,
            eta_cutoff=self.eta_cutoff,
            top_p=self.top_p,
            num_return_sequences=self.sequences,
            eos_token_id=self.tokenizer.eos_token_id,
            early_stopping=self.early_stopping,
            repetition_penalty=self.repetition_penalty,
            temperature=self.temperature,
            stopping_criteria=[stopping_criteria]
        )

    def run_with_thread(
        self,
        model_inputs,
        do_add_response_to_history: bool = True,
        action: LLMActionType = LLMActionType.CHAT,
        **kwargs,
    ):
        # Generate the response
        self.logger.debug("Generating...")

        self.emit_signal(SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL)

        stopping_criteria = ExternalConditionStoppingCriteria(self.do_interrupt_process)

        data = self.prepare_generate_data(model_inputs, stopping_criteria)
        streamer = kwargs.get("streamer", self.streamer)
        data["streamer"] = streamer

        try:
            self.response_worker.add_to_queue({
                "model": self.model,
                "kwargs": data
            })
            self.do_interrupt = False
        except Exception as e:
            print("545: An error occurred in model.generate:")
            print(str(e))
            print(traceback.format_exc())
        # strip all new lines from rendered_template:
        self.rendered_template = self.rendered_template.replace("\n", " ")
        eos_token = self.tokenizer.eos_token
        bos_token = self.tokenizer.bos_token
        if self.is_mistral:
            self.rendered_template = bos_token + self.rendered_template
        skip = True
        streamed_template = ""
        replaced = False
        is_end_of_message = False
        is_first_message = True
        if streamer:
            for new_text in streamer:
                # if self.do_interrupt:
                #     print("DO INTERRUPT PRESSED")
                #     self.do_interrupt = False
                #     streamed_template = None
                #     streamer.on_finalized_text("", stream_end=True)
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
                    for i, char in enumerate(self.rendered_template):
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
                    streamed_template = streamed_template.replace(self.rendered_template, "")
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

        # self.add_message_to_history(
        #     self.prompt,
        #     LLMChatRole.HUMAN
        # )

        if streamed_template is not None:
            if action == LLMActionType.CHAT:
                if do_add_response_to_history:
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

    def add_chatbot_response_to_history(self, response: dict):
        if response["message"] is None:
            return
        self.add_message_to_history(
            response["message"],
            response["role"]
        )

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
        if role == LLMChatRole.ASSISTANT and content:
            content = content.replace(f"{self.botname}:", "")
            content = content.replace(f"{self.botname}", "")

        last_item = self.history.pop() if len(self.history) > 0 else {}
        last_item_role = last_item.get("role", None)
        last_item_role_is_current_role = last_item_role == role.value

        # if the last_item is of the same role as the current message, append the content to the last_item
        if not last_item_role_is_current_role and len(last_item.keys()) > 0:
            self.history.append(last_item)

        if last_item_role_is_current_role:
            item = {
                "role": role.value,
                "content": content
            }
            item["content"] += last_item.get("content", "") + "\n" + content
            self.history.append(item)
        else:
            self.history.append({
                "role": role.value,
                "content": content
            })
