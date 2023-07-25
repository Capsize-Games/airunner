from io import BytesIO
from typing import Optional

import requests
import torch
from diffusers import DiffusionPipeline, EulerDiscreteScheduler, DDIMScheduler, PNDMScheduler, LMSDiscreteScheduler, \
    HeunDiscreteScheduler, EulerAncestralDiscreteScheduler, DPMSolverMultistepScheduler, UNet2DConditionModel, \
    AutoencoderKL, PriorTransformer, UnCLIPScheduler, DDPMScheduler
from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker
from diffusers.pipelines.stable_diffusion.convert_from_ckpt import convert_controlnet_checkpoint, \
    create_unet_diffusers_config, convert_ldm_unet_checkpoint, create_vae_diffusers_config, convert_ldm_vae_checkpoint, \
    convert_open_clip_checkpoint, stable_unclip_image_noising_components, stable_unclip_image_encoder, \
    convert_paint_by_example_checkpoint, convert_ldm_clip_checkpoint, create_ldm_bert_config, \
    convert_ldm_bert_checkpoint
from diffusers.utils import is_accelerate_available, is_omegaconf_available, BACKENDS_MAPPING, is_safetensors_available
from transformers import (
    AutoFeatureExtractor,
    BertTokenizerFast,
    CLIPTextModelWithProjection,
    CLIPTokenizer
)
from airunner.aihandler.logger import Logger as logger

if is_accelerate_available():
    from accelerate import init_empty_weights
    from accelerate.utils import set_module_tensor_to_device


def download_from_original_stable_diffusion_ckpt(
    checkpoint_path: str,
    original_config_file: str = None,
    image_size: Optional[int] = None,
    prediction_type: str = None,
    model_type: str = None,
    extract_ema: bool = False,
    scheduler_type: str = "pndm",
    num_in_channels: Optional[int] = None,
    upcast_attention: Optional[bool] = None,
    device: str = None,
    from_safetensors: bool = False,
    stable_unclip: Optional[str] = None,
    stable_unclip_prior: Optional[str] = None,
    clip_stats_path: Optional[str] = None,
    controlnet: Optional[bool] = None,
    load_safety_checker: bool = True,
    pipeline_class: DiffusionPipeline = None,
    local_files_only=False,
    vae_path=None,
    text_encoder=None,
    tokenizer=None,
) -> DiffusionPipeline:
    """
    Load a Stable Diffusion pipeline object from a CompVis-style `.ckpt`/`.safetensors` file and (ideally) a `.yaml`
    config file.

    Although many of the arguments can be automatically inferred, some of these rely on brittle checks against the
    global step count, which will likely fail for models that have undergone further fine-tuning. Therefore, it is
    recommended that you override the default values and/or supply an `original_config_file` wherever possible.

    Args:
        checkpoint_path (`str`): Path to `.ckpt` file.
        original_config_file (`str`):
            Path to `.yaml` config file corresponding to the original architecture. If `None`, will be automatically
            inferred by looking for a key that only exists in SD2.0 models.
        image_size (`int`, *optional*, defaults to 512):
            The image size that the model was trained on. Use 512 for Stable Diffusion v1.X and Stable Diffusion v2
            Base. Use 768 for Stable Diffusion v2.
        prediction_type (`str`, *optional*):
            The prediction type that the model was trained on. Use `'epsilon'` for Stable Diffusion v1.X and Stable
            Diffusion v2 Base. Use `'v_prediction'` for Stable Diffusion v2.
        num_in_channels (`int`, *optional*, defaults to None):
            The number of input channels. If `None`, it will be automatically inferred.
        scheduler_type (`str`, *optional*, defaults to 'pndm'):
            Type of scheduler to use. Should be one of `["pndm", "lms", "heun", "euler", "euler-ancestral", "dpm",
            "ddim"]`.
        model_type (`str`, *optional*, defaults to `None`):
            The pipeline type. `None` to automatically infer, or one of `["FrozenOpenCLIPEmbedder",
            "FrozenCLIPEmbedder", "PaintByExample"]`.
        is_img2img (`bool`, *optional*, defaults to `False`):
            Whether the model should be loaded as an img2img pipeline.
        extract_ema (`bool`, *optional*, defaults to `False`): Only relevant for
            checkpoints that have both EMA and non-EMA weights. Whether to extract the EMA weights or not. Defaults to
            `False`. Pass `True` to extract the EMA weights. EMA weights usually yield higher quality images for
            inference. Non-EMA weights are usually better to continue fine-tuning.
        upcast_attention (`bool`, *optional*, defaults to `None`):
            Whether the attention computation should always be upcasted. This is necessary when running stable
            diffusion 2.1.
        device (`str`, *optional*, defaults to `None`):
            The device to use. Pass `None` to determine automatically.
        from_safetensors (`str`, *optional*, defaults to `False`):
            If `checkpoint_path` is in `safetensors` format, load checkpoint with safetensors instead of PyTorch.
        load_safety_checker (`bool`, *optional*, defaults to `True`):
            Whether to load the safety checker or not. Defaults to `True`.
        pipeline_class (`str`, *optional*, defaults to `None`):
            The pipeline class to use. Pass `None` to determine automatically.
        local_files_only (`bool`, *optional*, defaults to `False`):
            Whether or not to only look at local files (i.e., do not try to download the model).
        text_encoder (`CLIPTextModel`, *optional*, defaults to `None`):
            An instance of [CLIP](https://huggingface.co/docs/transformers/model_doc/clip#transformers.CLIPTextModel)
            to use, specifically the [clip-vit-large-patch14](https://huggingface.co/openai/clip-vit-large-patch14)
            variant. If this parameter is `None`, the function will load a new instance of [CLIP] by itself, if needed.
        tokenizer (`CLIPTokenizer`, *optional*, defaults to `None`):
            An instance of
            [CLIPTokenizer](https://huggingface.co/docs/transformers/v4.21.0/en/model_doc/clip#transformers.CLIPTokenizer)
            to use. If this parameter is `None`, the function will load a new instance of [CLIPTokenizer] by itself, if
            needed.
        return: A StableDiffusionPipeline object representing the passed-in `.ckpt`/`.safetensors` file.
    """

    # import pipelines here to avoid circular import error when using from_single_file method
    from diffusers import (
        LDMTextToImagePipeline,
        PaintByExamplePipeline,
        StableDiffusionControlNetPipeline,
        StableDiffusionInpaintPipeline,
        StableDiffusionPipeline,
        StableDiffusionXLImg2ImgPipeline,
        StableDiffusionXLPipeline,
        StableUnCLIPImg2ImgPipeline,
        StableUnCLIPPipeline,
    )

    if pipeline_class is None:
        pipeline_class = StableDiffusionPipeline

    if prediction_type == "v-prediction":
        prediction_type = "v_prediction"

    if not is_omegaconf_available():
        raise ValueError(BACKENDS_MAPPING["omegaconf"][1])

    from omegaconf import OmegaConf

    if from_safetensors:
        if not is_safetensors_available():
            raise ValueError(BACKENDS_MAPPING["safetensors"][1])

        from safetensors.torch import load_file as safe_load

        checkpoint = safe_load(checkpoint_path, device="cpu")
    else:
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            checkpoint = torch.load(checkpoint_path, map_location=device)
        else:
            checkpoint = torch.load(checkpoint_path, map_location=device)

    # Sometimes models don't have the global_step item
    if "global_step" in checkpoint:
        global_step = checkpoint["global_step"]
    else:
        logger.debug("global_step key not found in model")
        global_step = None

    # NOTE: this while loop isn't great but this controlnet checkpoint has one additional
    # "state_dict" key https://huggingface.co/thibaud/controlnet-canny-sd21
    while "state_dict" in checkpoint:
        checkpoint = checkpoint["state_dict"]

    if original_config_file is None:
        key_name_v2_1 = "model.diffusion_model.input_blocks.2.1.transformer_blocks.0.attn2.to_k.weight"
        key_name_sd_xl_base = "conditioner.embedders.1.model.transformer.resblocks.9.mlp.c_proj.bias"
        key_name_sd_xl_refiner = "conditioner.embedders.0.model.transformer.resblocks.9.mlp.c_proj.bias"

        # model_type = "v1"
        original_config_file = "v1.yaml"

        if key_name_v2_1 in checkpoint and checkpoint[key_name_v2_1].shape[-1] == 1024:
            original_config_file = "v2.yaml"

            if global_step == 110000:
                # v2.1 needs to upcast attention
                upcast_attention = True
        elif key_name_sd_xl_base in checkpoint:
            # only base xl has two text embedders
            original_config_file = "sd_xl_base.yaml"
        elif key_name_sd_xl_refiner in checkpoint:
            # only refiner xl has embedder and one text embedders
            original_config_file = "sd_xl_refiner.yaml"

    original_config = OmegaConf.load(original_config_file)

    # Convert the text model.
    if (
        model_type is None
        and "cond_stage_config" in original_config.model.params
        and original_config.model.params.cond_stage_config is not None
    ):
        model_type = original_config.model.params.cond_stage_config.target.split(".")[-1]
        logger.debug(f"no `model_type` given, `model_type` inferred as: {model_type}")
    elif model_type is None and original_config.model.params.network_config is not None:
        if original_config.model.params.network_config.params.context_dim == 2048:
            model_type = "SDXL"
        else:
            model_type = "SDXL-Refiner"
        if image_size is None:
            image_size = 1024

    if num_in_channels is None and pipeline_class == StableDiffusionInpaintPipeline:
        num_in_channels = 9
    elif num_in_channels is None:
        num_in_channels = 4

    if "unet_config" in original_config.model.params:
        original_config["model"]["params"]["unet_config"]["params"]["in_channels"] = num_in_channels

    if (
        "parameterization" in original_config["model"]["params"]
        and original_config["model"]["params"]["parameterization"] == "v"
    ):
        if prediction_type is None:
            # NOTE: For stable diffusion 2 base it is recommended to pass `prediction_type=="epsilon"`
            # as it relies on a brittle global step parameter here
            prediction_type = "epsilon" if global_step == 875000 else "v_prediction"
        if image_size is None:
            # NOTE: For stable diffusion 2 base one has to pass `image_size==512`
            # as it relies on a brittle global step parameter here
            image_size = 512 if global_step == 875000 else 768
    else:
        if prediction_type is None:
            prediction_type = "epsilon"
        if image_size is None:
            image_size = 512

    if controlnet is None:
        controlnet = "control_stage_config" in original_config.model.params

    if controlnet:
        controlnet_model = convert_controlnet_checkpoint(
            checkpoint, original_config, checkpoint_path, image_size, upcast_attention, extract_ema
        )

    num_train_timesteps = getattr(original_config.model.params, "timesteps", None) or 1000

    if model_type in ["SDXL", "SDXL-Refiner"]:
        scheduler_dict = {
            "beta_schedule": "scaled_linear",
            "beta_start": 0.00085,
            "beta_end": 0.012,
            "interpolation_type": "linear",
            "num_train_timesteps": num_train_timesteps,
            "prediction_type": "epsilon",
            "sample_max_value": 1.0,
            "set_alpha_to_one": False,
            "skip_prk_steps": True,
            "steps_offset": 1,
            "timestep_spacing": "leading",
        }
        scheduler = EulerDiscreteScheduler.from_config(scheduler_dict)
        scheduler_type = "euler"
    else:
        beta_start = getattr(original_config.model.params, "linear_start", None) or 0.02
        beta_end = getattr(original_config.model.params, "linear_end", None) or 0.085
        scheduler = DDIMScheduler(
            beta_end=beta_end,
            beta_schedule="scaled_linear",
            beta_start=beta_start,
            num_train_timesteps=num_train_timesteps,
            steps_offset=1,
            clip_sample=False,
            set_alpha_to_one=False,
            prediction_type=prediction_type,
        )
    # make sure scheduler works correctly with DDIM
    scheduler.register_to_config(clip_sample=False)

    if scheduler_type == "pndm":
        config = dict(scheduler.config)
        config["skip_prk_steps"] = True
        scheduler = PNDMScheduler.from_config(config)
    elif scheduler_type == "lms":
        scheduler = LMSDiscreteScheduler.from_config(scheduler.config)
    elif scheduler_type == "heun":
        scheduler = HeunDiscreteScheduler.from_config(scheduler.config)
    elif scheduler_type == "euler":
        scheduler = EulerDiscreteScheduler.from_config(scheduler.config)
    elif scheduler_type == "euler-ancestral":
        scheduler = EulerAncestralDiscreteScheduler.from_config(scheduler.config)
    elif scheduler_type == "dpm":
        scheduler = DPMSolverMultistepScheduler.from_config(scheduler.config)
    elif scheduler_type == "ddim":
        scheduler = scheduler
    else:
        raise ValueError(f"Scheduler of type {scheduler_type} doesn't exist!")

    # Convert the UNet2DConditionModel model.
    unet_config = create_unet_diffusers_config(original_config, image_size=image_size)
    unet_config["upcast_attention"] = upcast_attention
    with init_empty_weights():
        unet = UNet2DConditionModel(**unet_config)

    converted_unet_checkpoint = convert_ldm_unet_checkpoint(
        checkpoint, unet_config, path=checkpoint_path, extract_ema=extract_ema
    )

    for param_name, param in converted_unet_checkpoint.items():
        set_module_tensor_to_device(unet, param_name, "cpu", value=param)

    # Convert the VAE model.
    if vae_path is None:
        vae_config = create_vae_diffusers_config(original_config, image_size=image_size)
        converted_vae_checkpoint = convert_ldm_vae_checkpoint(checkpoint, vae_config)

        if (
            "model" in original_config
            and "params" in original_config.model
            and "scale_factor" in original_config.model.params
        ):
            vae_scaling_factor = original_config.model.params.scale_factor
        else:
            vae_scaling_factor = 0.18215  # default SD scaling factor

        vae_config["scaling_factor"] = vae_scaling_factor

        with init_empty_weights():
            vae = AutoencoderKL(**vae_config)

        for param_name, param in converted_vae_checkpoint.items():
            set_module_tensor_to_device(vae, param_name, "cpu", value=param)
    else:
        vae = AutoencoderKL.from_pretrained(
            vae_path,
            local_files_only=local_files_only
        )

    if model_type == "FrozenOpenCLIPEmbedder":
        config_name = "stabilityai/stable-diffusion-2"
        config_kwargs = {"subfolder": "text_encoder"}

        text_model = convert_open_clip_checkpoint(checkpoint, config_name, **config_kwargs)
        tokenizer = CLIPTokenizer.from_pretrained(
            "stabilityai/stable-diffusion-2",
            subfolder="tokenizer",
            local_files_only=local_files_only
        )

        if stable_unclip is None:
            if controlnet:
                pipe = StableDiffusionControlNetPipeline(
                    vae=vae,
                    text_encoder=text_model,
                    tokenizer=tokenizer,
                    unet=unet,
                    scheduler=scheduler,
                    controlnet=controlnet_model,
                    safety_checker=None,
                    feature_extractor=None,
                    requires_safety_checker=False,
                )
            else:
                pipe = pipeline_class(
                    vae=vae,
                    text_encoder=text_model,
                    tokenizer=tokenizer,
                    unet=unet,
                    scheduler=scheduler,
                    safety_checker=None,
                    feature_extractor=None,
                    requires_safety_checker=False,
                )
        else:
            image_normalizer, image_noising_scheduler = stable_unclip_image_noising_components(
                original_config, clip_stats_path=clip_stats_path, device=device
            )

            if stable_unclip == "img2img":
                feature_extractor, image_encoder = stable_unclip_image_encoder(original_config)

                pipe = StableUnCLIPImg2ImgPipeline(
                    # image encoding components
                    feature_extractor=feature_extractor,
                    image_encoder=image_encoder,
                    # image noising components
                    image_normalizer=image_normalizer,
                    image_noising_scheduler=image_noising_scheduler,
                    # regular denoising components
                    tokenizer=tokenizer,
                    text_encoder=text_model,
                    unet=unet,
                    scheduler=scheduler,
                    # vae
                    vae=vae,
                )
            elif stable_unclip == "txt2img":
                if stable_unclip_prior is None or stable_unclip_prior == "karlo":
                    karlo_model = "kakaobrain/karlo-v1-alpha"
                    prior = PriorTransformer.from_pretrained(
                        karlo_model,
                        subfolder="prior",
                        local_files_only=local_files_only
                    )

                    prior_tokenizer = CLIPTokenizer.from_pretrained(
                        "openai/clip-vit-large-patch14",
                        local_files_only=local_files_only
                    )
                    prior_text_model = CLIPTextModelWithProjection.from_pretrained(
                        "openai/clip-vit-large-patch14",
                        local_files_only=local_files_only
                    )

                    prior_scheduler = UnCLIPScheduler.from_pretrained(
                        karlo_model,
                        subfolder="prior_scheduler",
                        local_files_only=local_files_only
                    )
                    prior_scheduler = DDPMScheduler.from_config(prior_scheduler.config)
                else:
                    raise NotImplementedError(f"unknown prior for stable unclip model: {stable_unclip_prior}")

                pipe = StableUnCLIPPipeline(
                    # prior components
                    prior_tokenizer=prior_tokenizer,
                    prior_text_encoder=prior_text_model,
                    prior=prior,
                    prior_scheduler=prior_scheduler,
                    # image noising components
                    image_normalizer=image_normalizer,
                    image_noising_scheduler=image_noising_scheduler,
                    # regular denoising components
                    tokenizer=tokenizer,
                    text_encoder=text_model,
                    unet=unet,
                    scheduler=scheduler,
                    # vae
                    vae=vae,
                )
            else:
                raise NotImplementedError(f"unknown `stable_unclip` type: {stable_unclip}")
    elif model_type == "PaintByExample":
        vision_model = convert_paint_by_example_checkpoint(checkpoint)
        tokenizer = CLIPTokenizer.from_pretrained(
            "openai/clip-vit-large-patch14",
            local_files_only=local_files_only
        )
        feature_extractor = AutoFeatureExtractor.from_pretrained(
            "CompVis/stable-diffusion-safety-checker",
            local_files_only=local_files_only
        )
        pipe = PaintByExamplePipeline(
            vae=vae,
            image_encoder=vision_model,
            unet=unet,
            scheduler=scheduler,
            safety_checker=None,
            feature_extractor=feature_extractor,
        )
    elif model_type == "FrozenCLIPEmbedder":
        text_model = convert_ldm_clip_checkpoint(
            checkpoint, local_files_only=local_files_only, text_encoder=text_encoder
        )
        tokenizer = CLIPTokenizer.from_pretrained(
            "openai/clip-vit-large-patch14",
            local_files_only=local_files_only
        ) if tokenizer is None else tokenizer

        if load_safety_checker:
            safety_checker = StableDiffusionSafetyChecker.from_pretrained(
                "CompVis/stable-diffusion-safety-checker",
                local_files_only=local_files_only
            )
            feature_extractor = AutoFeatureExtractor.from_pretrained(
                "CompVis/stable-diffusion-safety-checker",
                local_files_only=local_files_only
            )
        else:
            safety_checker = None
            feature_extractor = None

        if controlnet:
            pipe = StableDiffusionControlNetPipeline(
                vae=vae,
                text_encoder=text_model,
                tokenizer=tokenizer,
                unet=unet,
                controlnet=controlnet_model,
                scheduler=scheduler,
                safety_checker=safety_checker,
                feature_extractor=feature_extractor,
            )
        else:
            pipe = pipeline_class(
                vae=vae,
                text_encoder=text_model,
                tokenizer=tokenizer,
                unet=unet,
                scheduler=scheduler,
                safety_checker=safety_checker,
                feature_extractor=feature_extractor,
            )
    elif model_type in ["SDXL", "SDXL-Refiner"]:
        if model_type == "SDXL":
            tokenizer = CLIPTokenizer.from_pretrained(
                "openai/clip-vit-large-patch14",
                local_files_only=local_files_only
            )
            text_encoder = convert_ldm_clip_checkpoint(checkpoint, local_files_only=local_files_only)
            tokenizer_2 = CLIPTokenizer.from_pretrained(
                "laion/CLIP-ViT-bigG-14-laion2B-39B-b160k",
                pad_token="!",
                local_files_only=local_files_only
            )

            config_name = "laion/CLIP-ViT-bigG-14-laion2B-39B-b160k"
            config_kwargs = {"projection_dim": 1280}
            text_encoder_2 = convert_open_clip_checkpoint(
                checkpoint, config_name, prefix="conditioner.embedders.1.model.", has_projection=True, **config_kwargs
            )

            pipe = StableDiffusionXLPipeline(
                vae=vae,
                text_encoder=text_encoder,
                tokenizer=tokenizer,
                text_encoder_2=text_encoder_2,
                tokenizer_2=tokenizer_2,
                unet=unet,
                scheduler=scheduler,
                force_zeros_for_empty_prompt=True,
            )
        else:
            tokenizer = None
            text_encoder = None
            tokenizer_2 = CLIPTokenizer.from_pretrained(
                "laion/CLIP-ViT-bigG-14-laion2B-39B-b160k",
                pad_token="!",
                local_files_only=local_files_only
            )

            config_name = "laion/CLIP-ViT-bigG-14-laion2B-39B-b160k"
            config_kwargs = {"projection_dim": 1280}
            text_encoder_2 = convert_open_clip_checkpoint(
                checkpoint, config_name, prefix="conditioner.embedders.0.model.", has_projection=True, **config_kwargs
            )

            pipe = StableDiffusionXLImg2ImgPipeline(
                vae=vae,
                text_encoder=text_encoder,
                tokenizer=tokenizer,
                text_encoder_2=text_encoder_2,
                tokenizer_2=tokenizer_2,
                unet=unet,
                scheduler=scheduler,
                requires_aesthetics_score=True,
                force_zeros_for_empty_prompt=False,
            )
    else:
        text_config = create_ldm_bert_config(original_config)
        text_model = convert_ldm_bert_checkpoint(checkpoint, text_config)
        tokenizer = BertTokenizerFast.from_pretrained(
            "bert-base-uncased",
            local_files_only=local_files_only
        )
        pipe = LDMTextToImagePipeline(vqvae=vae, bert=text_model, tokenizer=tokenizer, unet=unet, scheduler=scheduler)

    return pipe