"""Bootstrap data for LLM models.

Format: {repo_id: {path_settings: str, context_length: int, capabilities: dict, files: {filename: expected_size_in_bytes}}}
File sizes are used to detect incomplete downloads and resume them.
This mirrors the SD_FILE_BOOTSTRAP_DATA format for consistency.

Capabilities:
- function_calling: Whether the model can call functions/tools reliably
- thinking_capable: Whether the model supports "thinking mode" reasoning blocks
  - Qwen3: <think>...</think> tags
  - Ministral 3 Reasoning: [THINK]...[/THINK] tags
- thinking_tag_format: Optional. "brackets" for [THINK], "angle" (default) for <think>
- rag_capable: Whether the model works well for RAG (retrieval augmented generation)
- vision_capable: Whether the model can process images
- code_capable: Whether the model is good at code generation
- is_embedding_model: Whether this is an embedding model (not a chat model)
"""

LLM_FILE_BOOTSTRAP_DATA = {
    # NOTE: Meta Llama 3.1 8B removed - outdated compared to Qwen3/Ministral3
    # Meta does not have an 8B model comparable to current generation models
    # Llama 3.3 is 70B only (too large for most consumer GPUs)
    "Qwen/Qwen3-8B-GGUF": {
        "path_settings": "llm_causallm_model_path",
        "context_length": 32768,
        "native_context_length": 32768,
        "yarn_max_context_length": 131072,
        "capabilities": {
            "function_calling": True,
            "thinking_capable": True,  # Supports both modes via enable_thinking flag
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "is_embedding_model": False,
        },
        "files": {
            "Qwen3-8B-Q4_K_M.gguf": 5026889920,
        },
    },
    # Code-specialized models
    "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF": {
        "path_settings": "llm_causallm_model_path",
        "context_length": 131072,
        "capabilities": {
            "function_calling": True,
            "thinking_capable": False,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,  # Primary purpose
            "is_embedding_model": False,
        },
        "files": {
            # Official Qwen GGUF Q4_K_M (4.68GB)
            "qwen2.5-coder-7b-instruct-q4_k_m.gguf": 4876509632,
        },
    },
    "CohereForAI/c4ai-command-r-08-2024": {
        "path_settings": "llm_causallm_model_path",
        "context_length": 131072,
        "capabilities": {
            "function_calling": True,
            "thinking_capable": False,
            "rag_capable": True,
            "vision_capable": False,
            "code_capable": True,
            "is_embedding_model": False,
        },
        "files": {
            "config.json": 639,
            "generation_config.json": 137,
            "model-00001-of-00014.safetensors": 4898947792,
            "model-00002-of-00014.safetensors": 4932553528,
            "model-00003-of-00014.safetensors": 4932570024,
            "model-00004-of-00014.safetensors": 4831890592,
            "model-00005-of-00014.safetensors": 4932553560,
            "model-00006-of-00014.safetensors": 4932553552,
            "model-00007-of-00014.safetensors": 4932570048,
            "model-00008-of-00014.safetensors": 4831890616,
            "model-00009-of-00014.safetensors": 4932553560,
            "model-00010-of-00014.safetensors": 4932553552,
            "model-00011-of-00014.safetensors": 4932570048,
            "model-00012-of-00014.safetensors": 4831890616,
            "model-00013-of-00014.safetensors": 4932553560,
            "model-00014-of-00014.safetensors": 805339584,
            "model.safetensors.index.json": 26206,
            "special_tokens_map.json": 439,
            "tokenizer.json": 12778456,
            "tokenizer_config.json": 21742,
        },
    },
    # NOTE: Using BF16 version because the standard FP8 version cannot be
    # requantized with BitsAndBytes (FP8 tensors are incompatible with 4-bit quantization)
    "mistralai/Ministral-3-8B-Instruct-2512-BF16": {
        "path_settings": "llm_causallm_model_path",
        "context_length": 262144,
        "capabilities": {
            "function_calling": True,
            "thinking_capable": False,
            "rag_capable": True,
            "vision_capable": True,
            "code_capable": True,
            "is_embedding_model": False,
        },
        # IMPORTANT: Config files need patching after download:
        # - config.json: text_config.model_type "ministral3" -> "mistral"
        # - tokenizer_config.json: tokenizer_class "TokenizersBackend" -> "PreTrainedTokenizerFast"
        # - tokenizer_config.json: remove extra_special_tokens (wrong format)
        # See airunner.components.llm.utils.ministral3_config_patcher
        "requires_config_patch": True,
        "files": {
            # Use sharded safetensors (faster download, same model)
            # consolidated.safetensors (17.8GB) is also available but we use sharded
            "chat_template.jinja": 7753,
            # config.json: size 0 = skip validation (file is patched post-download)
            # Original: 1579 bytes, Patched: ~1575 bytes
            "config.json": 0,
            "generation_config.json": 131,
            "model-00001-of-00004.safetensors": 4984292952,
            "model-00002-of-00004.safetensors": 4999804256,
            "model-00003-of-00004.safetensors": 4915917680,
            "model-00004-of-00004.safetensors": 2936108304,
            "model.safetensors.index.json": 52675,
            "params.json": 1098,
            "processor_config.json": 976,
            "special_tokens_map.json": 147085,
            "tekken.json": 16753777,
            "tokenizer.json": 17078110,
            # tokenizer_config.json: size 0 = skip validation (file is patched post-download)
            # Original: 198076 bytes, Patched: ~196KB (extra_special_tokens removed)
            "tokenizer_config.json": 0,
        },
    },
    "mistralai/Ministral-3-8B-Instruct-2512-GGUF": {
        # NOTE: GGUF disabled in provider_config.py - llama-cpp-python 0.3.16 doesn't support
        # the mistral3 architecture (vision-language model). Keep metadata for future use.
        "path_settings": "llm_causallm_model_path",
        "context_length": 262144,
        "capabilities": {
            "function_calling": True,
            "thinking_capable": False,
            "rag_capable": True,
            "vision_capable": True,
            "code_capable": True,
            "is_embedding_model": False,
        },
        "files": {
            # Official Mistral GGUF Q4_K_M (5.2GB)
            "Ministral-3-8B-Instruct-2512-Q4_K_M.gguf": 5583200704,
        },
    },
    "mistralai/Ministral-3-8B-Reasoning-2512": {
        "path_settings": "llm_causallm_model_path",
        "context_length": 262144,
        "requires_config_patch": True,
        "capabilities": {
            "function_calling": True,
            "thinking_capable": True,
            "thinking_tag_format": "brackets",  # [THINK]...[/THINK]
            "rag_capable": True,
            "vision_capable": True,
            "code_capable": True,
            "is_embedding_model": False,
        },
        "files": {
            # BF16 model - larger than FP8 Instruct variant (~17.8GB total)
            # Uses sharded safetensors (model-00001/2/3/4-of-00004.safetensors)
            "chat_template.jinja": 6206,
            # config.json is patched post-download; skip strict size validation
            "config.json": 0,
            "generation_config.json": 131,
            "model-00001-of-00004.safetensors": 4984292952,
            "model-00002-of-00004.safetensors": 4999804256,
            "model-00003-of-00004.safetensors": 4915917680,
            "model-00004-of-00004.safetensors": 2936108304,
            "model.safetensors.index.json": 52675,
            "params.json": 1098,
            "processor_config.json": 976,
            "special_tokens_map.json": 147085,
            "tekken.json": 16753777,
            "tokenizer.json": 17078110,
            # tokenizer_config.json is patched post-download; skip strict size validation
            "tokenizer_config.json": 0,
        },
    },
    "mistralai/Ministral-3-8B-Reasoning-2512-GGUF": {
        # NOTE: GGUF disabled in provider_config.py - llama-cpp-python 0.3.16 doesn't support
        # the mistral3 architecture (vision-language model). Keep metadata for future use.
        "path_settings": "llm_causallm_model_path",
        "context_length": 262144,
        "capabilities": {
            "function_calling": True,
            "thinking_capable": True,
            "thinking_tag_format": "brackets",  # [THINK]...[/THINK]
            "rag_capable": True,
            "vision_capable": True,
            "code_capable": True,
            "is_embedding_model": False,
        },
        "files": {
            # Official Mistral GGUF Q4_K_M (5.2GB)
            "Ministral-3-8B-Reasoning-2512-Q4_K_M.gguf": 5583200704,
        },
    },
    "sentence-transformers/sentence-t5-large": {
        "path_settings": "sentence_transformers_path",
        "context_length": 512,
        "capabilities": {
            "function_calling": False,
            "thinking_capable": False,
            "rag_capable": False,
            "vision_capable": False,
            "code_capable": False,
            "is_embedding_model": True,
        },
        "files": {
            "1_Pooling/config.json": 190,
            "2_Dense/config.json": 116,
            "2_Dense/model.safetensors": 3145848,
            "config.json": 1388,
            "config_sentence_transformers.json": 122,
            "model.safetensors": 669902800,
            "modules.json": 461,
            "sentence_bert_config.json": 53,
            "special_tokens_map.json": 1786,
            "spiece.model": 791656,
            "tokenizer.json": 1387554,
            "tokenizer_config.json": 1924,
        },
    },
    "intfloat/e5-large": {
        "path_settings": "text_embedding",
        "context_length": 512,
        "capabilities": {
            "function_calling": False,
            "thinking_capable": False,
            "rag_capable": False,
            "vision_capable": False,
            "code_capable": False,
            "is_embedding_model": True,
        },
        "files": {
            "1_Pooling/config.json": 201,
            "config.json": 611,
            "model.safetensors": 1340616616,
            "modules.json": 387,
            "sentence_bert_config.json": 57,
            "special_tokens_map.json": 112,
            "tokenizer.json": 466081,
            "tokenizer_config.json": 385,
            "vocab.txt": 231508,
        },
    },
    "microsoft/Fara-7B": {
        "path_settings": "llm_fara_model_path",
        "context_length": 32768,
        "capabilities": {
            "function_calling": False,
            "thinking_capable": False,
            "rag_capable": True,
            "vision_capable": True,
            "code_capable": False,
            "is_embedding_model": False,
        },
        "files": {
            "added_tokens.json": 605,
            "chat_template.jinja": 1017,
            "config.json": 2490,
            "generation_config.json": 214,
            "merges.txt": 1671853,
            "model-00001-of-00004.safetensors": 4968243272,
            "model-00002-of-00004.safetensors": 4991495784,
            "model-00003-of-00004.safetensors": 4932751008,
            "model-00004-of-00004.safetensors": 1691924352,
            "model.safetensors.index.json": 57618,
            "preprocessor_config.json": 575,
            "special_tokens_map.json": 613,
            "tokenizer.json": 11421896,
            "tokenizer_config.json": 4730,
            "video_preprocessor_config.json": 1730,
            "vocab.json": 2776833,
        },
    },
}
