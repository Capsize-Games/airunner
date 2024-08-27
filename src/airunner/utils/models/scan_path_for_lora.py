import os

from airunner.settings import BASE_PATH


def scan_path_for_lora(current_lora):
    lora_files = {}
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
                    if version not in lora_files:
                        lora_files[version] = []
                        lora_files[version].append((dirpath, file, version))

            # for dirpath, file, version in lora_files:
                name = file.replace(".ckpt", "").replace(".safetensors", "").replace(".pt", "")
                path = os.path.join(dirpath, file)
                if type(current_lora) is not dict:
                    current_lora = {}
                if version not in current_lora:
                    current_lora[version] = []
                if any((lora["name"] == name and lora["path"] == str(path)) for lora in current_lora[version]):
                    continue
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
