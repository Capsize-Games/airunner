from airunner.settings import AIRUNNER_ART_ENABLED


controlnet_bootstrap_data = [
]


if not AIRUNNER_ART_ENABLED:
    controlnet_bootstrap_data = []
