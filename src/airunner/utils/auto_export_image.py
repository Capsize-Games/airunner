import os

from airunner.exceptions import AutoExportSeedException


def auto_export_image(
        base_path,
        image_path,
        image_export_type,
        image,
        data=None,
        seed=None,
        type="image",
):
    if seed is None:
        raise AutoExportSeedException()

    data["options"]["seed"] = seed

    if data and "action" in data and data["action"] == "txt2vid":
        return None, None

    if type == "image":
        image_path = "images" if image_path == "" else image_path
    elif type == "controlnet":
        image_path = os.path.join(image_path, "controlnet_masks")

    path = os.path.join(base_path, image_path) if image_path == "images" else image_path
    if not os.path.exists(path):
        os.makedirs(path)

    extension = image_export_type
    if extension == "":
        extension = "png"
    extension = f".{extension}"

    filename = "image"
    if data:
        if type == "image":
            filename = data["action"]
        elif type == "controlnet":
            filename = f"mask_{data['controlnet']}"

    filename = f"{filename}_{str(seed)}"
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

