import datetime
import os
import threading
import torch
from PIL import Image
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import QFileDialog, QApplication, QMainWindow
from airunner.aihandler.logger import Logger
from airunner.settings import SQLITE_DB_PATH
from PIL import PngImagePlugin
from airunner.data.session_scope import session_scope

SESSION = None


def get_venv_python_executable():
    """
    Gets the python executable from the venv.
    :return: executable path
    """
    venv_python_executable = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "venv",
        "../../bin",
        "python",
    )
    if not os.path.exists(venv_python_executable):
        venv_python_executable = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "venv",
            "Scripts",
            "python.exe",
        )
    if not os.path.exists(venv_python_executable):
        venv_python_executable = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "venv",
            "../../bin",
            "python3",
        )
    if not os.path.exists(venv_python_executable):
        venv_python_executable = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "venv",
            "Scripts",
            "python3.exe",
        )
    if not os.path.exists(venv_python_executable):
        raise Exception("Could not find python executable in venv")
    return venv_python_executable


def initialize_os_environment():
    from airunner.data.managers import SettingsManager
    settings_manager = SettingsManager()
    hf_cache_path = settings_manager.path_settings.hf_cache_path
    if hf_cache_path != "":
        # check if hf_cache_path exists
        if os.path.exists(hf_cache_path):
            os.unsetenv("HUGGINGFACE_HUB_CACHE")
            os.environ["HUGGINGFACE_HUB_CACHE"] = hf_cache_path


def default_hf_cache_dir():
    default_home = os.path.join(os.path.expanduser("~"), ".cache")
    hf_cache_home = os.path.expanduser(
        os.getenv(
            "HF_HOME",
            os.path.join(os.getenv("XDG_CACHE_HOME", default_home), "huggingface"),
        )
    )
    default_cache_path = os.path.join(hf_cache_home, "hub")
    HUGGINGFACE_HUB_CACHE = os.getenv("HUGGINGFACE_HUB_CACHE", default_cache_path)
    return HUGGINGFACE_HUB_CACHE


def image_to_pixmap(image: Image, size=None):
    """
    Converts a PIL image to a QPixmap.
    :param image:
    :return:
    """
    image_width = image.width
    image_height = image.height

    # scaale the image to the new width and height preserving the aspect ratio
    if size is not None:
        if image_width > 0 and image_height > 0:
            aspect_ratio = image_width / image_height
            if image_width > image_height:
                image_width = size
                image_height = int(image_width / aspect_ratio)
            else:
                image_height = size
                image_width = int(image_height * aspect_ratio)
    image_copy = image.copy()
    image_copy = image_copy.resize((image_width, image_height))
    new_image = Image.new("RGB", (size, size))
    new_image.paste(image_copy, (int((size - image_width) / 2), int((size - image_height) / 2)))
    return QPixmap.fromImage(
        QImage(
            new_image.tobytes("raw", "RGB"), size, size, QImage.Format.Format_RGB888
        )
    )


def resize_image_to_working_size(image, settings):
    # get size of image
    width, height = image.size
    working_width = settings.working_width
    working_height = settings.working_height

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
    from diffusers import StableDiffusionPipeline, StableDiffusionInpaintPipeline

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


# def load_default_models(tab_section, section_name):
#     if section_name == "txt2img":
#         section_name = "generate"
#     section_name = f"{tab_section}_{section_name}"
#     return [
#         k for k in models[section_name].keys()
#     ]
#
#
# def load_models_from_path(path, models = None):
#     if models is None:
#         models = []
#     if path and os.path.exists(path):
#         for f in os.listdir(path):
#             if os.path.isdir(os.path.join(path, f)):
#                 folders_in_directory = os.listdir(os.path.join(path, f))
#                 is_diffusers = True
#                 for req_folder in ["scheduler", "text_encoder", "tokenizer", "unet", "vae"]:
#                     if req_folder not in folders_in_directory:
#                         is_diffusers = False
#                         break
#                 if is_diffusers:
#                     models.append(f)
#                 else:
#                     models = load_models_from_path(os.path.join(path, f), models)
#             elif f.endswith(".pt") or f.endswith(".safetensors") or f.endswith(".ckpt"):
#                 models.append(f)
#     # sort models by name
#     models.sort()
#     return models

def prepare_metadata(data, index=0):
    from airunner.data.managers import SettingsManager
    settings_manager = SettingsManager()
    if not settings_manager.metadata_settings.export_metadata or \
            settings_manager.settings.image_export_type != "png":
        return None
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
    metadata.add_text("image_guidance_scale", str(options.get("image_guidance_scale", 100)))
    metadata.add_text("scale", str(options.get("scale", 7)))
    metadata.add_text("seed", str(options.get("seed", 0)))
    metadata.add_text("latents_seed", str(options.get("latents_seed", 0)))
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

def prepare_controlnet_metadata(data):
    from airunner.data.managers import SettingsManager
    from PIL import PngImagePlugin
    settings_manager = SettingsManager()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("controlnet", str(data["controlnet"]))

def auto_export_image(
    image,
    data=None,
    seed=None,
    latents_seed=None,
    type="image",
):
    from airunner.data.managers import SettingsManager

    if seed is None:
        raise Exception("Seed must be set when auto exporting an image")
    
    if latents_seed is None:
        raise Exception("Latents seed must be set when auto exporting an image")

    data["options"]["seed"] = seed
    data["options"]["latents_seed"] = latents_seed
    
    settings_manager = SettingsManager()
    
    if data and "action" in data and data["action"] == "txt2vid":
        return None, None
    
    base_path = settings_manager.path_settings.model_base_path
    
    if type == "image":
        image_path = settings_manager.path_settings.image_path
        image_path = "images" if image_path == "" else image_path
    elif type == "controlnet":
        image_path = os.path.join(settings_manager.path_settings.image_path, "controlnet_masks")
    
    path = os.path.join(base_path, image_path) if image_path == "images" else image_path
    if not os.path.exists(path):
        os.makedirs(path)
    
    extension = settings_manager.settings.image_export_type
    if extension == "":
        extension = "png"
    extension = f".{extension}"
    
    filename = "image"
    if data:
        if type == "image":
            filename = data["action"]
        elif type == "controlnet":
            filename = f"mask_{data['controlnet']}"
    
    filename = f"{filename}_{str(seed)}_{str(latents_seed)}"
    if os.path.exists(os.path.join(path, filename + extension)):
        i = 1
        while os.path.exists(os.path.join(path, filename + "_" + str(i) + extension)):
            i += 1
        filename = filename + "_" + str(i)
    
    if data:
        if type == "image":
            metadata = prepare_metadata(data)
        elif type == "controlnet":
            metadata = prepare_controlnet_metadata(data)
    else:
        metadata = None

    if image:
        action = data["action"] if data and "action" in data else ""

        # date is year-month-day
        date = datetime.datetime.now().strftime("%Y-%m-%d")

        file_path = os.path.join(path, action, date)

        # if path doesn't exist, create it
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))
        
        # if image already exists, add a number to the end of the filename
        i = 1
        while os.path.exists(os.path.join(path, action, date, filename + "_" + str(i) + extension)):
            i += 1
        filename = filename + "_" + str(i) + extension
        file_path = os.path.join(path, action, date, filename)

        # ensure file_path exists:
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        if metadata:
            image.save(file_path, pnginfo=metadata)
        else:
            image.save(file_path)
        return file_path, image
    return None, None

def load_metadata_from_image(image):
    if image:
        return image.info
    return {}

def open_file_path(label="Import Image", directory="", file_type="Image Files (*.png *.jpg *.jpeg)"):
    return QFileDialog.getOpenFileName(
        None, label, directory, file_type
    )


def get_main_window():
    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            return widget


def create_airunner_paths():
    from airunner.data.models import PathSettings
    import os
    with session_scope() as session:
        path_settings = session.query(PathSettings).first()
        if path_settings:
            paths = [
                path_settings.base_path,
                path_settings.txt2img_model_path,
                path_settings.depth2img_model_path,
                path_settings.pix2pix_model_path,
                path_settings.outpaint_model_path,
                path_settings.upscale_model_path,
                path_settings.txt2vid_model_path,
                path_settings.embeddings_path,
                path_settings.lora_path,
                path_settings.image_path,
                path_settings.video_path
            ]
            for index, path in enumerate(paths):
                if not os.path.exists(path):
                    print("cerating path", index, path)
                    os.makedirs(path)


def apply_opacity_to_image(image, target_opacity):
    if not image:
        return image
    target_opacity = 255 * target_opacity
    if target_opacity == 0:
        target_opacity = 1
    image = image.convert("RGBA")
    r, g, b, a = image.split()
    a = a.point(lambda i: target_opacity if i > 0 else 0)
    image.putalpha(a)
    return image


lock = threading.Lock()

def delete_image(path):
    with lock:
        if os.path.exists(path):
            os.remove(path)


import os
import sys
import subprocess
import tempfile
import urllib.request

def install_library_from_url(url, install_dir):
    # Download the wheel file
    wheel_file = urllib.request.urlretrieve(url)[0]
    # Install the library
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--target", install_dir, wheel_file])

def load_extension(extension_dir):
    # Create a subdirectory for the installed libraries
    install_dir = os.path.join(extension_dir, "libs")
    os.makedirs(install_dir, exist_ok=True)

    # Read the dependencies file
    with open(os.path.join(extension_dir, "dependencies.txt")) as f:
        dependencies = f.read().splitlines()

    # Install the dependencies
    for url in dependencies:
        install_library_from_url(url, install_dir)

    # Add the directory to sys.path
    sys.path.append(install_dir)

    # Now you can import any library that was in the extension's dependencies