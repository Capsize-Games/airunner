from typing import List
from airunner.data.models import SplitterSetting


def load_splitter_settings(
    ui: object,
    splitters: List[str]
):
    for splitter_name in splitters:
        splitter = getattr(ui, splitter_name)
        splitter.setMinimumWidth(50)
        total_splitter_panels = splitter.count()
        
        settings = SplitterSetting.objects.filter_by_first(
            name="main_window_splitter"
        )

        if settings:
            sizes = [
                200 for _ in range(total_splitter_panels)
            ]
            try:
                state = settings.splitter_settings
                if state and len(state) > 0:
                    splitter.restoreState(state)
                else:
                    splitter.setSizes(sizes)
            except Exception as e:
                splitter.setSizes(sizes)
        setattr(ui, splitter_name, splitter)