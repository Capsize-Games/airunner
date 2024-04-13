from PIL import PngImagePlugin


def prepare_metadata(data, index=0):
    metadata = PngImagePlugin.PngInfo()
    options = data.get("options", {})
    action = data.get("action", "txt2img")
    metadata.add_text("action", action)

    prompt = options.get("prompt", "")
    if type(prompt) == list:
        prompt = prompt[index]
    metadata.add_text("prompt", prompt)

    negative_prompt = options.get("negative_prompt", "")
    if type(negative_prompt) == list:
        negative_prompt = negative_prompt[index]
    metadata.add_text("negative_prompt", negative_prompt)

    metadata.add_text("strength", str(options.get("strength", 100)))
    metadata.add_text("scale", str(options.get("scale", 7)))
    metadata.add_text("seed", str(options.get("seed", 0)))
    metadata.add_text("steps", str(options.get("steps", 20)))
    metadata.add_text("ddim_eta", str(options.get("ddim_eta", 0.0001)))
    metadata.add_text("n_iter", str(options.get("n_iter", 1)))
    metadata.add_text("n_samples", str(options.get("n_samples", 1)))
    metadata.add_text("clip_skip", str(options.get("clip_skip", 0)))
    if action == "txt2img":
        for k, v in options.get("model_data", {}).items():
            metadata.add_text(f"model_data_{k}", str(v))
    else:
        for k, v in options.get("model_data", {}).items():
            metadata.add_text(f"{action}_model_data_{k}", str(v))
        for k, v in options.get("original_model_data", {}).items():
            metadata.add_text(f"model_data_{k}", str(v))
    metadata.add_text("action", "txt2img")
    metadata.add_text("scheduler", str(options.get("scheduler", "DPM++ 2M Karras")))

    return metadata

