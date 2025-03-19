from typing import List
from airunner.data.models import SplitterSetting


def load_splitter_settings(
    ui: object,
    splitters: List[str],
    orientations: dict = None  # Dictionary mapping splitter_name to orientation
):
    if orientations is None:
        orientations = {}
        
    for splitter_name in splitters:
        splitter = getattr(ui, splitter_name)
        splitter.setMinimumWidth(50)
        total_splitter_panels = splitter.count()
        
        # Set the orientation if specified
        if splitter_name in orientations:
            orientation = orientations[splitter_name]
            splitter.setOrientation(orientation)
        
        settings = SplitterSetting.objects.filter_by_first(
            name=splitter_name  # Use the actual splitter name
        )

        if settings:
            # Calculate reasonable default sizes
            default_width = splitter.width() or 800  # Fallback to 800 if width is 0
            panel_size = max(50, default_width // total_splitter_panels)
            sizes = [panel_size for _ in range(total_splitter_panels)]
            
            try:
                state = settings.splitter_settings
                if state and len(state) > 0:
                    # Check if we're loading the correct state for this splitter
                    splitter.restoreState(state)
                else:
                    splitter.setSizes(sizes)
            except Exception as e:
                print(f"Error restoring splitter state for {splitter_name}: {e}")
                splitter.setSizes(sizes)
        
        # Store back the potentially modified splitter
        setattr(ui, splitter_name, splitter)