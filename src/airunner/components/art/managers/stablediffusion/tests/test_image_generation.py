from PIL import Image
from PIL import Image

from airunner.components.art.managers.stablediffusion.image_generation import (
    check_and_mark_nsfw_images,
    NSFWChecker,
    is_nsfw,
    save_image,
    export_image,
)


class DummyFeatureExtractor:
    def __call__(self, images, return_tensors=None):
        class PixelValues:
            def __init__(self, vals):
                self.vals = vals

            def to(self, device):
                return self

        class R:
            def __init__(self, vals):
                self.pixel_values = PixelValues(vals)

            def to(self, device):
                return self

        return R(images)


class DummySafetyChecker:
    def to(self, device):
        return None

    def __call__(self, images, clip_input=None):
        # mark first image as safe and second as nsfw if two provided
        has_nsfw = [False] * len(images)
        if len(images) > 1:
            has_nsfw[1] = True
        return images, has_nsfw


def test_check_and_mark_nsfw_images_no_feature_or_checker():
    img = Image.new("RGB", (32, 32))
    out, flags = check_and_mark_nsfw_images([img], None, None, "cpu")
    assert flags == [False]
    assert out[0] is img


def test_check_and_mark_nsfw_images_with_checker():
    img1 = Image.new("RGB", (32, 32))
    img2 = Image.new("RGB", (32, 32))
    fe = DummyFeatureExtractor()
    sc = DummySafetyChecker()
    images, flags = check_and_mark_nsfw_images([img1, img2], fe, sc, "cpu")
    assert flags == [False, True]
    # second image should have been converted to RGBA
    assert images[1].mode == "RGBA"


def test_nsfw_checker_and_helpers():
    checker = NSFWChecker()
    assert checker.is_nsfw(None) is False
    assert is_nsfw(None) is False
    assert save_image(None, "/tmp/x.png") == "/tmp/x.png"
    assert export_image(None, "/tmp/y.png") == "/tmp/y.png"
