from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget

from airunner.gui.windows.base_window import BaseWindow


class VideoPopup(BaseWindow):
    template_name = "video"
    window_title = "Video preview"

    def __init__(self, file_path):
        self.video_widget = None
        self.media_player = None
        self.file_path = file_path
        super().__init__()

    def initialize_window(self):
        # Create a video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setGeometry(0, 0, 800, 600)

        # Create a media player
        self.media_player = QMediaPlayer()

        # Set the video output
        self.media_player.setVideoOutput(self.video_widget)

        # Set the layout for the dialog
        self.template.layout().addWidget(self.video_widget)

        video_url = QUrl.fromLocalFile(self.file_path)
        self.media_player.setSource(QUrl(video_url))
        self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
        self.media_player.play()
