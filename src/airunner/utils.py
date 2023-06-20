import os
import platform
import torch
from diffusers import StableDiffusionPipeline, StableDiffusionInpaintPipeline

from aihandler.settings import MODELS


def resize_image_to_working_size(image, settings):
    # get size of image
    width, height = image.size
    working_width = settings.working_width.get()
    working_height = settings.working_height.get()

    # get the aspect ratio of the image
    aspect_ratio = width / height

    # choose to resize based on width or height, for example if
    # working size is 100x50 and the image is 100x200, we want to
    # resize the image to 25x50 so that it fits in the working size.
    # if the image is 200x100, we want to resize it to 100x50.
    if working_width / working_height > aspect_ratio:
        # resize based on height
        new_width = int(working_height * aspect_ratio)
        new_height = working_height
    else:
        # resize based on width
        new_width = working_width
        new_height = int(working_width / aspect_ratio)

    return image.resize((new_width, new_height))


class InpaintMerged:
    """
    This is the same thing as run_modelmerger, but it is a class that can be extended.
    It does not save to disc, rather it uses DiffusionPipeline to load, combine and use the models.
    We also have the ability to combine any number of models, not just three
    """
    def __init__(self, base_model: StableDiffusionInpaintPipeline, pipelines: [StableDiffusionPipeline]):
        self.base_model = base_model
        self.pipelines = pipelines
        self.combined_model = self.sum_weights()

    def average_sum(self, values):
        # combine all the values and average them
        return sum(values) / len(values)

    def sum_weights(self):
        inpaint_state_dict = self.base_model.unet.state_dict()
        state_dicts = [
            pipeline.unet.state_dict() for pipeline in self.pipelines
        ]
        skip_key = "cond_stage_model.transformer.text_model.embeddings.position_ids"
        state_dict = state_dicts.pop(0)
        for key in state_dict.keys():
            if key.contains(skip_key):
                continue
            if key.contains("model"):
                value_sums = {}
                for state_dict2 in state_dicts:
                    value_sums[key] = []
                    if key in state_dict2:
                        value_sums[key].append(state_dict2[key])
                    else:
                        value_sums[key].append(torch.zeros_like(state_dict[key]))
                state_dict[key] = self.average_sum(value_sums[key])

        primary_model_state_dict = self.base_model.unet.state_dict()
        for key in primary_model_state_dict.keys():
            if key.contains(skip_key):
                continue

            a = primary_model_state_dict[key]
            b = state_dict[key]

            if a.shape != b.shape and a.shape[0:1] + a.shape[2:] == b.shape[0:1] + b.shape[2:]:
                if a.shape[1] == 8 and b.shape[1] == 4:
                    # pix2pix
                    primary_model_state_dict[key][:, 0:4, :, :] = self.average_sum([a[:, 0:4, :, :], b])
                else:
                    # inpainting
                    primary_model_state_dict[key][:, 0:4, :, :] = self.average_sum([a[:, 0:4, :, :], b])
            else:
                primary_model_state_dict[key].half()


        self.base_model.unet.load_state_dict(primary_model_state_dict)
        return self.base_model


def get_version():
    version = None

    try:
        with open("./VERSION", "r") as f:
            version = f.read()
    except Exception as e:
        pass

    if not version:
        try:
            # attempt to get from setup.py file in current directory (works for compiled python only)
            with open("./setup.py", "r") as f:
                version = f.read().strip()
                version = version.split("version=")[1].split(",")[0]
        except Exception as e:
            pass

    if not version:
        # attempt to get from parent directory (works for uncompiled python only)
        try:
            with open("../../setup.py", "r") as f:
                version = f.read().strip()
                version = version.split("version=")[1].split(",")[0]
        except Exception as e:
            pass
    if version:
        # remove anything other than numbers and dots
        version = "".join([c for c in version if c in "0123456789."])
        return version
    return ""


def get_latest_version():
    # get latest release from https://github.com/Capsize-Games/airunner/releases/latest
    # follow the redirect to get the version number
    import requests
    import re
    url = "https://github.com/Capsize-Games/airunner/releases/latest"
    r = requests.get(url)
    if r.status_code == 200:
        m = re.search(r"\/Capsize-Games\/airunner\/releases\/tag\/v([0-9\.]+)", r.text)
        if m:
            return m.group(1)
    return None


def load_default_models(tab_section, section_name):
    if section_name == "txt2img":
        section_name = "generate"
    section_name = f"{tab_section}_{section_name}"
    return [
        k for k in MODELS[section_name].keys()
    ]


def load_models_from_path(path, models = None):
    if models is None:
        models = []
    if os.path.exists(path):
        for f in os.listdir(path):
            if os.path.isdir(os.path.join(path, f)):
                folders_in_directory = os.listdir(os.path.join(path, f))
                is_diffusers = True
                for req_folder in ["scheduler", "text_encoder", "tokenizer", "unet", "vae"]:
                    if req_folder not in folders_in_directory:
                        is_diffusers = False
                        break
                if is_diffusers:
                    models.append(f)
                else:
                    models = load_models_from_path(os.path.join(path, f), models)
            elif f.endswith(".pt") or f.endswith(".safetensors") or f.endswith(".ckpt"):
                models.append(f)
    # sort models by name
    models.sort()
    return models
