from airunner.components.nodegraph.gui.widgets.nodes.video.framepack_node import (
    FramePackNode,
    register_nodes,
)

from airunner.components.nodegraph.gui.widgets.nodes.video.video_player_node import (
    VideoNode,
)

# Register nodes can be called from external code to register these nodes
__all__ = ["FramePackNode", "register_nodes", "VideoNode"]
