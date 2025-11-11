from airunner.settings import AIRUNNER_ART_ENABLED


controlnet_bootstrap_data = [
    {
        "display_name": "Canny",
        "name": "canny",
        "path": "diffusers/controlnet-canny-sdxl-1.0",
        "version": "SDXL 1.0",
        "pipeline_action": "controlnet",
        "size": "320200",
    },
    {
        "display_name": "Depth Midas",
        "name": "depth_midas",
        "path": "diffusers/controlnet-depth-sdxl-1.0",
        "version": "SDXL 1.0",
        "pipeline_action": "controlnet",
        "size": "320200",
    },
]


if not AIRUNNER_ART_ENABLED:
    controlnet_bootstrap_data = []
