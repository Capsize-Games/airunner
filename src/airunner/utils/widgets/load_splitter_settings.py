from typing import List
from airunner.utils.settings import get_qsettings


def load_splitter_settings(
    ui: object,
    splitters: List[str],
    orientations: dict = None,  # Dictionary mapping splitter_name to orientation
):
    """
    Load the state of splitter widgets from PySide6 application settings.
    """
    # if orientations is None:
    #     orientations = {}

    # settings = get_qsettings()

    # for splitter_name in splitters:
    #     splitter = getattr(ui, splitter_name)
    #     total_splitter_panels = splitter.count()

    #     # Set the orientation if specified
    #     if splitter_name in orientations:
    #         orientation = orientations[splitter_name]
    #         splitter.setOrientation(orientation)

    #     # Retrieve the splitter state from application settings
    #     splitter_state = settings.value(f"splitters/{splitter_name}", None)

    #     # Calculate reasonable default sizes
    #     default_width = (
    #         splitter.width() or 800
    #     )  # Fallback to 800 if width is 0
    #     panel_size = max(50, default_width // total_splitter_panels)
    #     sizes = [panel_size for _ in range(total_splitter_panels)]

    #     try:
    #         if splitter_state:
    #             # Restore the splitter state if available
    #             splitter.restoreState(splitter_state)
    #         else:
    #             splitter.setSizes(sizes)
    #     except Exception as e:
    #         print(f"Error restoring splitter state for {splitter_name}: {e}")
    #         splitter.setSizes(sizes)

    #     # Store back the potentially modified splitter
    #     setattr(ui, splitter_name, splitter)

    # Set splitter width to minwidth of the same splitter
    for splitter_name in splitters:
        splitter = getattr(ui, splitter_name)

        if splitter.count() == 0:  # If splitter has no widgets, skip
            continue

        new_sizes = []
        for i in range(splitter.count()):
            widget = splitter.widget(i)
            # Determine minimum width for the widget
            # Prefer minimumSizeHint, then minimumWidth, then a fallback.
            min_w = widget.minimumSizeHint().width()

            if min_w <= 0:  # If hint is not positive or useful
                min_w = widget.minimumWidth()  # Try the explicit minimumWidth

            if min_w <= 0:  # If still not positive or useful
                min_w = 50  # Fallback to a default minimum panel width
            new_sizes.append(min_w)

        splitter.setSizes(new_sizes)
