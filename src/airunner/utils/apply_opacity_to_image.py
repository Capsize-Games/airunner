def apply_opacity_to_image(image, target_opacity):
    if not image:
        return image
    target_opacity = 255 * target_opacity
    if target_opacity == 0:
        target_opacity = 1
    image = image.convert("RGBA")
    r, g, b, a = image.split()
    a = a.point(lambda i: target_opacity if i > 0 else 0)
    image.putalpha(a)
    return image
