from typing import List
from airunner.data.models import SplitterSetting


def save_splitter_settings(
    ui: object,
    splitters: List[str]
):
    for splitter_name in splitters:
        widget = getattr(ui, splitter_name)
        sizes = widget.sizes()
    
        valid_state = True
        for size in sizes:
            if size < 50:
                valid_state = False
                break
        
        if valid_state:
            splitter_state = widget.saveState()
            settings = SplitterSetting.objects.filter_by_first(
                name=splitter_name
            )
            if not settings:
                SplitterSetting.objects.create(
                    name=splitter_name,
                    splitter_settings=splitter_state
                )
            else:
                SplitterSetting.objects.update(
                    settings.id,
                    splitter_settings=splitter_state
                )