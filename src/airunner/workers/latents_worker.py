import numpy as np
from PIL import Image
from airunner.enums import (
    SignalCode,
    SDMode,
)
from airunner.workers.worker import Worker
SKIP_RELOAD_CONSTS = (
    SDMode.FAST_GENERATE,
    SDMode.DRAWING,
)


class LatentsWorker(Worker):
    def __init__(self):
        super().__init__()
        self.register(SignalCode.HANDLE_LATENTS_SIGNAL, self.on_handle_latents_signal)

    def on_handle_latents_signal(self, data: dict):
        latents = data.get("latents")
        sd_request = data.get("sd_request")
        # convert latents to PIL image
        latents = latents[0].detach().cpu().numpy().astype(np.uint8)  # convert to uint8
        latents = latents.transpose(1, 2, 0)
        image = Image.fromarray(latents)
        image = image.resize((self.application_settings.working_width, self.application_settings.working_height))
        image = image.convert("RGBA")
        self.emit_signal(
            SignalCode.SD_IMAGE_GENERATED_SIGNAL,
            {
                "images": [image],
                "action": sd_request.section,
                "outpaint_box_rect": sd_request.active_rect,
            }
        )
        self.sd_request = None
