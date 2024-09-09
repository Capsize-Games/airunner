import os.path

from airunner.enums import SignalCode, LLMChatRole, AgentState, LLMActionType
from airunner.settings import BASE_PATH


class AgentLlamaIndexMixin:
    def __init__(self):
        self.__documents = None
        self.__index = None
        self.__chat_engine = None
        self.__retriever = None
        self.__service_context = None
        self.__storage_context = None
        self.__transformations = None
        self.__index_struct = None
        self.__callback_manager = None
        self.__pdf_reader = None
        self.__epub_reader = None
        self.__html_reader = None
        self.__markdown_reader = None
        self.__embed_model = None
        self.__model_name = os.path.expanduser(
            os.path.join(
                self.settings["path_settings"]["base_path"],
                "text/models",
                "sentence_transformers/sentence-t5-large"
            )
        )
        self.__query_instruction = "Search through all available texts and provide a brief summary of the key points which are relevant to the query."
        self.__text_instruction = "Summarize and provide a brief explanation of the text. Stay concise and to the point."
        self.__state = AgentState.SEARCH
        self.__chunk_size = 1000
        self.__chunk_overlap = 512
        self.__target_files = []

        self.register(SignalCode.RAG_RELOAD_INDEX_SIGNAL, self.on_reload_rag_index_signal)

    @property
    def target_files(self):
        target_files = self.__target_files or []
        if len(target_files) == 0:
            target_files = self.chatbot["target_files"] or []
        readme_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "..", "..",
            "README.md"
        )
        documentation_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..",
            "documents",
            "documentation.md"
        )
        # target_files.append(documentation_file)
        # target_files.append(readme_file)
        return target_files

    def on_reload_rag_index_signal(self, data: dict = None):
        self.__target_files = data["target_files"] or []
        self.__load_documents()
        self.__load_document_index()

    @property
    def query_instruction(self):
        if self.__state == AgentState.SEARCH:
            return self.__query_instruction
        elif self.__state == AgentState.CHAT:
            return "Search through the chat history for anything relevant to the query."

    @property
    def text_instruction(self):
        if self.__state == AgentState.SEARCH:
            return self.__text_instruction
        elif self.__state == AgentState.CHAT:
            return "Use the text to respond to the user"

    @property
    def index(self):
        if self.__state == AgentState.SEARCH:
            return self.__index
        elif self.__state == AgentState.CHAT:
            return self.__chat_history_index

    def load_rag(self, model, tokenizer):
        self.__load_llm(model, tokenizer)
        self.__load_rag_model()
        self.__load_readers()
        self.__load_file_extractor()
        self.__load_documents()
        self.__load_text_splitter()
        self.__load_prompt_helper()
        self.__load_service_context()
        self.__load_document_index()
        self.__load_retriever()
        self.__load_context_chat_engine()

        # self.__load_storage_context()
        # self.__load_transformations()
        # self.__load_index_struct()

    def __load_llm(self, model, tokenizer):
        # try:
            if self.settings["llm_generator_settings"]["use_api"]:
                self.__llm = model
            else:
                from llama_index.llms.huggingface import HuggingFaceLLM
                self.__llm = HuggingFaceLLM(
                    model=model,
                    tokenizer=tokenizer,
                    # generate_kwargs=dict(
                    #     max_new_tokens=4096,
                    #     top_k=40,
                    #     top_p=0.90,
                    #     temperature=0.5,
                    #     num_return_sequences=1,
                    #     num_beams=1,
                    #     no_repeat_ngram_size=4,
                    #     early_stopping=True,
                    #     do_sample=True,
                    # )
                )
        # except Exception as e:
        #     self.logger.error(f"Error loading LLM: {str(e)}")

    @property
    def is_llama_instruct(self):
        return True

    def perform_rag_search(
        self,
        prompt,
        streaming: bool = False,
        response_mode = None
    ):
        from llama_index.core.response_synthesizers import ResponseMode
        if response_mode is None:
            response_mode = ResponseMode.COMPACT

        if self.__chat_engine is None:
            raise RuntimeError(
                "Chat engine is not initialized. "
                "Please ensure __load_service_context "
                "is called before perform_rag_search."
            )

        self.add_message_to_history(
            prompt,
            LLMChatRole.HUMAN
        )

        if response_mode in (
            ResponseMode.ACCUMULATE
        ):
            streaming = False

        try:
            engine = self.__chat_engine
        except AttributeError as e:
            self.logger.error(f"Error performing RAG search: {str(e)}")
            if streaming:
                self.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    dict(
                        message="",
                        is_first_message=True,
                        is_end_of_message=True,
                        name=self.botname,
                    )
                )
            return

        inputs:str = self.get_rendered_template(LLMActionType.PERFORM_RAG_SEARCH, [])

        response = engine.stream_chat(
            message=inputs
        )
        response_text = ""
        if streaming:
            self.emit_signal(SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL)
            is_first_message = True
            is_end_of_message = False
            for res in response.response_gen:
                if response_text:  # Only add a space if response_text is not empty
                    response_text += " "
                response_text += res.strip()
                self.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    dict(
                        message=res,
                        is_first_message=is_first_message,
                        is_end_of_message=is_end_of_message,
                        name=self.botname,
                    )
                )
                is_first_message = False
            self.add_message_to_history(
                response_text,
                LLMChatRole.ASSISTANT
            )
            response_text = ""
        else:
            response_text = response.response
            is_first_message = True
            self.add_message_to_history(
                response_text,
                LLMChatRole.ASSISTANT
            )

        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            dict(
                message=response_text,
                is_first_message=is_first_message,
                is_end_of_message=True,
                name=self.botname,
            )
        )

        return response

    def __load_rag_model(self):
        self.logger.debug("Loading RAG model...")
        from airunner.aihandler.llm.custom_embedding import CustomEmbedding
        #from llama_index.core import Settings
        #Settings.embed_model = CustomEmbedding(self.__llm)
        self.__embed_model = CustomEmbedding(self.__llm)


    def __load_readers(self):
        from llama_index.readers.file import EpubReader, PDFReader, MarkdownReader
        from airunner.aihandler.llm.agent.html_file_reader import HtmlFileReader
        self.__pdf_reader = PDFReader()
        self.__epub_reader = EpubReader()
        self.__html_reader = HtmlFileReader()
        self.__markdown_reader = MarkdownReader()

    def __load_file_extractor(self):
        self.file_extractor = {
            ".pdf": self.__pdf_reader,
            ".epub": self.__epub_reader,
            ".html": self.__html_reader,
            ".htm": self.__html_reader,
            ".md": self.__markdown_reader,
        }

    def __load_documents(self):
        self.logger.debug("Loading documents...")
        from llama_index.core import SimpleDirectoryReader
        try:
            self.__documents = SimpleDirectoryReader(
                input_files=self.target_files,
                file_extractor=self.file_extractor,
                exclude_hidden=False
            ).load_data()
        except ValueError as e:
            self.logger.error(f"Error loading documents: {str(e)}")
            self.__documents = None

    def __load_text_splitter(self):
        from llama_index.core.node_parser import SentenceSplitter
        self.__text_splitter = SentenceSplitter(
            chunk_size=256,
            chunk_overlap=20
        )

    def __load_prompt_helper(self):
        from llama_index.core import PromptHelper
        self.__prompt_helper = PromptHelper(
            context_window=4096,
            num_output=1024,
            chunk_overlap_ratio=0.1,
            chunk_size_limit=None,
        )

    def __load_context_chat_engine(self):
        from llama_index.core.chat_engine import ContextChatEngine
        context_retriever = self.__retriever  # Your method to retrieve context
        try:
            self.__chat_engine = ContextChatEngine.from_defaults(
                retriever=context_retriever,
                service_context=self.__service_context,
                chat_history=self.history,
                memory=None,  # Define or use an existing memory buffer if needed
                system_prompt="Search the full text and find all relevant information related to the query.",
                node_postprocessors=[],  # Add postprocessors if utilized in your setup
                llm=self.__llm,  # Use the existing LLM setup
            )
        except Exception as e:
            self.logger.error(f"Error loading chat engine: {str(e)}")

    def __load_service_context(self):
        self.logger.debug("Loading service context with ContextChatEngine...")
        from llama_index.core import ServiceContext
        try:
            # Update service context to use the newly created chat engine
            self.__service_context = ServiceContext.from_defaults(
                llm=self.__llm,
                embed_model=self.__embed_model,
                #chat_engine=self.__chat_engine,  # Include the chat engine in the service context
                text_splitter=self.__text_splitter,
                prompt_helper=self.__prompt_helper,
            )
        except Exception as e:
            self.logger.error(f"Error loading service context with chat engine: {str(e)}")

    # def __load_storage_context(self):
    #     from llama_index.core import ServiceContext, StorageContext
    #     self.logger.debug("Loading storage context...")
    #     path = os.path.expanduser(self.settings["path_settings"]["storage_path"])
    #     if not os.path.exists(path):
    #         os.makedirs(path, exist_ok=True)
    #     self.__storage_context = StorageContext.from_defaults(
    #         docstore=self.__documents,
    #         index_store=self.__index,
    #         vector_store=None,
    #         image_store=None,
    #         vector_stores={},
    #         graph_store=None,
    #         persist_dir=path
    #     )

    # def __load_transformations(self):
    #     from llama_index.core.schema import TransformComponent
    #     self.logger.debug("Loading transformations...")
    #     self.__transformations = [
    #         TransformComponent(
    #             name="lowercase",
    #             function=lambda x: x.lower(),
    #             description="Lowercase all text",
    #         ),
    #         TransformComponent(
    #             name="remove_punctuation",
    #             function=lambda x: x.translate(str.maketrans("", "", string.punctuation)),
    #             description="Remove all punctuation",
    #         ),
    #         TransformComponent(
    #             name="remove_whitespace",
    #             function=lambda x: x.strip(),
    #             description="Remove all whitespace",
    #         ),
    #     ]

    # def __load_index_struct(self):
    #     from llama_index.core.data_structs import IndexDict
    #     self.logger.debug("Loading index struct...")
    #     self.__index_struct = IndexDict(
    #         nodes_dict=self.__index.index_struct.nodes_dict,
    #         doc_id_dict=self.__index.index_struct.doc_id_dict,
    #         embeddings_dict=self.__index.index_struct.embeddings_dict,
    #     )

    def print_chunks(self):
        # Assuming self.__service_context is already loaded
        for document in self.__documents:
            # Extract the text from the Document object
            document_text = document.text
            # Pass the text to the _split method
            chunks = self.__service_context.node_parser._split(document_text, self.__chunk_size)
            for chunk in chunks:
                print(chunk)

    def __load_document_index(self):
        self.logger.debug("Loading index...")
        from llama_index.core import SimpleKeywordTableIndex
        try:
            self.__index = SimpleKeywordTableIndex.from_documents(
                self.__documents,
                #service_context=self.__service_context,
                llm=self.__llm
            )
            self.logger.debug("Index loaded successfully.")
        except TypeError as e:
            self.logger.error(f"Error loading index: {str(e)}")

    def __load_retriever(self):
        from llama_index.core.indices.keyword_table import KeywordTableSimpleRetriever
        try:
            self.__retriever = KeywordTableSimpleRetriever(
                index=self.__index,
            )
            self.logger.debug("Retriever loaded successfully with index.")
        except Exception as e:
            self.logger.error(f"Error setting up the retriever: {str(e)}")
