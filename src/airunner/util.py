import pdb


def get_model_url_from_path(data):
    action = data["action"]
    model_path = data["options"][f"{action}_model_path"]
    model_path = "/".join(model_path.split("/")[-2:])
    huggingface_model_name = model_path.lstrip("/")
    return f"https://huggingface.co/{huggingface_model_name}"


def min_max(value, min_val, max_val):
    return max(min(value, max_val), min_val)


def debug(prnt=None):
    if prnt:
        print(prnt)
    pdb.set_trace()