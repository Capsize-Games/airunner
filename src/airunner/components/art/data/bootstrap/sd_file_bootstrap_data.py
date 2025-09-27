from airunner.settings import AIRUNNER_ART_ENABLED


SD_FILE_BOOTSTRAP_DATA = {
    "SD 1.5": {
        "txt2img": [
            "scheduler/scheduler_config.json",
            "unet/config.json",
            "v1-inference.yaml",
            "vae/config.json",
            "model_index.json",
            "text_encoder/config.json",
            "tokenizer/merges.txt",
            "tokenizer/special_tokens_map.json",
            "tokenizer/tokenizer_config.json",
            "tokenizer/vocab.json",
        ],
        "inpaint": [
            "feature_extractor/preprocessor_config.json",
            "safety_checker/config.json",
            "scheduler/scheduler_config.json",
            "text_encoder/config.json",
            "tokenizer/merges.txt",
            "tokenizer/special_tokens_map.json",
            "tokenizer/tokenizer_config.json",
            "tokenizer/vocab.json",
            "unet/config.json",
            "vae/config.json",
            "config.json",
            "model_index.json",
        ],
        "inpaint_vae": [
            "config.json",
        ],
        "controlnet": [
            "config.json",
            "diffusion_pytorch_model.fp16.safetensors",
        ],
        "safety_checker": [
            "config.json",
            "preprocessor_config.json",
            "pytorch_model.bin",
        ],
        "feature_extractor": [
            "config.json",
            "model.safetensors",
            "preprocessor_config.json",
            "special_tokens_map.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "vocab.json",
        ],
    },
    "SDXL 1.0": {
        "txt2img": [
            "scheduler/scheduler_config.json",
            "text_encoder/config.json",
            "text_encoder_2/config.json",
            "tokenizer/merges.txt",
            "tokenizer/special_tokens_map.json",
            "tokenizer/tokenizer_config.json",
            "tokenizer/vocab.json",
            "tokenizer_2/merges.txt",
            "tokenizer_2/special_tokens_map.json",
            "tokenizer_2/tokenizer_config.json",
            "tokenizer_2/vocab.json",
            "unet/config.json",
            "vae/config.json",
            "vae_1_0/config.json",
            "vae_decoder/config.json",
            "vae_encoder/config.json",
            "LICENSE.md",
            "model_index.json",
        ],
        "inpaint": [
            "scheduler/scheduler_config.json",
            "text_encoder/config.json",
            "text_encoder_2/config.json",
            "tokenizer/merges.txt",
            "tokenizer/special_tokens_map.json",
            "tokenizer/tokenizer_config.json",
            "tokenizer/vocab.json",
            "tokenizer_2/merges.txt",
            "tokenizer_2/special_tokens_map.json",
            "tokenizer_2/tokenizer_config.json",
            "tokenizer_2/vocab.json",
            "unet/config.json",
            "vae/config.json",
            "model_index.json",
        ],
        "controlnet": [
            "config.json",
            "diffusion_pytorch_model.fp16.safetensors",
        ],
    },
}


if not AIRUNNER_ART_ENABLED:
    SD_FILE_BOOTSTRAP_DATA = {}
