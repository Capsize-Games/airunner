import os
import imageio
import numpy as np
from PIL import Image
from aihandler.logger import logger


class TexttovideoMixin:
    @property
    def video_path(self):
        path = os.path.join(self.model_base_path, "videos")
        video_path = self.settings_manager.settings.video_path.get()
        if video_path and video_path != "":
            path = video_path
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    @property
    def txt2vid_file(self):
        return os.path.join(self.video_path, f"{self.prompt}_{self.seed}.mp4")

    def enhance_video(self, video_frames):
        """
        Iterate over each video frame and call img2img on it using the same options that were passed
        and replace each frame with the enhanced version.
        :param video_frames: list of numpy arrays
        :return: video_frames: list of numpy arrays
        """
        new_video_frames = []
        for img in video_frames:
            pil_image = Image.fromarray(img)
            pil_image = pil_image.resize((self.width, self.height), Image.LANCZOS)
            image, nsfw_detected = self.generator_sample({
                "action": "img2img",
                "options": {
                    "image": pil_image,
                    "mask": pil_image,
                    "img2img_prompt": self.prompt,
                    "img2img_negative_prompt": self.negative_prompt,
                    "img2img_steps": self.steps,
                    "img2img_ddim_eta": self.ddim_eta,
                    "img2img_n_iter": 1,
                    "img2img_width": self.width,
                    "img2img_height": self.height,
                    "img2img_n_samples": 20,
                    "img2img_strength": 0.5,
                    "img2img_scale": 7.5,
                    "img2img_seed": self.seed,
                    "img2img_model": "Stable diffusion V2",
                    "img2img_scheduler": self.scheduler_name,
                    "img2img_model_path": "stabilityai/stable-diffusion-2-1-base",
                    "img2img_model_branch": "fp16",
                    "width": self.width,
                    "height": self.height,
                    "do_nsfw_filter": self.do_nsfw_filter,
                    "model_base_path": self.model_base_path,
                    "pos_x": self.pos_x,
                    "pos_y": self.pos_y,
                    "outpaint_box_rect": self.outpaint_box_rect,
                    "hf_token": self.hf_token,
                    "enable_model_cpu_offload": self.enable_model_cpu_offload,
                    "use_attention_slicing": self.use_attention_slicing,
                    "use_tf32": self.use_tf32,
                    "use_enable_vae_slicing": self.use_enable_vae_slicing,
                    "use_accelerated_transformers": self.use_accelerated_transformers,
                    "use_torch_compile": self.use_torch_compile,
                    "use_tiled_vae": self.use_tiled_vae,
                }
            }, image_var=None, use_callback=False)
            if image:
                # convert to numpy array and add to new_video_frames
                new_video_frames.append(np.array(image))
        return new_video_frames if len(new_video_frames) > 0 else video_frames

    def handle_zeroshot_output(self, output):
        if self.enable_controlnet:
            result = output["frames"]
        else:
            result = np.concatenate(output["frames"])
            result = [(r * 255).astype("uint8") for r in result]
        logger.info(f"Saving video to {self.txt2vid_file}")
        imageio.mimsave(self.txt2vid_file, result, format="FFMPEG", codec="libx264")

        #print type of result
        print(type(result[0]))
        print(result[0])
        logger.info(f"Save complete")
        pil_image = Image.fromarray(result[0])
        return pil_image, None

    def handle_txt2vid_output(self, output):
        pil_image = None
        if output:
            from diffusers.utils import export_to_video
            video_frames = output.frames
            os.makedirs(os.path.dirname(self.txt2vid_file), exist_ok=True)
            #self.enhance_video(video_frames)
            export_to_video(video_frames, self.txt2vid_file)
            pil_image = Image.fromarray(video_frames[0])
        else:
            print("failed to get output from txt2vid")
        return pil_image, None