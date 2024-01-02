import io
import json
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.image.image_widget import BrushImageWidget
from airunner.widgets.qflowlayout.q_flow_layout import QFlowLayout
from PyQt6.QtWidgets import QInputDialog
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from airunner.utils import get_session
from airunner.data.models import Brush, GeneratorSetting
import base64
from PIL import Image
from io import BytesIO
from PyQt6.QtCore import QBuffer
from PyQt6.QtWidgets import QMenu


class BrushesContainer(BaseWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Enable the widget to accept drops
        self.setAcceptDrops(True)

        # Create a layout to manage the widgets
        self.layout = QFlowLayout()
        self.setLayout(self.layout)

        self.load_brushes()

    def dragEnterEvent(self, event):
        # Accept the drag enter event if the data is text
        event.acceptProposedAction()
    
    def save_brush(self, brush_name, thumbnail: QPixmap, meta_data):
        # Convert QPixmap to QImage
        image = thumbnail.toImage()

        # Convert QImage to raw bytes
        from PyQt6.QtCore import QIODevice  # Import the QIODevice class

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.ReadWrite)  # Use QIODevice.OpenModeFlag.ReadWrite
        image.save(buffer, "PNG")

        # Use PIL to open the image from raw bytes
        with Image.open(io.BytesIO(buffer.data())) as img:
            # Convert the image to RGB
            img = img.convert('RGB')

            # Create a BytesIO object
            buffer = BytesIO()

            # Save the image to the BytesIO object
            img.save(buffer, format='PNG')

            # Get the bytes value of the image
            img_bytes = buffer.getvalue()

            # Convert the bytes to base64
            img_base64 = base64.b64encode(img_bytes).decode()

        session = get_session()

        # Create a new GeneratorSetting entry with the metadata
        generator_setting = GeneratorSetting(
            section=meta_data.get("section", getattr(self.settings_manager, f"current_section_{self.settings_manager.current_image_generator}")),
            generator_name=meta_data.get("generator_name", self.settings_manager.current_image_generator),
            prompt=meta_data.get("prompt", ""),
            negative_prompt=meta_data.get("negative_prompt", ""),
            steps=meta_data.get("steps", 20),
            ddim_eta=meta_data.get("ddim_eta", 0.5),
            height=meta_data.get("height", 512),
            width=meta_data.get("width", 512),
            scale=meta_data.get("scale", 750),
            seed=meta_data.get("seed", 42),
            latents_seed=meta_data.get("latents_seed", 84),
            random_seed=meta_data.get("random_seed", True),
            random_latents_seed=meta_data.get("random_latents_seed", True),
            model=meta_data.get("model", ""),
            scheduler=meta_data.get("scheduler", "DPM++ 2M Karras"),
            prompt_triggers=meta_data.get("prompt_triggers", ""),
            strength=meta_data.get("strength", 50),
            image_guidance_scale=meta_data.get("image_guidance_scale", 150),
            n_samples=meta_data.get("n_samples", 1),
            controlnet=meta_data.get("controlnet", ""),
            enable_controlnet=meta_data.get("enable_controlnet", False),
            enable_input_image=meta_data.get("enable_input_image", False),
            controlnet_guidance_scale=meta_data.get("controlnet_guidance_scale", 50),
            clip_skip=meta_data.get("clip_skip", 0),
            variation=meta_data.get("variation", False),
            input_image_use_imported_image=meta_data.get("input_image_use_imported_image", False),
            input_image_use_grid_image=meta_data.get("input_image_use_grid_image", True),
            input_image_recycle_grid_image=meta_data.get("input_image_recycle_grid_image", True),
            input_image_mask_use_input_image=meta_data.get("input_image_mask_use_input_image", True),
            input_image_mask_use_imported_image=meta_data.get("input_image_mask_use_imported_image", False),
            controlnet_input_image_link_to_input_image=meta_data.get("controlnet_input_image_link_to_input_image", True),
            controlnet_input_image_use_imported_image=meta_data.get("controlnet_input_image_use_imported_image", False),
            controlnet_use_grid_image=meta_data.get("controlnet_use_grid_image", False),
            controlnet_recycle_grid_image=meta_data.get("controlnet_recycle_grid_image", False),
            controlnet_mask_link_input_image=meta_data.get("controlnet_mask_link_input_image", False),
            controlnet_mask_use_imported_image=meta_data.get("controlnet_mask_use_imported_image", False),
            use_prompt_builder=meta_data.get("use_prompt_builder", False),
            active_grid_border_color=meta_data.get("active_grid_border_color", "#00FF00"),
            active_grid_fill_color=meta_data.get("active_grid_fill_color", "#FF0000")
        )

        session.add(generator_setting)
        session.commit()

        # Create a new Brush entry associated with the GeneratorSetting entry
        brush = Brush(name=brush_name, thumbnail=img_base64, generator_setting_id=generator_setting.id)
        session.add(brush)

        session.commit()

        return brush
    
    selected_brushes = []

    def activate_brush(self, clicked_widget, brush, multiple):
        if clicked_widget in self.selected_brushes:
            if len(self.selected_brushes) == 1:
                self.selected_brushes.remove(clicked_widget)
                clicked_widget.setStyleSheet("")
            else:
                for widget in self.selected_brushes:
                    if not multiple:
                        if widget is not clicked_widget:
                            self.selected_brushes.remove(widget)
                            widget.setStyleSheet("")
                            break
                    else:
                        self.selected_brushes.remove(widget)
                        widget.setStyleSheet("")
            return

        for widget in self.selected_brushes:
            try:
                widget.setStyleSheet("")
            except RuntimeError:
                pass
        
        if not multiple:
            self.selected_brushes = [clicked_widget]
        else:
            self.selected_brushes.append(clicked_widget)
        
        if len(self.selected_brushes) > 2:
            self.selected_brushes = self.selected_brushes[1:]
        
        for widget in self.selected_brushes:
            widget.setStyleSheet(f"""
                border: 2px solid #ff0000;
            """)
            self.app.ui.generator_widget.enable_preset(widget.brush.generator_setting_id)
    
    def display_brush_menu(self, event, widget, brush):
        context_menu = QMenu(self)

        delete_action = context_menu.addAction("Delete brush")
        delete_action.triggered.connect(lambda: self.delete_brush(widget, brush))

        global_position = self.mapToGlobal(event.pos())
        context_menu.exec(global_position)

    def delete_brush(self, widget, brush):
        session = get_session()
        brush = session.query(Brush).filter(Brush.id == brush.id).first()
        generator_setting = session.query(GeneratorSetting).filter(GeneratorSetting.id == brush.generator_setting_id).first()
        
        if generator_setting is not None:
            session.delete(generator_setting)
        
        if brush is not None:
            session.delete(brush)
        
        session.commit()
        widget.deleteLater()
    
    def create_and_add_widget(self, image_source, is_base64=False, brush=None):
        widget = BrushImageWidget(self, container=self, brush=brush)

        if is_base64:
            # Convert the base64 image back to bytes
            img_bytes = base64.b64decode(image_source)
            
            # Create a BytesIO object from the bytes
            buffer = BytesIO(img_bytes)
            
            # Open the image file
            img = Image.open(buffer)
        else:
            img = image_source
        # Set the image to the widget
        widget.set_image(img)
        
        # Add the widget to the layout
        self.layout.addWidget(widget)

        return widget

    def dropEvent(self, event):
        # Get the metadata from the event's mime data
        meta_data_bytes = event.mimeData().data("application/x-qt-image-metadata")

        # Decode the bytes to a string
        meta_data_str = bytes(meta_data_bytes).decode()

        # Parse the JSON string to a dictionary
        meta_data = json.loads(meta_data_str)

        image_path = meta_data["path"]

        # Create an instance of the widget with the image path
        widget = self.create_and_add_widget(image_path)

        # Show a popup window asking the user to name the brush
        brush_name, ok = QInputDialog.getText(self, 'Name the preset', 'Enter preset name:')

        # If the user cancels the dialog, remove the widget from the layout
        if not ok or not brush_name:
            widget.deleteLater()
        else:
            # Save the brush name, thumbnail, and metadata to the database
            widget.brush = self.save_brush(brush_name, widget.thumbnail(), meta_data)
            

        event.acceptProposedAction()

    def load_brushes(self):
        session = get_session()
        brushes = session.query(Brush).all()

        for brush in brushes:
            self.create_and_add_widget(brush.thumbnail, is_base64=True, brush=brush)
