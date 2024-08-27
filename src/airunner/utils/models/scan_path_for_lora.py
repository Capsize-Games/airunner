import os

from airunner.settings import BASE_PATH


def scan_path_for_lora(current_lora):
    for versionpath, versionnames, versionfiles in os.walk(os.path.expanduser(os.path.join(BASE_PATH, "art/models"))):
        version = versionpath.split("/")[-1]
        lora_path = os.path.expanduser(
            os.path.join(
                BASE_PATH,
                "art/models",
                version,
                "lora"
            )
        )
        for dirpath, dirnames, filenames in os.walk(lora_path):
            for file in filenames:
                if file.endswith(".ckpt") or file.endswith(".safetensors") or file.endswith(".pt"):
                    name = file.replace(".ckpt", "").replace(".safetensors", "").replace(".pt", "")
                    path = os.path.join(dirpath, file)
                    if version not in current_lora:
                        current_lora[version] = []
                    add_lora = True
                    for lora in current_lora[version]:
                        if lora["name"] == name and lora["path"] == str(path):
                            add_lora = False
                            break
                    if add_lora:
                        lora_data = dict(
                            name=name,
                            path=path,
                            scale=1,
                            enabled=True,
                            loaded=False,
                            trigger_word="",
                            version=version
                        )
                        current_lora[version].append(lora_data)
    return current_lora
