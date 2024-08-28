import os


def scan_path_for_items(base_path, current_items, scan_type="lora"):
    for versionpath, versionnames, versionfiles in os.walk(os.path.expanduser(os.path.join(base_path, "art/models"))):
        version = versionpath.split("/")[-1]
        embedding_path = os.path.expanduser(
            os.path.join(
                base_path,
                "art/models",
                version,
                scan_type
            )
        )
        for dirpath, dirnames, filenames in os.walk(embedding_path):
            for file in filenames:
                if file.endswith(".ckpt") or file.endswith(".safetensors") or file.endswith(".pt"):
                    name = file.replace(".ckpt", "").replace(".safetensors", "").replace(".pt", "")
                    path = os.path.join(dirpath, file)
                    if type(current_items) is not dict:
                        current_items = {}
                    if version not in current_items:
                        current_items[version] = []
                    add_item = True
                    for item in current_items[version]:
                        if item["name"] == name and item["path"] == str(path):
                            add_item = False
                            break
                    if add_item:
                        if scan_type == "lora":
                            item_data = dict(
                                name=name,
                                path=path,
                                scale=1,
                                enabled=True,
                                loaded=False,
                                trigger_word="",
                                version=version
                            )
                        elif scan_type == "embeddings":
                            item_data = dict(
                                name= name,
                                path= path,
                                version= version,
                                tags= "",
                                active= True,
                                trigger_word= "",
                            )
                        else:
                            item_data = None

                        if item_data:
                            current_items[version].append(item_data)
    return current_items
