import os
import torch
from airunner.vendor.melo import utils
from cached_path import cached_path
from huggingface_hub import hf_hub_download
from airunner.api import API

DOWNLOAD_CKPT_URLS = {
    "EN": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/EN/checkpoint.pth",
    "EN_V2": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/EN_V2/checkpoint.pth",
    "FR": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/FR/checkpoint.pth",
    "JP": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/JP/checkpoint.pth",
    "ES": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/ES/checkpoint.pth",
    "ZH": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/ZH/checkpoint.pth",
    "KR": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/KR/checkpoint.pth",
}

DOWNLOAD_CONFIG_URLS = {
    "EN": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/EN/config.json",
    "EN_V2": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/EN_V2/config.json",
    "FR": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/FR/config.json",
    "JP": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/JP/config.json",
    "ES": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/ES/config.json",
    "ZH": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/ZH/config.json",
    "KR": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/KR/config.json",
}

PRETRAINED_MODELS = {
    "G.pth": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/pretrained/G.pth",
    "D.pth": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/pretrained/D.pth",
    "DUR.pth": "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/basespeakers/pretrained/DUR.pth",
}

LANG_TO_HF_REPO_ID = {
    "EN": API().paths["myshell-ai/MeloTTS-English"],
    # "EN_V2": API().paths["myshell-ai/MeloTTS-English-v2"],
    "EN_NEWEST": API().paths["myshell-ai/MeloTTS-English-v3"],
    "FR": API().paths["myshell-ai/MeloTTS-French"],
    "JP": API().paths["myshell-ai/MeloTTS-Japanese"],
    "ES": API().paths["myshell-ai/MeloTTS-Spanish"],
    "ZH": API().paths["myshell-ai/MeloTTS-Chinese"],
    "KR": API().paths["myshell-ai/MeloTTS-Korean"],
}


def load_or_download_config(locale, use_hf=True, config_path=None):
    if config_path is None:
        language = locale.split("-")[0].upper()
        config_path = os.path.join(
            LANG_TO_HF_REPO_ID.get(language, None), "config.json"
        )
    return utils.get_hparams_from_file(config_path)


def load_or_download_model(locale, device, use_hf=True, ckpt_path=None):
    if ckpt_path is None:
        language = locale.split("-")[0].upper()
        ckpt_path = os.path.join(
            LANG_TO_HF_REPO_ID.get(language, None), "checkpoint.pth"
        )
    return torch.load(ckpt_path, map_location=device)


def load_pretrain_model():
    return [cached_path(url) for url in PRETRAINED_MODELS.values()]
