import json
import random
import os
import torch
from llama_index.llms.groq import Groq
from llama_index.core.chat_engine.types import AgentChatResponse
from peft import LoraConfig, get_peft_model, PeftModel
from typing import Optional, Dict
from transformers import TrainingArguments, Trainer
from transformers.utils.quantization_config import BitsAndBytesConfig, GPTQConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation.streamers import TextIteratorStreamer
from datasets import Dataset
from airunner.handlers.base_handler import BaseHandler
from airunner.enums import SignalCode, ModelType, ModelStatus, LLMActionType
from airunner.settings import MAX_SEED
from airunner.utils.clear_memory import clear_memory
from airunner.handlers.llm.agent.mistral_agent import MistralAgentQObject
from airunner.data.models.conversation import Conversation


class CausalLMTransformerBaseHandler(
    BaseHandler
):
    model_type = ModelType.LLM

    def __init__(self, *args, **kwargs):
        self.model_type = ModelType.LLM
        self.model_class = "llm"
        self.agent_options = kwargs.pop("agent_options", {})
        self._model = None
        self._streamer = None
        self._chat_engine = None
        self._chat_agent: Optional[MistralAgentQObject] = None
        self._llm_with_tools = None
        self._agent_executor = None
        self._embed_model = None
        self._service_context_model = None
        self._use_query_engine: bool = False
        self._use_chat_engine: bool = True
        self._user_evaluation: str = ""
        self._restrict_tools_to_additional: bool = True
        self._return_agent_code: bool = False
        self._rag_tokenizer = None
        self._rag_retriever = None
        self._do_quantize_model = kwargs.pop("do_quantize_model", False)
        self._vocoder = None
        self._current_model_path = kwargs.get("current_model_path", "")
        self._history = []
        self._set_attention_mask = kwargs.get("set_attention_mask", False)
        self._do_push_to_hub = kwargs.get("do_push_to_hub", False)
        self._llm_int8_enable_fp32_cpu_offload = kwargs.get("llm_int8_enable_fp32_cpu_offload", True)
        self._generator_name = kwargs.get("generator_name", "")
        self._return_result = kwargs.get("return_result", True)
        self._skip_special_tokens = kwargs.get("skip_special_tokens", True)
        self._processing_request = kwargs.get("_processing_request", False)
        self._bad_words_ids = kwargs.get("bad_words_ids", None)
        self._bos_token_id = kwargs.get("bos_token_id", None)
        self._pad_token_id = kwargs.get("pad_token_id", None)
        self._eos_token_id = kwargs.get("eos_token_id", None)
        self._no_repeat_ngram_size = kwargs.get("no_repeat_ngram_size", 1)
        self._decoder_start_token_id = kwargs.get("decoder_start_token_id", None)
        self._tokenizer = None
        self._generator = None

        super().__init__(*args, **kwargs)

    @property
    def is_mistral(self) -> bool:
        path = self._current_model_path.lower()
        return "ministral" in path

    @property
    def is_llama_instruct(self):
        path = self._current_model_path.lower()
        if "instruct" in path and "llama" in path:
            return True
        return False

    @property
    def chat_template(self):
        if self.is_mistral:
            return (
                "{% for message in messages %}"
                "{% if message['role'] == 'system' %}"
                "{{ '[INST] <<SYS>>' + message['content'] + ' <</SYS>>[/INST]' }}"
                "{% elif message['role'] == 'user' %}"
                "{{ '[INST]' + message['content'] + ' [/INST]' }}"
                "{% elif message['role'] == 'assistant' %}"
                "{{ message['content'] + eos_token + ' ' }}"
                "{% endif %}"
                "{% endfor %}"
            )
        elif self.is_llama_instruct:
            return (
                "{{ '<|begin_of_text|>' }}"
                "{% for message in messages %}"
                "{{ '<|start_header_id|>' + "
                "message['role'] + '<|end_header_id|>' + '\n\n' + message['content'] + "
                "'<|end_header_id|>\n\n' + message['content'] + '<|eot_id|>' }}"
                "{% endfor %}"
            )

    @property
    def username(self):
        return self.user.username

    @property
    def botname(self):
        if self.chatbot.assign_names:
            return self.chatbot.botname
        return "Assistant"

    @property
    def _quantization_config(self):
        config = None
        if self.llm_dtype == "8bit":
            config = BitsAndBytesConfig(
                load_in_4bit=False,
                load_in_8bit=True,
                llm_int8_threshold=6.0,
                llm_int8_has_fp16_weight=False,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type='nf4',
            )
        elif self.llm_dtype == "4bit":
            config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16  # changed to match input type
            )
        elif self.llm_dtype == "2bit":
            config = GPTQConfig(
                bits=2,
                dataset="c4",
                tokenizer=self._tokenizer
            )
        return config

    @property
    def use_cache(self):
        if self.llm_generator_settings.override_parameters:
            return self.llm_generator_settings.use_cache
        return self.chatbot.use_cache

    @property
    def model_version(self) -> str:
        model_version = self.chatbot.model_version
        if self.llm_generator_settings.override_parameters:
            model_version = self.llm_generator_settings.model_version
        return model_version

    @property
    def finetuned_model_directory(self) -> str:
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text",
                "models",
                "llm",
                "causallm",
                self.model_version,
                "fine_tuned_mistral_qllm"
            )
        )

    @property
    def latest_checkpoint(self) -> Optional[str]:
        latest_checkpoint = None
        if os.path.exists(self.finetuned_model_directory):
            checkpoints = [
                os.path.join(
                    self.finetuned_model_directory, 
                    d
                ) for d in os.listdir(
                    self.finetuned_model_directory
                ) if d.startswith(
                    "checkpoint-"
                )
            ]
            if checkpoints:
                latest_checkpoint = max(checkpoints, key=os.path.getmtime)
        return latest_checkpoint

    @property
    def model_path(self):
        return os.path.expanduser(os.path.join(
            self.path_settings.base_path,
            "text",
            "models",
            "llm",
            "causallm",
            self.model_version
        ))
    
    @property
    def adapter_path(self):
        base = self.path_settings.base_path
        return os.path.expanduser(os.path.join(
            base,
            "text",
            "models",
            "llm",
            "causallm",
            self.model_version,
            "user_memory_adapter"
        ))

    def load(self):
        if self.model_status in (
            ModelStatus.LOADING,
            ModelStatus.LOADED
        ):
            return
        self.unload()
        self.change_model_status(ModelType.LLM, ModelStatus.LOADING)
        self._current_model_path = self.model_path
        self._load_tokenizer()
        self._load_model()
        self._load_streamer()
        self._load_agent()
        if self._model and self._tokenizer and self._streamer and self._chat_agent:
            self.change_model_status(ModelType.LLM, ModelStatus.LOADED)
        else:
            self.change_model_status(ModelType.LLM, ModelStatus.FAILED)

    def unload(self):
        if self.model_status in (
            ModelStatus.LOADING,
            ModelStatus.UNLOADED
        ):
            return
        self.logger.debug("Unloading LLM")
        self.change_model_status(ModelType.LLM, ModelStatus.LOADING)
        self._unload_streamer()
        self._unload_llm_with_tools()
        self._unload_agent_executor()
        self._unload_embed_model()
        self._unload_model()
        self._unload_tokenizer()
        self._unload_agent()
        clear_memory()
        self.change_model_status(ModelType.LLM, ModelStatus.UNLOADED)

    def handle_request(self, data: Dict) -> AgentChatResponse:
        self.logger.debug("Handling request")
        self._processing_request = True
        self._do_set_seed()
        self.load()
        self._processing_request = True
        action = self.llm_generator_settings.action
        if type(action) is str:
            action = LLMActionType[action]
        return self._do_generate(
            data["request_data"]["prompt"],
            action
        )
    
    def chat(self, prompt) -> AgentChatResponse:
        return self._do_generate(prompt, LLMActionType.CHAT)
    
    def train(self):
        conversation_objects = self.session.query(Conversation).all()
        messages = []
        for conversation in conversation_objects:
            conv_text = ""
            roles = conversation.value
            for i in range(0, len(roles), 2):
                user_msg = roles[i]["blocks"][0]["text"]
                assistant_msg = ""
                if i + 1 < len(roles) and roles[i + 1]["role"] == "assistant":
                    assistant_msg = roles[i + 1]["blocks"][0]["text"]
                conv_text += f"<s>[INST] {user_msg} [/INST]{assistant_msg}</s>"
            messages.append(conv_text)
        dataset = Dataset.from_dict({"text": messages})
        # Configure QLoRA Parameters for Fine-Tuning
        lora_config = LoraConfig(
            r=8,  # Increased rank for better model capacity
            lora_alpha=32,  # Increased alpha for stronger adaptations
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # Added more target modules
            lora_dropout=0.0,  # set dropout to zero to boost memorization
            bias="none",
            task_type="CAUSAL_LM"
        )

        # Apply LoRA configuration to the model
        try:
            self._model = get_peft_model(self._model, lora_config)
            self._model.print_trainable_parameters()
            self._model.config.use_cache = False
            self._model.enable_input_require_grads()
        except AttributeError as e:
            self.logger.error(f"Error applying LoRA configuration: {e}")

        # Get the latest step number from existing checkpoints
        last_step = 0
        if os.path.exists(self.finetuned_model_directory):
            checkpoints = [
                d for d in os.listdir(self.finetuned_model_directory)
                if d.startswith("checkpoint-")
            ]
            if checkpoints:
                last_step = max(
                    int(cp.split("-")[1]) 
                    for cp in checkpoints
                )

        # Define Training Arguments with resumed training
        training_args = TrainingArguments(
            output_dir=self.finetuned_model_directory,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=16,
            learning_rate=1e-4,
            warmup_steps=50,
            num_train_epochs=50,
            max_steps=last_step + 1,  # Increment the step count
            logging_steps=1,
            save_steps=1,
            save_total_limit=None,
            fp16=True,
            optim="adamw_torch",
            gradient_checkpointing=True,
            report_to="none",
            overwrite_output_dir=False
        )

        # Train the QLoRA Model on Conversations
        def tokenize_function(examples):
            tokens = self._tokenizer(examples["text"], truncation=True, padding="max_length", max_length=128)
            tokens["labels"] = tokens["input_ids"].copy()
            return tokens

        self._tokenizer.pad_token = self._tokenizer.eos_token
        tokenized_dataset = dataset.map(tokenize_function, batched=True)

        trainer = Trainer(
            model=self._model,
            args=training_args,
            train_dataset=tokenized_dataset
        )

        self.logger.info(f"Resuming training from step {last_step}...")
        trainer.train(resume_from_checkpoint=self.latest_checkpoint)
        
        self.logger.info("Training completed.")
        self.logger.info("Saving finetuned model")
        self._model.save_pretrained(self.adapter_path)
        
        # Create minimal config
        minimal_config = {
            "name_or_path": self.model_path,
            "tokenizer_class": self._tokenizer.__class__.__name__,
            "model_max_length": self._tokenizer.model_max_length,
            "padding_side": self._tokenizer.padding_side,
            "truncation_side": getattr(self._tokenizer, "truncation_side", "right"),
            "special_tokens": {
                "bos_token": self._tokenizer.bos_token,
                "eos_token": self._tokenizer.eos_token,
                "unk_token": self._tokenizer.unk_token,
                "pad_token": self._tokenizer.pad_token,
            }
        }
        
        if hasattr(self._tokenizer, 'chat_template') and self._tokenizer.chat_template:
            minimal_config["chat_template"] = self._tokenizer.chat_template
                
        # Save the config
        config_path = os.path.join(self.adapter_path, "tokenizer_config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(minimal_config, f, indent=2, ensure_ascii=False)

        print(f"✅ QLoRA Adapter saved to: {self.adapter_path}")

    def do_interrupt(self):
        """
        Public method to interrupt the chat process
        """
        if self._chat_agent:
            self._chat_agent.interrupt_process()

    def clear_history(self, data: Optional[Dict] = None):
        """
        Public method to clear the chat agent history
        """
        if not self._chat_agent:
            return
        self.logger.debug("Clearing chat history")
        self._chat_agent.clear_history(data)

    def add_chatbot_response_to_history(self, message):
        """
        Public method to add a chatbot response to the chat agent history
        """
        self._chat_agent.add_chatbot_response_to_history(message)

    def load_conversation(self, message):
        """
        Public method to load a conversation into the chat agent
        """
        self._chat_agent.on_load_conversation(message)

    def reload_rag(self):
        """
        Public method to reload the RAG model
        """
        self._chat_agent.reload_rag_engine()

    def _load_tokenizer(self):
        if self._tokenizer is not None:
            return
        self.logger.debug(f"Loading tokenizer from {self.model_path}")  # Changed path variable
        kwargs = {
            "local_files_only": True,
            "device_map": self.device,
            "trust_remote_code": False,
            "torch_dtype": self.torch_dtype,
            "attn_implementation": "flash_attention_2",
        }

        if self.chat_template:
            kwargs["chat_template"] = self.chat_template
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,  # Changed to use current_model_path
                **kwargs,
            )
            self.logger.debug("Tokenizer loaded")
        except Exception as e:
            self.logger.error(e)

        if self._tokenizer:
            self._tokenizer.use_default_system_prompt = False
        else:
            self.logger.error("Tokenizer failed to load")

    def _load_model(self):
        if self._model is not None:
            return
        self.logger.debug("transformer_base_handler.load_model Loading model")
        if self.llm_generator_settings.use_api:
            self._model = Groq(
                model=self.llm_generator_settings.api_model,
                api_key=self.llm_generator_settings.api_key,
            )
        else:
            self._load_model_local()

    def _load_streamer(self):
        if self._streamer is not None:
            return
        self.logger.debug("Loading LLM text streamer")
        self._streamer = TextIteratorStreamer(self._tokenizer)

    def _load_agent(self):
        if self._chat_agent is not None:
            return
        self.logger.debug("Loading agent")
        # def get_weather(
        #     location: str = Field(
        #         description="The location to get the weather for.",
        #     )
        # ) -> str:
        #     """Get the weather report for a given location."""
        #     return f"{location} is sunny today."

        tools = [
            # FunctionTool.from_defaults(
            #     get_weather,
            #     return_direct=True
            # ),
        ]
        self._chat_agent = MistralAgentQObject(
            model=self._model,
            tokenizer=self._tokenizer,
            default_tool_choice=None
        )

    def _unload_streamer(self):
        self.logger.debug("Unloading streamer")
        del self._streamer
        self._streamer = None

    def _unload_llm_with_tools(self):
        self.logger.debug("Unloading LLM with tools")
        del self._llm_with_tools
        self._llm_with_tools = None

    def _unload_agent_executor(self):
        self.logger.debug("Unloading agent executor")
        del self._agent_executor
        self._agent_executor = None

    def _unload_embed_model(self):
        self.logger.debug("Unloading embed model")
        del self._embed_model
        self._embed_model = None

    def _unload_model(self):
        self.logger.debug("Unloading model")
        self._model = None
        return True

    def _unload_tokenizer(self):
        self.logger.debug("Unloading tokenizer")
        del self._tokenizer
        self._tokenizer = None
        clear_memory(self.memory_settings.default_gpu_llm)
        return True

    def _unload_agent(self):
        self.logger.debug("Unloading agent")
        do_clear_memory = False
        if self._chat_agent is not None:
            self.logger.debug("Unloading chat agent")
            self._chat_agent.unload()
            del self._chat_agent
            self._chat_agent = None
            do_clear_memory = True
        return do_clear_memory

    def _load_model_local(self):
        self.logger.debug(f"Loading local LLM model from {self.model_path}")
        params = {
            "local_files_only": True,
            "use_cache": self.use_cache,
            "trust_remote_code": False,
            "torch_dtype": self.torch_dtype,
            "device_map": self.device,
        }
        if self._do_quantize_model and self.use_cuda:
            config = self._quantization_config
            if config:
                config.bnb_4bit_compute_dtype = torch.float16
                params["quantization_config"] = config
        try:
            # Use the same path as tokenizer
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                **params
            )
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return
        
        try:
            if os.path.exists(self.adapter_path):
                # Apply LoRA config before loading adapter
                lora_config = LoraConfig(
                    r=8,
                    lora_alpha=32,
                    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                    lora_dropout=0.0,
                    bias="none",
                    task_type="CAUSAL_LM"
                )
                
                # Convert base model to PEFT format first
                self._model = get_peft_model(self._model, lora_config)
                
                # Now load the adapter weights
                self._model = PeftModel.from_pretrained(
                    self._model,
                    self.adapter_path,
                    is_trainable=True,
                    adapter_name="default"
                )
                
                # Merge adapter weights with base model
                self._model = self._model.merge_and_unload()
                
                self.logger.info("Successfully loaded and merged adapter weights")
        except Exception as e:
            self.logger.error(f"Error loading adapter (continuing with base model): {e}")

    def _do_generate(
        self, 
        prompt: str, 
        action: LLMActionType
    ) -> AgentChatResponse:
        self.logger.debug("Generating response")
        if self._current_model_path != self.model_path:
            self.unload()
            self.load()
        # if action is LLMActionType.CHAT and self.chatbot.use_mood:
        #     action = LLMActionType.UPDATE_MOOD
        response = self._chat_agent.chat(prompt, action)
        if action is LLMActionType.CHAT:
            self._send_final_message()
        return response

    def _emit_streamed_text_signal(self, **kwargs):
        self.logger.debug("Emitting streamed text signal")
        kwargs["name"] = self.botname
        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL,
            kwargs
        )

    def _send_final_message(self):
        self.logger.debug("Sending final message")
        self._emit_streamed_text_signal(
            message="",
            is_first_message=False,
            is_end_of_message=True
        )

    def _do_set_seed(self):
        self.logger.debug("Setting seed")

        if self.llm_generator_settings.override_parameters:
            seed = self.llm_generator_settings.seed
            random_seed = self.llm_generator_settings.random_seed
        else:
            seed = self.chatbot.seed
            random_seed = self.chatbot.random_seed

        if random_seed:
            seed = random.randint(-MAX_SEED, MAX_SEED)

        torch.manual_seed(seed)
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        random.seed(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        if self._tokenizer:
            self._tokenizer.seed = seed

    def _save_quantized_model(self):
        self.logger.debug("Saving quantized model to cache")
        self._model.save_pretrained(self.model_path)

    def _clear_memory(self):
        self.logger.debug("Clearing memory")
        clear_memory(self.memory_settings.default_gpu_llm)

    def _prepare_config_for_save(self, config_dict):
        """Convert numpy dtypes to strings in config dictionary."""
        cleaned_config = {}
        for key, value in config_dict.items():
            if hasattr(value, 'dtype'):
                cleaned_config[key] = str(value.dtype)
            elif isinstance(value, dict):
                cleaned_config[key] = self._prepare_config_for_save(value)
            else:
                cleaned_config[key] = value
        return cleaned_config
