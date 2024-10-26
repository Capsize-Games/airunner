from PIL import Image
from PIL.ImageQt import QImage


def pil_to_qimage(pil_image):
    if pil_image.mode == "RGB":
        r, g, b = pil_image.split()
        pil_image = Image.merge("RGBA", (r, g, b, Image.new("L", r.size, 255)))
    elif pil_image.mode == "L":
        pil_image = pil_image.convert("RGBA")
    data = pil_image.tobytes("raw", "RGBA")
    qimage = QImage(data, pil_image.size[0], pil_image.size[1], QImage.Format.Format_RGBA8888)
    return qimage
