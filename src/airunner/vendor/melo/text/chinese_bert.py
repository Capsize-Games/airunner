import torch
import sys
from transformers import AutoTokenizer, AutoModelForMaskedLM

from airunner.api import API

tokenizers = {}
models = {}


def get_bert_feature(text, word2ph, device=None, model_id=None):
    model_id = model_id or "hfl/chinese-roberta-wwm-ext-large"
    model_id = API().paths[model_id]
    if model_id not in models:
        models[model_id] = AutoModelForMaskedLM.from_pretrained(model_id).to(
            device
        )
        tokenizers[model_id] = AutoTokenizer.from_pretrained(model_id)
    model = models[model_id]
    tokenizer = tokenizers[model_id]

    if (
        sys.platform == "darwin"
        and torch.backends.mps.is_available()
        and device == "cpu"
    ):
        device = "mps"
    if not device:
        device = "cuda"

    with torch.no_grad():
        inputs = tokenizer(text, return_tensors="pt")
        for i in inputs:
            inputs[i] = inputs[i].to(device)
        res = model(**inputs, output_hidden_states=True)
        res = torch.cat(res["hidden_states"][-3:-2], -1)[0].cpu()
    word2phone = word2ph
    phone_level_feature = []
    for i in range(len(word2phone)):
        repeat_feature = res[i].repeat(word2phone[i], 1)
        phone_level_feature.append(repeat_feature)

    phone_level_feature = torch.cat(phone_level_feature, dim=0)
    return phone_level_feature.T
