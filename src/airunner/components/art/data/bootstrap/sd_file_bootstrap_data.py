from airunner.settings import AIRUNNER_ART_ENABLED


# Bootstrap data for art models.
# Format: {version: {pipeline_action: {filename: expected_size_in_bytes}}}
# File sizes are used to detect incomplete downloads and resume them.
SD_FILE_BOOTSTRAP_DATA = {
    "SDXL 1.0": {
        "txt2img": {
            "scheduler/scheduler_config.json": 479,
            "text_encoder/config.json": 565,
            "text_encoder_2/config.json": 575,
            "tokenizer/merges.txt": 524619,
            "tokenizer/special_tokens_map.json": 472,
            "tokenizer/tokenizer_config.json": 737,
            "tokenizer/vocab.json": 1059962,
            "tokenizer_2/merges.txt": 524619,
            "tokenizer_2/special_tokens_map.json": 460,
            "tokenizer_2/tokenizer_config.json": 725,
            "tokenizer_2/vocab.json": 1059962,
            "unet/config.json": 1680,
            "vae/config.json": 642,
            "vae_1_0/config.json": 607,
            "vae_decoder/config.json": 607,
            "vae_encoder/config.json": 607,
            "LICENSE.md": 14109,
            "model_index.json": 609,
        },
        "inpaint": {
            "scheduler/scheduler_config.json": 479,
            "text_encoder/config.json": 565,
            "text_encoder_2/config.json": 575,
            "tokenizer/merges.txt": 524619,
            "tokenizer/special_tokens_map.json": 472,
            "tokenizer/tokenizer_config.json": 737,
            "tokenizer/vocab.json": 1059962,
            "tokenizer_2/merges.txt": 524619,
            "tokenizer_2/special_tokens_map.json": 460,
            "tokenizer_2/tokenizer_config.json": 725,
            "tokenizer_2/vocab.json": 1059962,
            "unet/config.json": 1680,
            "vae/config.json": 642,
            "model_index.json": 609,
        },
        "controlnet": {
            "config.json": 0,  # Size varies by controlnet model
            "diffusion_pytorch_model.fp16.safetensors": 0,  # Size varies by controlnet model
        },
    },
    "Upscaler": {
        "x4": {
            "low_res_scheduler/scheduler_config.json": 300,
            "scheduler/scheduler_config.json": 348,
            "text_encoder/config.json": 634,
            "text_encoder/model.fp16.safetensors": 680821096,
            "tokenizer/merges.txt": 524619,
            "tokenizer/special_tokens_map.json": 460,
            "tokenizer/tokenizer_config.json": 825,
            "tokenizer/vocab.json": 1059962,
            "unet/config.json": 982,
            "unet/diffusion_pytorch_model.fp16.safetensors": 946878752,
            "vae/config.json": 587,
            "vae/diffusion_pytorch_model.fp16.safetensors": 110674374,
            "model_index.json": 485,
            "x4-upscaler-ema.safetensors": 3531269371,
        },
    },
    "Z-Image Turbo": {
        "txt2img": {
            "model_index.json": 467,
            "scheduler/scheduler_config.json": 173,
            "text_encoder/config.json": 726,
            "text_encoder/generation_config.json": 239,
            "text_encoder/model-00001-of-00003.safetensors": 3957900840,
            "text_encoder/model-00002-of-00003.safetensors": 3987450520,
            "text_encoder/model-00003-of-00003.safetensors": 99630640,
            "text_encoder/model.safetensors.index.json": 32819,
            "tokenizer/merges.txt": 1671853,
            "tokenizer/tokenizer.json": 11422654,
            "tokenizer/tokenizer_config.json": 9732,
            "tokenizer/vocab.json": 2776833,
            "transformer/config.json": 473,
            "transformer/diffusion_pytorch_model-00001-of-00003.safetensors": 9973693184,
            "transformer/diffusion_pytorch_model-00002-of-00003.safetensors": 9973714824,
            "transformer/diffusion_pytorch_model-00003-of-00003.safetensors": 4672282880,
            "transformer/diffusion_pytorch_model.safetensors.index.json": 48969,
            "vae/config.json": 805,
            "vae/diffusion_pytorch_model.safetensors": 167666902,
        },
    },
    "Safety Checker": {
        "safety_checker": {
            "config.json": 4549,
            "pytorch_model.bin": 1216067303,
            "preprocessor_config.json": 342,
        },
    },
}


if not AIRUNNER_ART_ENABLED:
    SD_FILE_BOOTSTRAP_DATA = {}
