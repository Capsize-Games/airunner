import os
import argparse
import logging
import json
import numpy as np
from scipy.io.wavfile import read
import torch
import librosa

logger = logging.getLogger(__name__)


def summarize(
    writer,
    global_step,
    scalars={},
    histograms={},
    images={},
    audios={},
    audio_sampling_rate=22050,
):
    for k, v in scalars.items():
        writer.add_scalar(k, v, global_step)
    for k, v in histograms.items():
        writer.add_histogram(k, v, global_step)
    for k, v in images.items():
        writer.add_image(k, v, global_step, dataformats="HWC")
    for k, v in audios.items():
        writer.add_audio(k, v, global_step, audio_sampling_rate)


def load_wav_to_torch(full_path):
    sampling_rate, data = read(full_path)
    return torch.FloatTensor(data.astype(np.float32)), sampling_rate


def load_wav_to_torch_librosa(full_path, sr):
    audio_norm, sampling_rate = librosa.load(full_path, sr=sr, mono=True)
    return torch.FloatTensor(audio_norm.astype(np.float32)), sampling_rate


def load_filepaths_and_text(filename, split="|"):
    with open(filename, encoding="utf-8") as f:
        filepaths_and_text = [line.strip().split(split) for line in f]
    return filepaths_and_text


def get_hparams(init=True):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="./configs/base.json",
        help="JSON file for configuration",
    )
    parser.add_argument("--local_rank", type=int, default=0)
    parser.add_argument("--world-size", type=int, default=1)
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument(
        "-m", "--model", type=str, required=True, help="Model name"
    )
    parser.add_argument(
        "--pretrain_G", type=str, default=None, help="pretrain model"
    )
    parser.add_argument(
        "--pretrain_D", type=str, default=None, help="pretrain model D"
    )
    parser.add_argument(
        "--pretrain_dur",
        type=str,
        default=None,
        help="pretrain model duration",
    )

    args = parser.parse_args()
    model_dir = os.path.join("./logs", args.model)

    os.makedirs(model_dir, exist_ok=True)

    config_path = args.config
    config_save_path = os.path.join(model_dir, "config.json")
    if init:
        with open(config_path, "r") as f:
            data = f.read()
        with open(config_save_path, "w") as f:
            f.write(data)
    else:
        with open(config_save_path, "r") as f:
            data = f.read()
    config = json.loads(data)

    hparams = HParams(**config)
    hparams.model_dir = model_dir
    hparams.pretrain_G = args.pretrain_G
    hparams.pretrain_D = args.pretrain_D
    hparams.pretrain_dur = args.pretrain_dur
    hparams.port = args.port
    return hparams


def get_hparams_from_file(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        data = f.read()
    config = json.loads(data)

    hparams = HParams(**config)
    return hparams


def get_logger(model_dir, filename="train.log"):
    global logger
    logger = logging.getLogger(os.path.basename(model_dir))
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s"
    )
    if not os.path.exists(model_dir):
        os.makedirs(model_dir, exist_ok=True)
    h = logging.FileHandler(os.path.join(model_dir, filename))
    h.setLevel(logging.DEBUG)
    h.setFormatter(formatter)
    logger.addHandler(h)
    return logger


class HParams:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if type(v) == dict:
                v = HParams(**v)
            self[k] = v

    def keys(self):
        return self.__dict__.keys()

    def items(self):
        return self.__dict__.items()

    def values(self):
        return self.__dict__.values()

    def __len__(self):
        return len(self.__dict__)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    def __contains__(self, key):
        return key in self.__dict__

    def __repr__(self):
        return self.__dict__.__repr__()
