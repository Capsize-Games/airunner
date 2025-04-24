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
    if orientations is None:
        orientations = {}

    settings = get_qsettings()

    for splitter_name in splitters:
        splitter = getattr(ui, splitter_name)
        splitter.setMinimumWidth(50)
        total_splitter_panels = splitter.count()

        # Set the orientation if specified
        if splitter_name in orientations:
            orientation = orientations[splitter_name]
            splitter.setOrientation(orientation)

        # Retrieve the splitter state from application settings
        splitter_state = settings.value(f"splitters/{splitter_name}", None)

        # Calculate reasonable default sizes
        default_width = (
            splitter.width() or 800
        )  # Fallback to 800 if width is 0
        panel_size = max(50, default_width // total_splitter_panels)
        sizes = [panel_size for _ in range(total_splitter_panels)]

        try:
            if splitter_state:
                # Restore the splitter state if available
                splitter.restoreState(splitter_state)
            else:
                splitter.setSizes(sizes)
        except Exception as e:
            print(f"Error restoring splitter state for {splitter_name}: {e}")
            splitter.setSizes(sizes)

        # Store back the potentially modified splitter
        setattr(ui, splitter_name, splitter)
