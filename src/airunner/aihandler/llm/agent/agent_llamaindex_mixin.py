import os.path
import string
from typing import Optional, List

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, ServiceContext, StorageContext
from llama_index.core.data_structs import IndexDict
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.core.schema import TransformComponent
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.huggingface import HuggingFaceLLM
from llama_index.readers.file import EpubReader, PDFReader, MarkdownReader
from llama_index.core import Settings
from airunner.aihandler.llm.agent.html_file_reader import HtmlFileReader
from airunner.enums import SignalCode, LLMChatRole, AgentState


class AgentLlamaIndexMixin:
    def __init__(self):
        self.__documents = None
        self.__index = None
        self.__service_context: Optional[ServiceContext] = None
        self.__storage_context: StorageContext = None
        self.__transformations: Optional[List[TransformComponent]] = None
        self.__index_struct: Optional[IndexDict] = None
        self.__callback_manager = None
        self.__pdf_reader = None
        self.__epub_reader = None
        self.__html_reader = None
        self.__markdown_reader = None
        self.__model_name = os.path.expanduser(f"{self.settings['path_settings']['sentence_transformers_path']}/sentence-transformers/sentence-t5-large")
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
        self.__load_service_context()
        # self.__load_storage_context()
        # self.__load_transformations()
        # self.__load_index_struct()
        self.__load_document_index()

    def __load_llm(self, model, tokenizer):
        self.__llm = HuggingFaceLLM(
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=1000,
            generate_kwargs=dict(
                top_k=50,
                top_p=0.95,
                temperature=0.9,
                num_return_sequences=1,
                num_beams=1,
                no_repeat_ngram_size=3,
                early_stopping=True,
                do_sample=True,
                # pad_token_id=tokenizer.eos_token_id,
                # eos_token_id=tokenizer.eos_token_id,
                # bos_token_id=tokenizer.bos_token_id,
            )
        )

    def perform_rag_search(
        self,
        prompt,
        streaming: bool = False,
        response_mode: ResponseMode = ResponseMode.COMPACT
    ):
        if response_mode in (
            ResponseMode.ACCUMULATE
        ):
            streaming = False

        try:
            query_engine = self.__index.as_query_engine(
                streaming=streaming,
                response_mode=response_mode,
            )
            print(f"Querying with prompt: {prompt}")  # Debug: Show the prompt
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
        response = query_engine.query(prompt)
        response_text = ""
        if streaming:
            self.emit_signal(SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL)
            is_first_message = True
            is_end_of_message = False
            for res in response.response_gen:
                response_text += res
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
            response_text = ""
        else:
            response_text = response.response
            is_first_message = True

        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            dict(
                message=response_text,
                is_first_message=is_first_message,
                is_end_of_message=True,
                name=self.botname,
            )
        )

        self.add_message_to_history(
            response_text,
            LLMChatRole.ASSISTANT
        )

        return response

    def __load_rag_model(self):
        self.logger.debug("Loading RAG model...")
        Settings.embed_model = HuggingFaceEmbedding(
            model_name=self.__model_name,
            query_instruction=self.query_instruction,
            text_instruction=self.text_instruction,
            trust_remote_code=False,
        )

    def __load_readers(self):
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
        try:
            self.__documents = SimpleDirectoryReader(
                input_files=self.target_files,
                file_extractor=self.file_extractor,
                exclude_hidden=False
            ).load_data()
        except ValueError as e:
            self.logger.error(f"Error loading documents: {str(e)}")
            self.__documents = None

    def __load_service_context(self):
        self.logger.debug("Loading service context...")
        self.__service_context = ServiceContext.from_defaults(
            llm=self.__llm,
            embed_model=Settings.embed_model,
            chunk_size=self.__chunk_size,
            chunk_overlap=self.__chunk_overlap,
            system_prompt="Search the full text and find all relevant information related to the query.",
        )

    # def __load_storage_context(self):
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

    def print_indexed_chunks(self):
        # Assuming get_indexed_nodes is a method that returns the indexed nodes
        if self.__index is not None:
            node_doc_ids = list(self.__index.index_struct.nodes_dict.values())
            indexed_nodes = self.__index.docstore.get_nodes(node_doc_ids)
            for i, node in enumerate(indexed_nodes):
                print(f"Chunk {i + 1}: {node.text}")  # Print first 200 characters of each chunk

    def __load_document_index(self):
        self.logger.debug("Loading index...")
        try:
            self.__index = VectorStoreIndex.from_documents(
                self.__documents,
                service_context=self.__service_context,
                # storage_context=self.__storage_context,
                # transformations=self.__transformations,
                # index_struct=self.__index_struct
            )
        except TypeError as e:
            self.logger.error(f"Error loading index: {str(e)}")

        self.print_indexed_chunks()
