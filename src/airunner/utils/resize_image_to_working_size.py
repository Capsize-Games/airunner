def resize_image_to_working_size(image, settings):
    # get size of image
    width, height = image.size
    working_width = settings.working_width
    working_height = settings.working_height

    # get the aspect ratio of the image
    aspect_ratio = width / height

    # choose to resize based on width or height, for example if
    # working size is 100x50 and the image is 100x200, we want to
    # resize the image to 25x50 so that it fits in the working size.
    # if the image is 200x100, we want to resize it to 100x50.
    if working_width / working_height > aspect_ratio:
        # resize based on height
        new_width = int(working_height * aspect_ratio)
        new_height = working_height
    else:
        # resize based on width
        new_width = working_width
        new_height = int(working_width / aspect_ratio)

    return image.resize((new_width, new_height))
