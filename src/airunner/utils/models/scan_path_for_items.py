import os

from airunner.data.models import Lora, Embedding


def scan_path_for_lora(base_path) -> bool:
    lora_added = False
    lora_deleted = False

    for versionpath, versionnames, versionfiles in os.walk(
        os.path.expanduser(os.path.join(base_path, "art/models"))
    ):
        version = versionpath.split("/")[-1]
        lora_path = os.path.expanduser(
            os.path.join(base_path, "art/models", version, "lora")
        )
        if not os.path.exists(lora_path):
            continue

        existing_lora = Lora.objects.all()
        for lora in existing_lora:
            if not os.path.exists(lora.path):
                Lora.objects.delete(lora.id)
                lora_deleted = True
        for dirpath, dirnames, filenames in os.walk(lora_path):
            for file in filenames:
                if (
                    file.endswith(".ckpt")
                    or file.endswith(".safetensors")
                    or file.endswith(".pt")
                ):
                    name = (
                        file.replace(".ckpt", "")
                        .replace(".safetensors", "")
                        .replace(".pt", "")
                    )
                    path = os.path.join(dirpath, file)
                    item = Lora.objects.filter_first(Lora.name == name)
                    if (
                        not item
                        or item.path != path
                        or item.version != version
                    ):
                        item = Lora.objects.create(
                            name=name,
                            path=path,
                            scale=1,
                            enabled=False,
                            loaded=False,
                            trigger_word="",
                            version=version,
                        )
                        lora_added = True
    return lora_deleted or lora_added


def scan_path_for_embeddings(base_path) -> bool:
    embedding_added = False
    embedding_deleted = False
    for versionpath, versionnames, versionfiles in os.walk(
        os.path.expanduser(os.path.join(base_path, "art/models"))
    ):
        version = versionpath.split("/")[-1]
        embedding_path = os.path.expanduser(
            os.path.join(base_path, "art/models", version, "embeddings")
        )
        if not os.path.exists(embedding_path):
            continue
        existing_embeddings = Embedding.objects.all()
        for embedding in existing_embeddings:
            if not os.path.exists(embedding.path):
                Embedding.objects.delete(embedding.id)
                embedding_deleted = True
        for dirpath, dirnames, filenames in os.walk(embedding_path):
            for file in filenames:
                if (
                    file.endswith(".ckpt")
                    or file.endswith(".safetensors")
                    or file.endswith(".pt")
                ):
                    name = (
                        file.replace(".ckpt", "")
                        .replace(".safetensors", "")
                        .replace(".pt", "")
                    )
                    path = os.path.join(dirpath, file)
                    item = Embedding.objects.filter_first(
                        Embedding.name == name
                    )
                    if (
                        not item
                        or item.path != path
                        or item.version != version
                    ):
                        item = Embedding.objects.create(
                            name=name,
                            path=path,
                            version=version,
                            tags="",
                            active=False,
                            trigger_word="",
                        )
                        embedding_added = True
    return embedding_deleted or embedding_added
