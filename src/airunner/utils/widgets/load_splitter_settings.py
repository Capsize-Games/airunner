import os
from typing import List
from PySide6.QtCore import Qt  # ADDED IMPORT
from airunner.utils.settings import get_qsettings


def _is_running_in_docker():
    """Check if the application is running inside a Docker container."""
    return os.path.exists("/.dockerenv")


def load_splitter_settings(
    ui: object,
    splitters: List[str],
    orientations: dict = None,
    default_maximize_config: dict = None,  # NEW PARAMETER
):
    """
    Load the state of splitter widgets from PySide6 application settings.
    Skips loading from disk if running in a Docker container.
    Applies default sizes if no settings are found, with an option to maximize a specific panel.
    """
    if orientations is None:
        orientations = {}
    if default_maximize_config is None:  # Initialize new parameter
        default_maximize_config = {}

    running_in_docker = _is_running_in_docker()
    settings = None
    if not running_in_docker:
        settings = get_qsettings()

    for splitter_name in splitters:
        splitter = getattr(ui, splitter_name)
        total_splitter_panels = splitter.count()

        if splitter_name in orientations:
            orientation = orientations[splitter_name]
            splitter.setOrientation(orientation)
        # Ensure orientation is known for default sizing logic
        current_orientation = splitter.orientation()

        splitter_state = None
        if not running_in_docker and settings:
            # Retrieve the splitter state from application settings
            splitter_state = settings.value(f"splitters/{splitter_name}", None)

        # Attempt to restore state if available and not in Docker
        if splitter_state and not running_in_docker:
            try:
                splitter.restoreState(splitter_state)
            except Exception as e:
                print(
                    f"Error restoring splitter state for {splitter_name}: {e}. Applying default sizes."
                )
                splitter_state = None  # Mark as if no state was found to trigger default sizing

        # Apply default sizes if no state was restored, or if in Docker
        if not splitter_state or running_in_docker:
            min_sensible_size_for_panels = (
                50  # A general minimum for any panel
            )

            # Determine a dimension to use for calculating proportional sizes.
            # If splitter has no size yet, use a nominal dimension.
            actual_dimension = 0
            if current_orientation == Qt.Horizontal:
                actual_dimension = splitter.width()
            else:  # Qt.Vertical
                actual_dimension = splitter.height()

            nominal_dimension_if_unknown = (
                800 if current_orientation == Qt.Horizontal else 600
            )
            calc_dimension = (
                actual_dimension
                if actual_dimension > 0
                else nominal_dimension_if_unknown
            )

            sizes = []
            if total_splitter_panels > 0:
                config_for_this_splitter = default_maximize_config.get(
                    splitter_name
                )

                if config_for_this_splitter and total_splitter_panels > 1:
                    idx_to_maximize = config_for_this_splitter.get(
                        "index_to_maximize"
                    )
                    min_size_for_other_panels = config_for_this_splitter.get(
                        "min_other_size", min_sensible_size_for_panels
                    )

                    if (
                        idx_to_maximize is not None
                        and 0 <= idx_to_maximize < total_splitter_panels
                    ):
                        sizes = [0] * total_splitter_panels
                        space_for_minimized_panels = (
                            min_size_for_other_panels
                            * (total_splitter_panels - 1)
                        )
                        size_for_maximized = (
                            calc_dimension - space_for_minimized_panels
                        )

                        min_for_maximized_panel = max(
                            min_size_for_other_panels,
                            min_sensible_size_for_panels,
                        )
                        if size_for_maximized < min_for_maximized_panel:
                            size_for_maximized = min_for_maximized_panel

                        for i in range(total_splitter_panels):
                            if i == idx_to_maximize:
                                sizes[i] = size_for_maximized
                            else:
                                sizes[i] = min_size_for_other_panels
                    else:  # Invalid or inapplicable config, fallback to equal distribution
                        panel_size = max(
                            min_sensible_size_for_panels,
                            (
                                calc_dimension // total_splitter_panels
                                if total_splitter_panels > 0
                                else calc_dimension
                            ),
                        )
                        sizes = [
                            panel_size for _ in range(total_splitter_panels)
                        ]
                else:  # No specific config, or only one panel, fallback to equal distribution
                    if total_splitter_panels == 1:
                        sizes = [
                            calc_dimension
                        ]  # Single panel takes all available space
                    else:  # Multiple panels, equal distribution
                        panel_size = max(
                            min_sensible_size_for_panels,
                            (
                                calc_dimension // total_splitter_panels
                                if total_splitter_panels > 0
                                else calc_dimension
                            ),
                        )
                        sizes = [
                            panel_size for _ in range(total_splitter_panels)
                        ]

            if (
                sizes
            ):  # Only call setSizes if there are panels and sizes were calculated
                try:
                    splitter.setSizes(sizes)
                except Exception as e:
                    print(
                        f"Error setting default sizes for {splitter_name} with sizes {sizes}: {e}"
                    )

        # Store back the potentially modified splitter (already done by getattr earlier)
        # setattr(ui, splitter_name, splitter) # This line was in original, but getattr returns a reference, so changes apply.
