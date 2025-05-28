import os
from pathlib import Path

from airunner.data.models import Lora, Embedding


# Dummy mixin for test patching
class SettingsMixin:
    pass


def scan_path_for_lora(base_path) -> bool:
    lora_added = False
    lora_deleted = False
    model_base = Path(base_path) / "art" / "models"

    if not model_base.exists():
        return False

    for versionpath, versionnames, versionfiles in os.walk(str(model_base)):
        # versionpath will be like /path/to/art/models/version_name
        # We only want to process actual version directories, not model_base itself
        if Path(versionpath) == model_base:
            continue
        version = os.path.basename(versionpath)
        lora_path = Path(versionpath) / "lora"

        if not lora_path.exists():
            continue

        existing_lora = Lora.objects.all()
        for lora_db_item in existing_lora:
            if not Path(lora_db_item.path).exists():
                Lora.objects.delete(lora_db_item.id)
                lora_deleted = True

        for dirpath, dirnames, filenames in os.walk(str(lora_path)):
            for file in filenames:
                if (
                    file.endswith(".ckpt")
                    or file.endswith(".safetensors")
                    or file.endswith(".pt")
                ):
                    name = Path(file).stem  # More robust way to get name without extension
                    path_obj = Path(dirpath) / file
                    path_str = str(path_obj)
                    item = Lora.objects.filter_first(Lora.name == name, Lora.version == version) # Also check version
                    if (
                        not item
                        or item.path != path_str
                        # item.version != version # Already checked in filter
                    ):
                        if item and item.path != path_str: # Update path if name and version match but path differs
                            item.path = path_str
                            item.save()
                            # Consider if other attributes need updating or if it implies a new entry
                            lora_added = True # Or some other flag indicating an update
                        elif not item:
                            Lora.objects.create(
                                name=name,
                                path=path_str,
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
    model_base = Path(base_path) / "art" / "models"

    if not model_base.exists():
        return False

    for versionpath, versionnames, versionfiles in os.walk(str(model_base)):
        # versionpath will be like /path/to/art/models/version_name
        # We only want to process actual version directories, not model_base itself
        if Path(versionpath) == model_base:
            continue
        version = os.path.basename(versionpath)
        embedding_path = Path(versionpath) / "embeddings"

        if not embedding_path.exists():
            continue

        existing_embeddings = Embedding.objects.all()
        for embedding_db_item in existing_embeddings:
            if not Path(embedding_db_item.path).exists():
                Embedding.objects.delete(embedding_db_item.id)
                embedding_deleted = True

        for dirpath, dirnames, filenames in os.walk(str(embedding_path)):
            for file in filenames:
                if (
                    file.endswith(".ckpt")
                    or file.endswith(".safetensors")
                    or file.endswith(".pt")
                ):
                    name = Path(file).stem # More robust way to get name without extension
                    path_obj = Path(dirpath) / file
                    path_str = str(path_obj)
                    item = Embedding.objects.filter_first(Embedding.name == name, Embedding.version == version) # Also check version
                    if (
                        not item
                        or item.path != path_str
                        # item.version != version # Already checked in filter
                    ):
                        if item and item.path != path_str: # Update path if name and version match but path differs
                            item.path = path_str
                            item.save()
                            # Consider if other attributes need updating or if it implies a new entry
                            embedding_added = True # Or some other flag indicating an update
                        elif not item:
                            Embedding.objects.create(
                                name=name,
                                path=path_str,
                                version=version,
                                tags="",
                                active=False,
                                trigger_word="",
                            )
                            embedding_added = True
    return embedding_deleted or embedding_added
