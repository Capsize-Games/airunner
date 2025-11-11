from airunner.settings import AIRUNNER_ART_ENABLED


SD_FILE_BOOTSTRAP_DATA = {
    "Flux.1 S": {
        "txt2img": [
            "model_index.json",
            "scheduler/scheduler_config.json",
            "text_encoder/config.json",
            "text_encoder/model.safetensors",
            "text_encoder_2/config.json",
            "text_encoder_2/model-00001-of-00002.safetensors",
            "text_encoder_2/model-00002-of-00002.safetensors",
            "text_encoder_2/model.safetensors.index.json",
            "tokenizer/merges.txt",
            "tokenizer/special_tokens_map.json",
            "tokenizer/tokenizer_config.json",
            "tokenizer/vocab.json",
            "tokenizer_2/special_tokens_map.json",
            "tokenizer_2/spiece.model",
            "tokenizer_2/tokenizer.json",
            "tokenizer_2/tokenizer_config.json",
            "transformer/config.json",
            "transformer/diffusion_pytorch_model-00001-of-00003.safetensors",
            "transformer/diffusion_pytorch_model-00002-of-00003.safetensors",
            "transformer/diffusion_pytorch_model-00003-of-00003.safetensors",
            "transformer/diffusion_pytorch_model.safetensors.index.json",
            "vae/config.json",
            "vae/diffusion_pytorch_model.safetensors",
            "ae.safetensors",
        ],
        "inpaint": [
            "model_index.json",
            "scheduler/scheduler_config.json",
            "text_encoder/config.json",
            "text_encoder/model.safetensors",
            "text_encoder_2/config.json",
            "text_encoder_2/model-00001-of-00002.safetensors",
            "text_encoder_2/model-00002-of-00002.safetensors",
            "text_encoder_2/model.safetensors.index.json",
            "tokenizer/merges.txt",
            "tokenizer/special_tokens_map.json",
            "tokenizer/tokenizer_config.json",
            "tokenizer/vocab.json",
            "tokenizer_2/merges.txt",
            "tokenizer_2/special_tokens_map.json",
            "tokenizer_2/tokenizer_config.json",
            "tokenizer_2/vocab.json",
            "transformer/config.json",
            "transformer/diffusion_pytorch_model-00001-of-00003.safetensors",
            "transformer/diffusion_pytorch_model-00002-of-00003.safetensors",
            "transformer/diffusion_pytorch_model-00003-of-00003.safetensors",
            "transformer/diffusion_pytorch_model.safetensors.index.json",
            "vae/config.json",
            "vae/diffusion_pytorch_model.safetensors",
        ],
    },
}


if not AIRUNNER_ART_ENABLED:
    SD_FILE_BOOTSTRAP_DATA = {}
