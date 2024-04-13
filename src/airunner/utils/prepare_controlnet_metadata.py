def prepare_controlnet_metadata(data):
    from PIL import PngImagePlugin
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("controlnet", str(data["controlnet"]))

