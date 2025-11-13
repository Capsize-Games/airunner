


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
