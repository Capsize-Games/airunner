import torch
from llama_index.core.base_query_engine import BaseQueryEngine
from transformers import AutoModelForCausalLM, TextIteratorStreamer

from llama_index.llms import HuggingFaceLLM
from llama_index.embeddings import HuggingFaceEmbedding
from llama_index import ServiceContext, StorageContext, load_index_from_storage
from llama_index import VectorStoreIndex, SimpleDirectoryReader

from airunner.aihandler.tokenizer_handler import TokenizerHandler
from airunner.enums import SignalCode


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
        self.embeddings_model_path = "BAAI/bge-small-en-v1.5"

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
            tokenizer=self.tokenizer
        )

    def load_embed_model(self):
        self.logger.info("Loading embeddings")
        self.embed_model = HuggingFaceEmbedding(
            model_name=self.embeddings_model_path,
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
        self.rag_stream()

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

    def prepare_template(self):
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
        return rendered_template

    def rag_stream(self):
        self.logger.info("Generating RAG response")
        streaming_response = self.query_engine.query(
            self.prompt
        )
        is_first_message = True
        is_end_of_message = False
        for new_text in streaming_response.response_gen:
            if "</s>" in new_text:
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
        if not is_end_of_message:
            self.emit(
                SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                dict(
                    message="",
                    is_first_message=False,
                    is_end_of_message=True,
                    name=self.botname,
                )
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
