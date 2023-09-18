from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from airunner.data.models import Base, ControlnetModel, Pipeline, Document, Settings, PromptGeneratorSetting, \
    GeneratorSetting, SplitterSection, GridSettings, MetadataSettings, PathSettings, MemorySettings, AIModel, \
    ImageFilter, ImageFilterValue, BrushSettings

engine = create_engine('sqlite:///airunner.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


if not session.query(ControlnetModel).first():
    # Populate the database with some seed data
    session.add(ControlnetModel(name="canny", path="lllyasviel/control_v11p_sd15_canny"))
    session.add(ControlnetModel(name="depth_leres", path="lllyasviel/control_v11f1p_sd15_depth"))
    session.add(ControlnetModel(name="depth_leres++", path="lllyasviel/control_v11f1p_sd15_depth"))
    session.add(ControlnetModel(name="depth_midas", path="lllyasviel/control_v11f1p_sd15_depth"))
    session.add(ControlnetModel(name="depth_zoe", path="lllyasviel/control_v11f1p_sd15_depth"))
    session.add(ControlnetModel(name="mlsd", path="lllyasviel/control_v11p_sd15_mlsd"))
    session.add(ControlnetModel(name="normal_bae", path="lllyasviel/control_v11p_sd15_normalbae"))
    session.add(ControlnetModel(name="normal_midas", path="lllyasviel/control_v11p_sd15_normalbae"))
    session.add(ControlnetModel(name="scribble_hed", path="lllyasviel/control_v11p_sd15_scribble"))
    session.add(ControlnetModel(name="scribble_pidinet", path="lllyasviel/control_v11p_sd15_scribble"))
    session.add(ControlnetModel(name="segmentation", path="lllyasviel/control_v11p_sd15_seg"))
    session.add(ControlnetModel(name="lineart_coarse", path="lllyasviel/control_v11p_sd15_lineart"))
    session.add(ControlnetModel(name="lineart_realistic", path="lllyasviel/control_v11p_sd15_lineart"))
    session.add(ControlnetModel(name="lineart_anime", path="lllyasviel/control_v11p_sd15s2_lineart_anime"))
    session.add(ControlnetModel(name="openpose", path="lllyasviel/control_v11p_sd15_openpose"))
    session.add(ControlnetModel(name="openpose_face", path="lllyasviel/control_v11p_sd15_openpose"))
    session.add(ControlnetModel(name="openpose_faceonly", path="lllyasviel/control_v11p_sd15_openpose"))
    session.add(ControlnetModel(name="openpose_full", path="lllyasviel/control_v11p_sd15_openpose"))
    session.add(ControlnetModel(name="openpose_hand", path="lllyasviel/control_v11p_sd15_openpose"))
    session.add(ControlnetModel(name="softedge_hed", path="lllyasviel/control_v11p_sd15_softedge"))
    session.add(ControlnetModel(name="softedge_hedsafe", path="lllyasviel/control_v11p_sd15_softedge"))
    session.add(ControlnetModel(name="softedge_pidinet", path="lllyasviel/control_v11p_sd15_softedge"))
    session.add(ControlnetModel(name="softedge_pidsafe", path="lllyasviel/control_v11p_sd15_softedge"))
    session.add(ControlnetModel(name="pixel2pixel", path="lllyasviel/control_v11e_sd15_ip2p"))
    session.add(ControlnetModel(name="inpaint", path="lllyasviel/control_v11p_sd15_inpaint"))
    session.add(ControlnetModel(name="shuffle", path="lllyasviel/control_v11e_sd15_shuffle"))
    
    session.commit()


if not session.query(AIModel).first():
    session.add(AIModel(
        name="Shap-e",
        path="openai/shap-e-img2img",
        branch="fp16",
        version="SD 1.5",
        category="shapegif",
        pipeline_action="img2img",
        enabled=True,
    ))
    session.add(AIModel(
        name="Stable Diffusion 2.1 512",
        path="stabilityai/stable-diffusion-2",
        branch="fp16",
        version="SD 2.1",
        category="stablediffusion",
        pipeline_action="txt2img",
        enabled=True
    ))
    session.add(AIModel(
        name="Stable Diffusion 2.1 768",
        path="stabilityai/stable-diffusion-2-1",
        branch="fp16",
        version="SD 2.1",
        category="stablediffusion",
        pipeline_action="txt2img",
        enabled=True
    ))
    session.add(AIModel(
        name="Stable Diffusion 1.5",
        path="runwayml/stable-diffusion-v1-5",
        branch="fp16",
        version="SD 1.5",
        category="stablediffusion",
        pipeline_action="txt2img",
        enabled=True,
    ))
    session.add(AIModel(
        name="Stable Diffusion XL Base 1.0",
        path="stabilityai/stable-diffusion-xl-base-1.0",
        branch="fp16",
        version="SDXL 1.0",
        category="stablediffusion",
        pipeline_action="txt2img",
        enabled=True,
    ))
    session.add(AIModel(
        name="Kandinsky 2.1",
        path="kandinsky-community/kandinsky-2-1",
        branch="fp16",
        version="K 2.1",
        category="kandinsky",
        pipeline_action="txt2img",
        enabled=True,
    ))
    session.add(AIModel(
        name="Shap-e",
        path="openai/shap-e",
        branch="fp16",
        version="SD 1.5",
        category="shapegif",
        pipeline_action="txt2img",
        enabled=True,
    ))
    session.add(AIModel(
        name="Stable Diffusion Inpaint 2",
        path="stabilityai/stable-diffusion-2-inpainting",
        branch="fp16",
        version="SD 2.1",
        category="stablediffusion",
        pipeline_action="outpaint",
        enabled=True
    ))
    session.add(AIModel(
        name="Stable Diffusion Inpaint 1.5",
        path="runwayml/stable-diffusion-inpainting",
        branch="fp16",
        version="SD 1.5",
        category="stablediffusion",
        pipeline_action="outpaint",
        enabled=True
    ))
    session.add(AIModel(
        name="Kandinsky Inpaint 2.1",
        path="kandinsky-community/kandinsky-2-1-inpaint",
        branch="fp16",
        version="K 2.1",
        category="kandinsky",
        pipeline_action="outpaint",
        enabled=True
    ))
    session.add(AIModel(
        name="Stable Diffusion Depth2Img",
        path="stabilityai/stable-diffusion-2-depth",
        branch="fp16",
        version="SD 2.1",
        category="stablediffusion",
        pipeline_action="depth2img",
        enabled=True
    ))
    session.add(AIModel(
        name="Stable Diffusion 1.5",
        path="runwayml/stable-diffusion-v1-5",
        branch="fp16",
        version="SD 1.5",
        category="stablediffusion",
        pipeline_action="controlnet",
        enabled=True
    ))
    session.add(AIModel(
        name="Stability AI 4x resolution",
        path="stabilityai/stable-diffusion-x4-upscaler",
        branch="fp16",
        version="SD 1.5",
        category="stablediffusion",
        pipeline_action="superresolution",
        enabled=True
    ))
    session.add(AIModel(
        name="Instruct pix2pix",
        path="timbrooks/instruct-pix2pix",
        branch="fp16",
        version="SD 1.5",
        category="stablediffusion",
        pipeline_action="pix2pix",
        enabled=True
    ))
    session.add(AIModel(
        name="SD Image Variations",
        path="lambdalabs/sd-image-variations-diffusers",
        branch="v2.0",
        version="SD 1.5",
        category="stablediffusion",
        pipeline_action="vid2vid",
        enabled=True
    ))
    session.add(AIModel(
        name="sd-x2-latent-upscaler",
        path="stabilityai/sd-x2-latent-upscaler",
        branch="fp16",
        version="SD 1.5",
        category="stablediffusion",
        pipeline_action="upscale",
        enabled=True
    ))
    session.add(AIModel(
        name="CompVis Safety Checker",
        path="CompVis/stable-diffusion-safety-checker",
        branch="fp16",
        version="SD 1.5",
        category="stablediffusion",
        pipeline_action="safety_checker",
        enabled=True
    ))
    session.add(AIModel(
        name="CompVis Safety Checker",
        path="CompVis/stable-diffusion-safety-checker",
        branch="fp16",
        version="SD 1.5",
        category="stablediffusion",
        pipeline_action="safety_checker",
        enabled=True
    ))
    session.add(AIModel(
        name="CompVis Safety Checker",
        path="CompVis/stable-diffusion-safety-checker",
        branch="fp16",
        version="SD 2.1",
        category="stablediffusion",
        pipeline_action="safety_checker",
        enabled=True
    ))
    session.add(AIModel(
        name="OpenAI Text Encoder",
        path="openai/clip-vit-large-patch14",
        branch="fp16",
        version="SD 1.5",
        category="stablediffusion",
        pipeline_action="text_encoder",
        enabled=True
    ))
    session.add(AIModel(
        name="Inpaint vae",
        path="cross-attention/asymmetric-autoencoder-kl-x-1-5",
        branch="fp16",
        version="SD 1.5",
        category="stablediffusion",
        pipeline_action="inpaint_vae",
        enabled=True
    ))
    session.commit()


if not session.query(Pipeline).first():
    session.add(Pipeline(
        pipeline_action="safety_checker",
        version="SD 1.5",
        category="stablediffusion",
        classname="diffusers.pipelines.stable_diffusion.StableDiffusionSafetyChecker",
        default=True
    ))
    session.add(Pipeline(
        pipeline_action="safety_checker",
        version="SD 2.1",
        category="stablediffusion",
        classname="diffusers.pipelines.stable_diffusion.StableDiffusionSafetyChecker",
        default=True
    ))
    session.add(Pipeline(
        pipeline_action="controlnet",
        version="SD 1.5",
        category="stablediffusion",
        classname="diffusers.ControlNetModel",
        default=True
    ))
    session.add(Pipeline(
        pipeline_action="txt2img",
        version="SD 1.5",
        category="stablediffusion",
        classname="diffusers.AutoPipelineForText2Image",
        singlefile_classname="diffusers.StableDiffusionPipeline",
        default=True
    ))
    session.add(Pipeline(
        pipeline_action="txt2img",
        version="SD 1.5",
        category="controlnet",
        classname="diffusers.StableDiffusionControlNetPipeline"
    ))
    session.add(Pipeline(
        pipeline_action="txt2img",
        version="SD 1.5",
        category="shapegif",
        classname="diffusers.DiffusionPipeline"
    ))
    session.add(Pipeline(
        pipeline_action="txt2img",
        version="SDXL 1.0",
        category="stablediffusion",
        classname="diffusers.AutoPipelineForText2Image"
    ))
    session.add(Pipeline(
        pipeline_action="txt2img",
        version="K 2.1",
        category="kandinsky",
        classname="diffusers.KandinskyPipeline"
    ))
    session.add(Pipeline(
        pipeline_action="txt2img",
        version="SD 2.1",
        category="stablediffusion",
        classname="diffusers.AutoPipelineForText2Image"
    ))
    session.add(Pipeline(
        pipeline_action="img2img",
        version="SD 1.5",
        category="stablediffusion",
        classname="diffusers.AutoPipelineForImage2Image",
        singlefile_classname="diffusers.StableDiffusionImg2ImgPipeline",
    ))
    session.add(Pipeline(
        pipeline_action="img2img",
        version="SD 1.5",
        category="controlnet",
        classname="diffusers.StableDiffusionControlNetImg2ImgPipeline",
    ))
    session.add(Pipeline(
        pipeline_action="img2img",
        version="SD 1.5",
        category="shapegif",
        classname="diffusers.DiffusionPipeline",
    ))
    session.add(Pipeline(
        pipeline_action="img2img",
        version="SD 2.1",
        category="stablediffusion",
        classname="diffusers.AutoPipelineForImage2Image",
    ))
    session.add(Pipeline(
        pipeline_action="img2img",
        version="K 2.1",
        category="kandinsky",
        classname="diffusers.KandinskyImg2ImgPipeline",
    ))
    session.add(Pipeline(
        pipeline_action="img2img",
        version="SDXL 1.0",
        category="stablediffusion",
        classname="diffusers.AutoPipelineForImage2Image",
    ))
    session.add(Pipeline(
        pipeline_action="pix2pix",
        version="SD 1.5",
        category="stablediffusion",
        classname="diffusers.StableDiffusionInstructPix2PixPipeline",
    ))
    session.add(Pipeline(
        pipeline_action="outpaint",
        version="SD 1.5",
        category="stablediffusion",
        classname="diffusers.StableDiffusionInpaintPipeline",
        singlefile_classname="diffusers.StableDiffusionInpaintPipeline"
    ))
    session.add(Pipeline(
        pipeline_action="outpaint",
        version="SD 1.5",
        category="conrolnet",
        classname="diffusers.StableDiffusionControlNetInpaintPipeline",
    ))
    session.add(Pipeline(
        pipeline_action="outpaint",
        version="K 2.1",
        category="kandinsky",
        classname="diffusers.KandinskyInpaintPipeline",
    ))
    session.add(Pipeline(
        pipeline_action="outpaint",
        version="SD 2.1",
        category="stablediffusion",
        classname="diffusers.AutoPipelineForInpainting",
    ))
    session.add(Pipeline(
        pipeline_action="inpaint_vae",
        version="SD 1.5",
        category="stablediffusion",
        classname="diffusers.AsymmetricAutoencoderKL",
    ))
    session.add(Pipeline(
        pipeline_action="inpaint_vae",
        version="SD 2.1",
        category="stablediffusion",
        classname="diffusers.AsymmetricAutoencoderKL",
    ))
    session.add(Pipeline(
        pipeline_action="depth2img",
        version="SD 1.5",
        category="stablediffusion",
        classname="diffusers.StableDiffusionDepth2ImgPipeline",
    ))
    session.add(Pipeline(
        pipeline_action="depth2img",
        version="SD 2.1",
        category="stablediffusion",
        classname="diffusers.StableDiffusionDepth2ImgPipeline",
    ))
    session.add(Pipeline(
        pipeline_action="upscale",
        version="SD 1.5",
        category="stablediffusion",
        classname="diffusers.StableDiffusionLatentUpscalePipeline",
    ))
    session.add(Pipeline(
        pipeline_action="latent-upscale",
        version="SD 1.5",
        category="stablediffusion",
        classname="diffusers.StableDiffusionLatentUpscalePipeline",
    ))
    session.add(Pipeline(
        pipeline_action="txt2vid",
        version="SD 1.5",
        category="stablediffusion",
        classname="diffusers.TextToVideoZeroPipeline",
    ))
    session.add(Pipeline(
        pipeline_action="vid2vid",
        version="SD 1.5",
        category="stablediffusion",
        classname="diffusers.StableDiffusionControlNetPipeline",
    ))
    session.add(Pipeline(
        pipeline_action="superresolution",
        version="SD 1.5",
        category="stablediffusion",
        classname="diffusers.StableDiffusionUpscalePipeline",
    ))
    session.add(Pipeline(
        pipeline_action="text_encoder",
        version="SD 1.5",
        category="stablediffusion",
        classname="transformers.CLIPTextModel",
    ))
    session.add(Pipeline(
        pipeline_action="text_encoder",
        version="SD 2.1",
        category="stablediffusion",
        classname="transformers.CLIPTextModel",
    ))
    session.add(Pipeline(
        pipeline_action="text_encoder",
        version="SDXL 1.0",
        category="stablediffusion",
        classname="transformers.CLIPTextModel",
    ))
    session.add(Pipeline(
        pipeline_action="feature_extractor",
        version="SD 1.5",
        category="stablediffusion",
        classname="transformers.AutoFeatureExtractor",
    ))
    session.add(Pipeline(
        pipeline_action="feature_extractor",
        version="SD 2.1",
        category="stablediffusion",
        classname="transformers.AutoFeatureExtractor",
    ))
    session.commit()


if not session.query(PathSettings).first():
    session.add(PathSettings())
    session.commit()


if not session.query(BrushSettings).first():
    session.add(BrushSettings())
    session.commit()


if not session.query(GridSettings).first():
    session.add(GridSettings())
    session.commit()


if not session.query(MetadataSettings).first():
    session.add(MetadataSettings())
    session.commit()


if not session.query(MemorySettings).first():
    session.add(MemorySettings())
    session.commit()


if not session.query(ImageFilter).first():
    bootstrap_data = (
        ("Pixel Art", "pixel_art", "PixelFilter", (
            ("number_of_colors", "24", "int", "2", "1024"),
            ("smoothing", "1", "int"),
            ("base_size", "256", "int", "2", "256"),
        )),
        ("Gaussian Blur", "gaussian_blur", "GaussianBlur", (
            ("radius", "0.0", "float"),
        )),
        ("Box Blur", "box_blur", "BoxBlur", (
            ("radius", "0.0", "float"),
        )),
        ("Color Balance", "color_balance", "ColorBalanceFilter", (
            ("cyan_red", "0.0", "float"),
            ("magenta_green", "0.0", "float"),
            ("yellow_blue", "0.0", "float"),
        )),
        ("Halftone Filter", "halftone", "HalftoneFilter", (
            ("sample", "1", "int"),
            ("scale", "1", "int"),
            ("color_mode", "L", "str"),
        )),
        ("Registration Error", "registration_error", "RegistrationErrorFilter", (
            ("red_offset_x_amount", "3", "int"),
            ("red_offset_y_amount", "3", "int"),
            ("green_offset_x_amount", "6", "int"),
            ("green_offset_y_amount", "6", "int"),
            ("blue_offset_x_amount", "9", "int"),
            ("blue_offset_y_amount", "9", "int")
        )),
        ("Unsharp Mask", "unsharp_mask", "UnsharpMask", (
            ("radius", "0.5", "float"),
            ("percent", "0.5", "float"),
            ("threshold", "0.5", "float"),
        )),
        ("Saturation Filter", "saturation", "SaturationFilter", (
            ("factor", "1.0", "float"),
        )),
        ("RGB Noise Filter", "rgb_noise", "RGBNoiseFilter", (
            ("red", "0.0", "float"),
            ("green", "0.0", "float"),
            ("blue", "0.0", "float")
        )),
    )
    for filter in bootstrap_data:
        image_filter = ImageFilter(
            display_name=filter[0],
            name=filter[1],
            filter_class=filter[2]
        )
        for filter_value in filter[3]:
            image_filter.image_filter_values.append(ImageFilterValue(
                name=filter_value[0],
                value=filter_value[1],
                value_type=filter_value[2],
                min_value=filter_value[3] if len(filter_value) > 3 else None,
                max_value=filter_value[4] if len(filter_value) > 4 else None
            ))
        session.add(image_filter)
        session.commit()

    image_filter = session.query(ImageFilter).filter_by(name='color_balance').first()

    # Access its image_filter_values
    filter_values = image_filter.image_filter_values


if not session.query(Document).first():
    settings = Settings(nsfw_filter=True)
    settings.prompt_generator_settings.append(
        PromptGeneratorSetting(
            name="Prompt A",
            active=True,
            settings_id=settings.id
        )
    )
    settings.prompt_generator_settings.append(
        PromptGeneratorSetting(
            name="Prompt B",
            settings_id=settings.id
        )
    )

    settings.splitter_sizes.append(SplitterSection(
        name="main",
        order=0,
        size=-1
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="main",
        order=1,
        size=-1
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="main",
        order=2,
        size=-1
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="center",
        order=0,
        size=520
    ))
    settings.splitter_sizes.append(SplitterSection(
        name="center",
        order=1,
        size=-1
    ))

    settings.brush_settings = session.query(BrushSettings).first()
    settings.path_settings = session.query(PathSettings).first()
    settings.grid_settings = session.query(GridSettings).first()
    settings.metadata_settings = session.query(MetadataSettings).first()
    settings.memory_settings = session.query(MemorySettings).first()

    sections = {
        "stablediffusion": ["txt2img", "outpaint", "depth2img", "pix2pix", "upscale", "supersample", "txt2vid"],
        "kandinsky": ["txt2img", "outpaint"],
        "shapegif": ["txt2img"],
    }
    for section in sections:
        for generator_name in sections[section]:
            settings.generator_settings.append(GeneratorSetting(
                section=section,
                generator_name=generator_name
            ))

    session.add(Document(
        name="Untitled",
        settings=settings
    ))
    session.commit()
