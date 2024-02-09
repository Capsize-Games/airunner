import os
import imageio
import numpy as np
from PIL import Image


class TexttovideoMixin:
    @property
    def video_path(self):
        path = os.path.join(self.model_base_path, "videos")
        video_path = self.video_path
        if video_path and video_path != "":
            path = video_path
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    @property
    def txt2vid_file(self):
        return os.path.join(self.video_path, f"{self.prompt}_{self.latents_seed}.mp4")

    def handle_txt2vid_output(self, output):
        output_image = None
        if output is None:
            self.logger.error("txt2vid output is None")
        else:
            if self.enable_controlnet:
                result = output["frames"]
            else:
                result = np.concatenate(output["frames"])
                result = [(r * 255).astype("uint8") for r in result]

            if len(result) > 0:
                self.logger.info(f"Saving video to {self.txt2vid_file}")
                filename = self.txt2vid_file
                index = 1
                while os.path.exists(filename):
                    filename = self.txt2vid_file.replace(".mp4", f"_{index}.mp4")
                    index += 1
                imageio.mimsave(filename, result, format="FFMPEG", codec="libx264")
                self.logger.info(f"Save complete")
                output_image = Image.fromarray(result[0])
            else:
                self.logger.error("No frames in txt2vid output")

        return output_image, None