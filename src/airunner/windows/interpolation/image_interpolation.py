import os
from PIL import Image
from PyQt6 import uic
from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel

from airunner.windows.interpolation.templates.interpolation_ui import Ui_interpolation_window
from airunner.utils import image_to_pixmap
from airunner.windows.base_window import BaseWindow
from functools import partial


class ImageInterpolation(BaseWindow):
    template_class_ = Ui_interpolation_window
    is_modal = True

    def __init__(self, *args, **kwargs):
        self.adjusting_interpolation_weight = False
        self.images = {}

        super().__init__(*args, **kwargs)

    def initialize_window(self):
        self.interpolation_container = self.ui.interpolation_scrollarea.widget()
        self.interpolation_container_layout = self.interpolation_container.layout()
        self.add_interpolation_widget()
        self.ui.add_blend_option_button.clicked.connect(self.add_interpolation_widget)
        self.load_generate_form()

        """
        This is a hack to make the Kandinsky txt2img generate button say "Interpolate" instead of "Generate"
        """
        self.app.generator_tab_widget.data["kandinsky"]["txt2img"]["generate_button"].setText("Interpolate")

        """
        We also set use_interpolation and the get_interpolation_data function on the parent so that when we click
        the "Interpolate" button, it will pass these values to the aihandler runner as options.
        """
        # QtCore.pyqtSignal has no attribute 'connect'
        # this is because the parent class is not a QObject
        self.app.generate_signal.connect(self.handle_generate_signal)
        self.app.add_image_to_canvas_signal.connect(self.handle_add_image_to_canvas_signal)

        """
        We track this window and if it is open, we pass image processing data to this window rather than processing
        the image through its normal pipeline. We do this so that we can show the user the interpolated images
        in the sidebar and let the user decide what to do with them.
        """
        self.app.image_interpolation_window = self

        self.ui.kandinsky_button.clicked.connect(self.handle_kandinsky_button)
        self.ui.closeEvent = self.handle_close

    def handle_generate_signal(self, options):
        options["use_interpolation"] = True
        options["interpolation_data"] = self.get_interpolation_data()

    def handle_add_image_to_canvas_signal(self, data):
        data["add_image_to_canvas"] = False
        self.handle_interpolated_image(data["processed_image"])

    def handle_kandinsky_button(self):
        """
        Clicking the Kandinsky button activates the Kandinsky txt2img tab.
        :return:
        """
        self.app.generator_tab_widget.sectionTabWidget.setCurrentIndex(1)
        self.app.generator_tab_widget.stableDiffusionTabWidget.setCurrentIndex(0)

    def handle_interpolated_image(self, image):
        """
        Called from the image processing pipeline after an image is generated. It displays
        the image in a widget in the sidebar and allows the user to export to perform various actions on the image.
        :param image: The image generated with interpolation.
        :return:
        """
        widget = uic.loadUi(os.path.join("pyqt/generated_image.ui"))
        pixmap = image_to_pixmap(image, 256)
        widget.image_container.setPixmap(pixmap)
        container = self.ui.generate_scroll_area.widget()
        self.ui.interpolated_images_label.hide()
        widget.to_canvas_button.clicked.connect(partial(self.handle_interpolated_image_to_canvas_button, image=image))
        widget.export_button.clicked.connect(partial(self.handle_interpolated_image_export_button, image=image))
        widget.delete_button.clicked.connect(partial(self.handle_interpolated_image_delete_button, widget=widget))
        widget.to_slot_button.clicked.connect(partial(self.handle_interpolated_image_to_slot_button, widget=widget, image=image))
        for i in range(self.interpolation_container_layout.count()):
            widget.slot_combobox.addItem("Slot " + str(i + 1))
        container.layout().addWidget(widget)

    def handle_interpolated_image_to_slot_button(self, widget, image):
        """
        Send an interpolated image to a selected interpolation slot. This allows the user to easily reuse an image
        that was generated with interpolation for further interpolation.
        :param widget:
        :param image:
        :return:
        """
        interpoloation_container = self.interpolation_container
        index = widget.slot_combobox.currentIndex()
        interpolation_widget = interpoloation_container.layout().itemAt(index).widget()
        widget_id = id(interpolation_widget)
        pixmap = image_to_pixmap(image, 128)
        interpolation_widget.image_container.setPixmap(pixmap)
        self.images[widget_id] = image

    def handle_interpolated_image_export_button(self, image):
        """
        Export an interpolated image to a file.
        :param widget:
        :param image:
        :return:
        """
        file_name, _ = self.app.display_file_export_dialog()
        if file_name:
            self.app.canvas.save_image(file_name, image=image)

    def handle_interpolated_image_to_canvas_button(self, widget, image):
        self.app.canvas.add_image_to_canvas(
            image,
            image_root_point=QPoint(0, 0),
            image_pivot_point=QPoint(0, 0),
        )
        self.app.canvas.update()

    def handle_interpolated_image_delete_button(self, widget):
        widget.deleteLater()
        widget.setParent(None)
        self.ui.interpolated_images_label.show()

    def handle_close(self, event):
        """
        On close we set the generate button back to "Generate" and set use_interpolation and get_interpolation_data
        back to their default values. This prevents interpolation from being used without the interpolation window.
        :param event:
        :return:
        """
        self.app.generator_tab_widget.data["kandinsky"]["txt2img"]["generate_button"].setText("Generate")
        self.app.use_interpolation = False
        self.app.get_interpolation_data = None
        self.ui.close()

    def load_generate_form(self):
        pass

    def handle_interpolation_checkbox_change(self, val):
        self.app.use_interpolation = val == 2

    def add_interpolation_widget(self):
        widget = uic.loadUi(os.path.join("pyqt/blend_option_widget.ui"))
        widget.weight_slider.valueChanged.connect(partial(self.handle_interpolation_weight_slider_change, widget=widget))
        widget.weight_spinbox.valueChanged.connect(partial(self.handle_interpolation_weight_spinbox_change, widget=widget))
        widget.delete_button.clicked.connect(partial(self.handle_interpolation_delete_button, widget))
        widget.image_or_text_combobox.currentIndexChanged.connect(partial(self.handle_interpolation_image_or_text_combobox_change, widget=widget))
        widget.plainTextEdit.hide()
        # add each layer to the widget.layer_combobox
        widget.layer_combobox.addItem("None")
        for layer in self.app.canvas.layers:
            widget.layer_combobox.addItem(layer.name)
        # on change of widget.layer_combobox, change the thumbnail
        widget.layer_combobox.currentIndexChanged.connect(partial(self.show_thumbnail, widget=widget))
        self.ui.interpolation_scrollarea.setWidget(self.interpolation_container)
        # create a border around widget.image_container
        widget.import_image_button.clicked.connect(partial(self.handle_interpolation_import_image_button, widget=widget))

        self.interpolation_container_layout.addWidget(widget)

        # count number of widgets
        num_widgets = self.interpolation_container_layout.count()
        total = 100 // num_widgets
        widget.weight_slider.setValue(total)

        self.update_interpolation_slot_combobox()

    def update_interpolation_slot_combobox(self):
        # iterate over all interpolation widgets and update the slot combobox
        container = self.ui.generate_scroll_area.widget()
        num_widgets = self.interpolation_container_layout.count()
        for i in range(container.layout().count()):
            interpolation_widget = container.layout().itemAt(i).widget()
            # skip if interpolation_widget is a QLabel
            if isinstance(interpolation_widget, QLabel):
                continue
            # clear interpolation_widget.slot_combobox
            interpolation_widget.slot_combobox.clear()
            for j in range(num_widgets):
                interpolation_widget.slot_combobox.addItem("Slot " + str(j + 1))

    def update_interpolation_layer_combobox(self, layer_name):
        for i in range(self.interpolation_container_layout.count()):
            widget = self.interpolation_container_layout.itemAt(i).widget()
            widget.layer_combobox.addItem(layer_name)

    def handle_interpolation_image_or_text_combobox_change(self, val, widget):
        if val == 0:
            widget.plainTextEdit.setEnabled(False)
            # do not show the text edit
            widget.plainTextEdit.hide()
            widget.layer_combobox.setEnabled(True)
            widget.layer_combobox.show()
            widget.import_image_button.setEnabled(True)
            widget.import_image_button.show()
            widget.image_container.show()
        else:
            widget.plainTextEdit.setEnabled(True)
            widget.plainTextEdit.show()
            widget.layer_combobox.setEnabled(False)
            widget.layer_combobox.hide()
            widget.import_image_button.setEnabled(False)
            widget.import_image_button.hide()
            widget.image_container.hide()

    def show_thumbnail(self, layer_id, widget):
        image = None
        if layer_id > 0:
            layer_id -= 1
            image = self.app.canvas.layers[layer_id].image_data.image
        if image is None:
            widget.image_container.setPixmap(QPixmap())
            return
        # convert pil image to pixmap
        pixmap = image_to_pixmap(image, 128)
        widget.image_container.setPixmap(pixmap)

    def handle_interpolation_import_image_button(self, val, widget):
        # display a file dialog to select an image
        file_path, _ = self.app.display_import_image_dialog(label="Select an image", directory=self.app.settings_manager.path_settings.image_path)
        if file_path == "":
            return
        image = Image.open(file_path)
        pixmap = image_to_pixmap(image, 128)
        widget.layer_combobox.setCurrentIndex(0)
        widget.image_container.setPixmap(pixmap)
        widget_id = id(widget)
        self.images[widget_id] = image

    def handle_interpolation_delete_button(self, widget):
        widget_id = id(widget)
        if widget_id in self.images:
            del self.images[widget_id]
        self.interpolation_container_layout.removeWidget(widget)
        widget.deleteLater()
        num_widgets = self.interpolation_container_layout.count()
        if num_widgets > 0:
            for i in range(num_widgets):
                widget = self.interpolation_container_layout.itemAt(i).widget()
                widget.weight_slider.setValue(int(100 / num_widgets))
        else:
            self.add_interpolation_widget()

        self.update_interpolation_slot_combobox()

    def get_interpolation_data(self):
        # iterate over each interpolation widget and get the weight and type (layer or text)
        data = []
        for i in range(self.interpolation_container_layout.count()):
            widget = self.interpolation_container_layout.itemAt(i).widget()
            weight_type = widget.image_or_text_combobox.currentIndex()
            if weight_type == 0:  # image
                # get layer by name
                widget_id = id(widget)
                image = self.images[widget_id] if widget_id in self.images else None
                if image is None:
                    for layer in self.app.canvas.layers:
                        if layer.name == widget.layer_combobox.currentText():
                            image = layer.image_data.image
                            break
                text = None
                weight_type = "image"
            elif weight_type == 1:  # text
                image = None
                text = widget.plainTextEdit.toPlainText()
                weight_type = "text"
            data.append({
                "weight": widget.weight_slider.value() / 100,
                "type": weight_type,
                "text": text,
                "image": image
            })
        return data

    def handle_interpolation_weight_slider_change(self, value, widget):
        widget.weight_spinbox.setValue(value / 100)
        # change the weight of the other widgets to be a blend of the total
        num_widgets = self.interpolation_container_layout.count()
        if num_widgets > 1 and not self.adjusting_interpolation_weight:
            self.adjusting_interpolation_weight = True
            for i in range(num_widgets):
                if i != self.interpolation_container_layout.indexOf(widget):
                    other_widget = self.interpolation_container_layout.itemAt(i).widget()
                    other_widget.weight_slider.setValue(int((100 - value) / (num_widgets - 1)))
            self.adjusting_interpolation_weight = False

    def handle_interpolation_weight_spinbox_change(self, value, widget):
        widget.weight_slider.setValue(int(value * 100))
