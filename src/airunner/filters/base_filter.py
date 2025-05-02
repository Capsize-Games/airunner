from PIL import ImageFilter

from airunner.gui.windows.main.settings_mixin import SettingsMixin


class BaseFilter(ImageFilter.Filter, SettingsMixin):
    """Base class for all image filters in the AI Runner application.

    This class provides the foundational structure for implementing
    custom image filters. All filter implementations should inherit
    from this class and override the apply_filter method.

    Attributes:
        image: The last processed image reference.
        image_id: ID of the last processed image for caching purposes.
    """

    def __init__(self, **kwargs):
        """Initialize the filter with optional parameters.

        Args:
            **kwargs: Arbitrary keyword arguments that will be set as
                     attributes on the filter instance.
        """
        super().__init__()
        self.image = None
        self.image_id = None

        for k, v in kwargs.items():
            setattr(self, k, v)

    def filter(self, image):
        """Apply the filter to an image.

        This method handles caching and delegates to apply_filter.

        Args:
            image: The PIL Image to filter.

        Returns:
            The filtered PIL Image.
        """
        do_reset = False
        if not self.image_id or self.image_id != id(image):
            self.image_id = id(image)
            self.image = image
            do_reset = True
        return self.apply_filter(image, do_reset)

    def apply_filter(self, image, do_reset=False):
        """Apply the actual filter transformation to the image.

        This method must be overridden by subclasses to implement
        the specific filter behavior.

        Args:
            image: The PIL Image to filter.
            do_reset: Whether the filter should reset its internal state.

        Returns:
            The filtered PIL Image.

        Raises:
            NotImplementedError: If the subclass does not override this method.
        """
        raise NotImplementedError("Subclasses must implement apply_filter()")
