import os
import threading

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.image.image_widget import ImageWidget
from airunner.widgets.image.templates.image_panel_widget_ui import Ui_image_panel_widget
from airunner.widgets.qflowlayout.q_flow_layout import QFlowLayout


class ImagePanelWidget(BaseWidget):
    widget_class_ = Ui_image_panel_widget

    def __init__(self, *args, **kwargs):
        """
        Initializes the ImagePanelWidget.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            None
        """
        super().__init__(*args, **kwargs)
        self.page = 0
        self.total_per_page = 50
        self.page_step = 512
        self.last_page = False
        self.sorted_files = []
        self.start = 0
        self.end = 0
        self.ui.scrollArea.verticalScrollBar().valueChanged.connect(self.handle_scroll)
        flowLayout = QFlowLayout()
        self.ui.scrollAreaWidgetContents.setLayout(flowLayout)
        self.display_thread = threading.Thread(target=self.display_thumbnails)

    def showEvent(self, event):
        super().showEvent(event)
        if self.path_settings.image_path != "":
            self.load_files()
            self.show_files()
        else:
            self.logger.warning("Image path not set. Please set the image path in the settings.")

    def clear_files(self):
        self.page = 0
        # remove all images from the container
        while self.ui.scrollAreaWidgetContents.layout().count() > 0:
            item = self.ui.scrollAreaWidgetContents.layout().takeAt(0)
            widget = item.widget()
            widget.deleteLater()

    def show_files(self, clear_images=True, reset_scroll_bar=True, show_folders=True):
        """
        Displays the files in the image panel widget.

        Args:
            clear_images (bool, optional): Whether to clear the existing images. Defaults to True.
            reset_scroll_bar (bool, optional): Whether to reset the scroll bar position. Defaults to True.
            show_folders (bool, optional): Whether to show folders in the file list. Defaults to True.
        """
        if reset_scroll_bar:
            self.ui.scrollArea.verticalScrollBar().setValue(0)

        self.start = self.page * self.total_per_page
        self.end = self.start + self.total_per_page

        self.display_thumbnails()

    def load_files(self):
        """
        Load files from the specified image path and sort them based on modification time.

        Returns:
            None
        """
        image_path = self.path_settings.image_path
        files_in_image_path = os.listdir(image_path)
        sorted_files = {}
        for file in files_in_image_path:
            if os.path.isdir(os.path.join(image_path, file)):
                sorted_files[file] = []
                for root, dirs, files_in_dir in os.walk(os.path.join(image_path, file)):
                    files = []
                    for f in files_in_dir:
                        if ".png.thumbnail.png" not in f:
                            files.append(os.path.join(root, f))
                    sorted_files[file].extend(files)
        
        section = "txt2img"
        files = sorted_files[section]
        files.sort(key=os.path.getmtime, reverse=True)
        self.sorted_files = files

    def display_thumbnails(self):
        """
        Display thumbnails of images from the sorted_files list within the specified range.
        """
        for file in self.sorted_files[self.start:self.end]:
            if file.endswith(".png"):
                image_widget = ImageWidget(self, is_thumbnail=True)
                image_widget.set_image(os.path.join(self.path_settings.image_path, file))
                self.ui.scrollAreaWidgetContents.layout().addWidget(image_widget)
    
    def handle_folder_clicked(self, path):
        """
        Handles the event when a folder is clicked.

        Args:
            path (str): The path of the clicked folder.
        """
        self.show_files()
    
    def handle_scroll(self, value):
        """
        Handles the scroll event of the image panel widget.

        Args:
            value (int): The value of the scroll event.

        Returns:
            None
        """
        if value >= self.ui.scrollArea.verticalScrollBar().maximum() - self.page_step + 1:
            self.page += 1
            self.show_files(clear_images=False, reset_scroll_bar=False, show_folders=False)
