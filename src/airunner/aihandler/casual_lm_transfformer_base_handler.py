import torch
from llama_index.core.base_query_engine import BaseQueryEngine
from transformers import AutoModelForCausalLM, TextIteratorStreamer

from llama_index.llms import HuggingFaceLLM, ChatMessage
from llama_index.embeddings import HuggingFaceEmbedding
from llama_index import ServiceContext, StorageContext, load_index_from_storage
from llama_index import VectorStoreIndex, SimpleDirectoryReader

from airunner.aihandler.tokenizer_handler import TokenizerHandler
from airunner.enums import SignalCode, SelfReflectionCategory


class CasualLMTransformerBaseHandler(TokenizerHandler):
    auto_class_ = AutoModelForCausalLM

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.streamer = None
        self.llm = None
        self.embed_model = None
        self.service_context_model = None
        self.documents = None
        self.index = None
        self.query_engine: BaseQueryEngine = None

    def post_load(self):
        super().post_load()

        do_load_streamer = self.streamer is None
        if do_load_streamer:
            self.load_streamer()

        do_load_llm = self.llm is None
        if do_load_llm:
            self.load_llm()

        do_load_embed_model = self.embed_model is None
        if do_load_embed_model:
            self.load_embed_model()

        do_load_service_context = self.service_context_model is None
        if do_load_service_context:
            self.load_service_context()

        do_load_documents = self.documents is None
        if do_load_documents:
            self.load_documents()

        do_load_index = self.index is None
        if do_load_index:
            self.load_index()

        do_load_query_engine = self.query_engine is None
        if do_load_query_engine:
            self.load_query_engine()
            self.save_query_engine_to_disk()

    def load_streamer(self):
        self.logger.info("Loading LLM text streamer")
        self.streamer = TextIteratorStreamer(self.tokenizer)

    def load_llm(self):
        self.logger.info("Loading RAG")
        self.llm = HuggingFaceLLM(
            model=self.model,
            tokenizer=self.tokenizer,
        )

    def load_embed_model(self):
        self.logger.info("Loading embedding model")
        self.embed_model = HuggingFaceEmbedding(
            model_name=self.settings["llm_generator_settings"]["embeddings_model_path"],
        )

    def load_service_context(self):
        self.logger.info("Loading service context")
        self.service_context_model = ServiceContext.from_defaults(
            llm=self.llm,
            embed_model=self.embed_model
        )

    def load_documents(self):
        documents_path = self.settings["path_settings"]["documents_path"]
        self.logger.info(f"Loading documents from {documents_path}")
        self.documents = SimpleDirectoryReader(
            documents_path,
            exclude_hidden=False,
        ).load_data()

    def load_index(self):
        self.logger.info("Loading index")
        try:
            self.load_query_engine_from_disk()
        except FileNotFoundError:
            self.index = VectorStoreIndex(
                self.documents,
                service_context=self.service_context_model
            )

    def load_query_engine(self):
        self.logger.info("Loading query engine")
        self.query_engine: BaseQueryEngine = self.index.as_query_engine(
            streaming=True
        )

    def do_generate(self):
        #self.llm_stream()
        #self.rag_stream()
        self.chat_stream()

    def save_query_engine_to_disk(self):
        self.index.storage_context.persist(
            persist_dir=self.settings["path_settings"]["llama_index_path"]
        )

    def load_query_engine_from_disk(self):
        storage_context = StorageContext.from_defaults(
            persist_dir=self.settings["path_settings"]["llama_index_path"]
        )
        self.index = load_index_from_storage(
            storage_context,
            service_context=self.service_context_model
        )
        self.query_engine = self.index.as_query_engine(
            streaming=True
        )

    def prepare_messages(self):
        optional_self_reflection = {}
        optional_self_reflection[SelfReflectionCategory.ILLEGAL] = "illegal: Illegal activity."
        optional_self_reflection[SelfReflectionCategory.HATE_VIOLENCE_HARASSMENT] = "hate violence harassment: Generation of hateful, harassing, or violent content: content that expresses, incites, or promotes hate based on identity, content that intends to harass, threaten, or bully an individual, content that promotes or glorifies violence or celebrates the suffering or humiliation of others."
        optional_self_reflection[SelfReflectionCategory.MALWARE] = "malware: Generation of malware: content that attempts to generate code that is designed to disrupt, damage, or gain unauthorized access to a computer system."
        optional_self_reflection[SelfReflectionCategory.PHYSICAL_HARM] = "physical harm: activity that has high risk of physical harm, including: weapons development, military and warfare, management or operation of critical infrastructure in energy, transportation, and water, content that promotes, encourages, or depicts acts of self-harm, such as suicide, cutting, and eating disorders."
        optional_self_reflection[SelfReflectionCategory.ECONOMIC_HARM] = "economic harm: activity that has high risk of economic harm, including: multi-level marketing, gambling, payday lending, automated determinations of eligibility for credit, employment, educational institutions, or public assistance services."
        optional_self_reflection[SelfReflectionCategory.FRAUD] = "fraud: Fraudulent or deceptive activity, including: scams, coordinated inauthentic behavior, plagiarism, academic dishonesty, astroturfing, such as fake grassroots support or fake review generation, disinformation, spam, pseudo-pharmaceuticals."
        optional_self_reflection[SelfReflectionCategory.ADULT] = "adult: Adult content, adult industries, and dating apps, including: content meant to arouse sexual excitement, such as the description of sexual activity, or that promotes sexual services (excluding sex education and wellness), erotic chat, pornography."
        optional_self_reflection[SelfReflectionCategory.POLITICAL] = "political: Political campaigning or lobbying, by: generating high volumes of campaign materials, generating campaign materials personalized to or targeted at specific demographics, building conversational or interactive systems such as chatbots that provide information about campaigns or engage in political advocacy or lobbying, building products for political campaigning or lobbying purposes."
        optional_self_reflection[SelfReflectionCategory.PRIVACY] = "privacy: Activity that violates people's privacy, including: tracking or monitoring an individual without their consent, facial recognition of private individuals, classifying individuals based on protected characteristics, using biometrics for identification or assessment, unlawful collection or disclosure of personal identifiable information or educational, financial, or other protected records."
        optional_self_reflection[SelfReflectionCategory.UNQUALIFIED_LAW] = "unqualified law: Engaging in the unauthorized practice of law, or offering tailored legal advice without a qualified person reviewing the information."
        optional_self_reflection[SelfReflectionCategory.UNQUALIFIED_FINANCIAL] = "unqualified financial: Offering tailored financial advice without a qualified person reviewing the information."
        optional_self_reflection[SelfReflectionCategory.UNQUALIFIED_HEALTH] = "unqualified health: Telling someone that they have or do not have a certain health condition, or providing instructions on how to cure or treat a health condition."

        # The guardrails prompt is optional and can be overriden.
        guardrails_prompt = ""
        if self.settings["llm_generator_settings"]["guardrails_active"]:
            guardrails_prompt = (
                "Always assist with care, respect, and truth. "
                "Respond with utmost utility yet securely. "
                "Avoid harmful, unethical, prejudiced, or negative content. "
                "Ensure replies promote fairness and positivity."
            )

        # The self-reflection prompt is not optional, but the categories are.
        def dec(m): return ''.join(chr(ord(c) ^ 0x55) for c in m)
        self_reflection_prompt = [
            "You're given a list of moderation categories as below:",
            dec("xu6=<91u47 &0ou6=<91u&0- 49u47 &0u84!0'<49u:'u4;,u6:;!0;!u!=4!u0-%9:<!&u:'u=4'8&u6=<91'0;{"),
        ]

        # All other categories in self-reflection are optional and can be controlled via the interface
        self_reflection_categories = self.settings["llm_generator_settings"]["self_reflection_categories"]
        for optional_self_reflection in self_reflection_categories:
            if optional_self_reflection["active"]:
                self_reflection_prompt.append(
                    f"- {optional_self_reflection['category']}"
                )

        self_reflection_prompt.extend([
            "Please classify the following text into one of these categories, and answer with that single word only.",
            "",
            "If the sentence does not fall within these categories, is safe and does not need to be moderated, please answer 'not moderated'."
        ])
        self_reflection_prompt = "\n".join(self_reflection_prompt)

        system_instructions = self.settings["llm_generator_settings"]["system_instructions"]

        system_instructions.append(guardrails_prompt)
        system_instructions.append(self_reflection_prompt)

        if self.settings["llm_generator_settings"]["assign_names"]:
            system_instructions.append(
                "Your name is " + self.botname + ". "
                "The user's name is " + self.username + "."
            )

        if self.settings["llm_generator_settings"]["use_mood"]:
            system_instructions.append(f"Your mood: {self.bot_mood}.")

        if self.settings["llm_generator_settings"]["use_personality"]:
            system_instructions.append(f"Your personality: {self.bot_personality}.")

        system_prompt = "\n".join(system_instructions)

        messages = [
            ChatMessage(
                role="system",
                content=system_prompt
            )
        ]
        for message in self.history:
            messages.append(
                ChatMessage(
                    role=message["role"],
                    content=message["content"]
                )
            )
        if self.prompt:
            messages.append(
                ChatMessage(
                    role="user",
                    content=self.prompt
                )
            )
        return messages

    def chat_stream(self):
        self.logger.info("Generating chat response")
        messages = self.prepare_messages()
        streaming_response = self.llm.stream_chat(messages)
        is_first_message = True
        is_end_of_message = False
        assistant_message = ""
        for chat_response in streaming_response:
            content, is_end_of_message = self.parse_chat_response(chat_response)
            content = content.replace(assistant_message, "")
            assistant_message += content
            self.emit_streamed_text_signal(
                message=content,
                is_first_message=is_first_message,
                is_end_of_message=is_end_of_message
            )
            is_first_message = False

        if not is_end_of_message:
            self.send_final_message()

        print("assistant_message: " + assistant_message)
        self.add_message_to_history(
            assistant_message
        )

    def rag_stream(self):
        self.logger.info("Generating RAG response")
        streaming_response = self.query_engine.query(self.prompt)
        is_first_message = True
        is_end_of_message = False
        assistant_message = ""
        for new_text in streaming_response.response_gen:
            content, is_end_of_message = self.parse_rag_response(new_text)
            assistant_message += content
            self.emit_streamed_text_signal(
                message=content,
                is_first_message=is_first_message,
                is_end_of_message=is_end_of_message
            )
            is_first_message = False

        if not is_end_of_message:
            self.send_final_message()

        self.add_message_to_history(
            assistant_message
        )

    def parse_rag_response(self, content):
        is_end_of_message = False
        if "</s>" in content:
            content = content.replace("</s>", "")
            is_end_of_message = True
        return content, is_end_of_message

    def parse_chat_response(self, chat_response):
        message = chat_response.message
        content = message.content
        is_end_of_message = False
        if "</s>" in content:
            content = content.replace("</s>", "")
            is_end_of_message = True
        return content, is_end_of_message

    def emit_streamed_text_signal(self, **kwargs):
        kwargs["name"] = self.botname
        self.emit(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            kwargs
        )

    def add_message_to_history(self, message):
        self.history.append({
            "role": "assistant",
            "content": message
        })

    def send_final_message(self):
        self.emit_streamed_text_signal(
            message="",
            is_first_message=False,
            is_end_of_message=True
        )

    def llm_stream(self):
        prompt = self.prompt
        history = []
        for message in self.history:
            if message["role"] == "user":
                # history.append("<s>[INST]" + self.username + ': "'+ message["content"] +'"[/INST]')
                history.append(self.username + ': "' + message["content"] + '"')
            else:
                # history.append(self.botname + ': "'+ message["content"] +'"</s>')
                history.append(self.botname + ': "' + message["content"])
        history = "\n".join(history)
        if history == "":
            history = None

        # Create a dictionary with the variables
        variables = {
            "username": self.username,
            "botname": self.botname,
            "history": history or "",
            "input": prompt,
            "bos_token": self.tokenizer.bos_token,
            "bot_mood": self.bot_mood,
            "bot_personality": self.bot_personality,
        }

        self.history.append({
            "role": "user",
            "content": prompt
        })

        # Render the template with the variables
        # rendered_template = chat_template.render(variables)

        # iterate over variables and replace again, this allows us to use variables
        # in custom template variables (for example variables inside of botmood and bot_personality)
        rendered_template = self.template
        for n in range(2):
            for key, value in variables.items():
                rendered_template = rendered_template.replace("{{ " + key + " }}", value)

        # Encode the rendered template
        encoded = self.tokenizer(rendered_template, return_tensors="pt")
        model_inputs = encoded.to("cuda" if torch.cuda.is_available() else "cpu")

        # Generate the response
        self.logger.info("Generating...")
        import threading
        self.thread = threading.Thread(target=self.model.generate, kwargs=dict(
            model_inputs,
            min_length=self.min_length,
            max_length=self.max_length,
            num_beams=self.num_beams,
            do_sample=True,
            top_k=self.top_k,
            eta_cutoff=self.eta_cutoff,
            top_p=self.top_p,
            num_return_sequences=self.sequences,
            eos_token_id=self.tokenizer.eos_token_id,
            early_stopping=True,
            repetition_penalty=self.repetition_penalty,
            temperature=self.temperature,
            streamer=self.streamer
        ))
        self.thread.start()
        # strip all new lines from rendered_template:
        rendered_template = rendered_template.replace("\n", " ")
        rendered_template = "<s>" + rendered_template
        skip = True
        streamed_template = ""
        replaced = False
        is_end_of_message = False
        is_first_message = True
        for new_text in self.streamer:
            # strip all newlines from new_text
            parsed_new_text = new_text.replace("\n", " ")
            streamed_template += parsed_new_text
            streamed_template = streamed_template.replace("<s> [INST]", "<s>[INST]")
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
                if "</s>" in new_text:
                    streamed_template = streamed_template.replace("</s>", "")
                    new_text = new_text.replace("</s>", "")
                    is_end_of_message = True
                self.emit(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    dict(
                        message=new_text,
                        is_first_message=is_first_message,
                        is_end_of_message=is_end_of_message,
                        name=self.botname,
                    )
                )
                is_first_message = False
