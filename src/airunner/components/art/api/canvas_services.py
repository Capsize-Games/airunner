from typing import Any, Dict, List
from airunner.components.application.api.api_service_base import APIServiceBase
from airunner.components.art.data.brush_settings import BrushSettings
from airunner.components.art.data.canvas_layer import CanvasLayer
from airunner.components.art.data.controlnet_settings import ControlnetSettings
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings
from airunner.components.art.data.image_to_image_settings import (
    ImageToImageSettings,
)
from airunner.components.art.data.metadata_settings import MetadataSettings
from airunner.components.art.data.outpaint_settings import OutpaintSettings
from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.enums import GeneratorSection, SignalCode
from PySide6.QtCore import QPoint
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.components.art.data.ai_models import AIModels
from airunner.enums import ImagePreset, QualityEffects, Scheduler, SignalCode
from airunner.utils.image.convert_binary_to_image import (
    convert_binary_to_image,
)


class CanvasAPIService(APIServiceBase):
    def recenter_grid(self):
        self.emit_signal(SignalCode.RECENTER_GRID_SIGNAL)

    def toggle_grid(self, val):
        self.emit_signal(SignalCode.TOGGLE_GRID, {"show_grid": val})

    def toggle_grid_snap(self, val):
        self.emit_signal(SignalCode.TOGGLE_GRID_SNAP, {"snap_to_grid": val})

    def generate_mask(self):
        self.emit_signal(SignalCode.GENERATE_MASK)

    def mask_response(self, mask):
        self.emit_signal(
            SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL, {"mask": mask}
        )

    def image_updated(self):
        self.emit_signal(SignalCode.CANVAS_IMAGE_UPDATED_SIGNAL)

    def update_current_layer(self, point: QPoint):
        self.emit_signal(
            SignalCode.LAYER_UPDATE_CURRENT_SIGNAL,
            {"pivot_point_x": point.x(), "pivot_point_y": point.y()},
        )

    def mask_updated(self):
        self.emit_signal(SignalCode.MASK_UPDATED)

    def brush_color_changed(self, color):
        self.emit_signal(
            SignalCode.BRUSH_COLOR_CHANGED_SIGNAL, {"color": color}
        )

    def image_from_path(self, path):
        self.emit_signal(
            SignalCode.CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL, {"image_path": path}
        )

    def new_document(self):
        self.clear()

    def clear(self):
        self.emit_signal(SignalCode.CANVAS_CLEAR, {})

    def undo(self):
        self.emit_signal(SignalCode.UNDO_SIGNAL)

    def redo(self):
        self.emit_signal(SignalCode.REDO_SIGNAL)

    def import_image(self):
        self.emit_signal(SignalCode.CANVAS_IMPORT_IMAGE_SIGNAL)

    def export_image(self):
        self.emit_signal(SignalCode.CANVAS_EXPORT_IMAGE_SIGNAL)

    def paste_image(self):
        self.emit_signal(SignalCode.CANVAS_PASTE_IMAGE_SIGNAL)

    def copy_image(self):
        self.emit_signal(SignalCode.CANVAS_COPY_IMAGE_SIGNAL)

    def cut_image(self):
        self.emit_signal(SignalCode.CANVAS_CUT_IMAGE_SIGNAL)

    def rotate_image_90_clockwise(self):
        self.emit_signal(SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL)

    def rotate_image_90_counterclockwise(self):
        self.emit_signal(SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL)

    def mask_layer_toggled(self):
        self.emit_signal(SignalCode.MASK_LAYER_TOGGLED)

    def show_layers(self):
        self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL)

    def layer_opacity_changed(self, value):
        self.emit_signal(SignalCode.LAYER_OPACITY_CHANGED_SIGNAL, value)

    def toggle_tool(self, tool, active):
        self.emit_signal(
            SignalCode.TOGGLE_TOOL, {"tool": tool, "active": active}
        )

    def tool_changed(self, tool, active):
        self.emit_signal(
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL,
            {"tool": tool, "active": active},
        )

    def do_draw(self, force=False):
        self.emit_signal(
            SignalCode.SCENE_DO_DRAW_SIGNAL, {"force_draw": force}
        )

    def clear_history(self):
        self.emit_signal(SignalCode.HISTORY_UPDATED, {"undo": 0, "redo": 0})

    def update_history(self, undo, redo):
        self.emit_signal(
            SignalCode.HISTORY_UPDATED, {"undo": undo, "redo": redo}
        )

    def update_cursor(self, event, apply_cursor):
        self.emit_signal(
            SignalCode.CANVAS_UPDATE_CURSOR,
            {"event": event, "apply_cursor": apply_cursor},
        )

    def zoom_level_changed(self):
        self.emit_signal(SignalCode.CANVAS_ZOOM_LEVEL_CHANGED)

    def layer_deleted(self, layer_id: int):
        self.emit_signal(
            SignalCode.LAYER_DELETED,
            {"layer_id": layer_id},
        )

    def layer_selection_changed(self, selected_layer_ids: List[int]):
        self.emit_signal(
            SignalCode.LAYER_SELECTION_CHANGED,
            {"selected_layer_ids": selected_layer_ids},
        )

    def update_grid_info(self, data: Dict):
        self.emit_signal(
            SignalCode.CANVAS_UPDATE_GRID_INFO,
            data,
        )

    def interrupt_image_generation(self):
        self.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL)

    def send_image_to_canvas(self, image_response: ImageResponse):
        self.cached_send_image_to_canvas = image_response
        self.emit_signal(
            SignalCode.SEND_IMAGE_TO_CANVAS_SIGNAL,
            {"image_response": image_response},
        )

    def create_image_request(self, **kwargs) -> ImageRequest:
        # Check if we have an inpaint model selected, prioritize that
        section = kwargs.get("section", None)

        controlnet_enabled = False
        pipeline_action = self.generator_settings.pipeline_action

        if pipeline_action == GeneratorSection.INPAINT.value:
            section = GeneratorSection.TXT2IMG
        if self.image_to_image_settings.enabled:
            section = GeneratorSection.IMG2IMG
        if (
            self.drawing_pad_settings.image is not None
            and self.outpaint_settings.enabled
        ):
            section = GeneratorSection.OUTPAINT

        controlnet_enabled = (
            self.controlnet_settings.enabled
            and self.controlnet_settings.image is not None
        )

        is_img2img = section is GeneratorSection.IMG2IMG
        is_outpaint = section is GeneratorSection.OUTPAINT
        is_inpaint = section is GeneratorSection.INPAINT

        generator_settings = self.generator_settings

        # Determine strength based on whether we are doing img2img or txt2img
        if controlnet_enabled:
            strength = self.controlnet_settings.strength
        elif is_inpaint or is_outpaint:
            strength = self.outpaint_settings.strength
        elif is_img2img:
            strength = self.image_to_image_settings.strength
        else:
            strength = generator_settings.strength

        model_path = ""
        model_id = generator_settings.model
        if model_id is not None:
            aimodel = AIModels.objects.get(model_id)
            if aimodel is not None:
                model_path = aimodel.path

        if model_path == "":
            if generator_settings.model is not None:
                aimodel = AIModels.objects.get(generator_settings.model)
            else:
                aimodel = AIModels.objects.first()

            if aimodel is not None:
                model_path = aimodel.path

        # Debug logging for model selection
        try:
            self.logger.debug(
                "do_generate model selection: version=%s pipeline_action=%s model_id=%s resolved_model_path=%s",
                generator_settings.version,
                pipeline_action,
                generator_settings.model,
                model_path,
            )
        except Exception:
            pass

        binary_image = None
        image = None
        mask = None
        scheduler = generator_settings.scheduler

        # Get image from ImageToImageSettings if img2img
        if is_img2img:
            binary_image = self.image_to_image_settings.image
        elif pipeline_action in (
            GeneratorSection.UPSCALER.value,
        ):
            binary_image = self.drawing_pad_settings.image
            scheduler = Scheduler.DDIM.value

        if binary_image is not None:
            image = convert_binary_to_image(binary_image)
            image = image.convert("RGB")

        controlnet_image = None
        if controlnet_enabled:
            controlnet_binary_image = self.controlnet_settings.image
            controlnet_image = convert_binary_to_image(controlnet_binary_image)
            controlnet_image = controlnet_image.convert("RGB")

        custom_path = self.generator_settings.custom_path
        if type(custom_path) is tuple:
            custom_path = None

        image_request = ImageRequest(
            prompt=self.generator_settings.prompt,
            negative_prompt=self.generator_settings.negative_prompt,
            second_prompt=self.generator_settings.second_prompt,
            second_negative_prompt=self.generator_settings.second_negative_prompt,
            crops_coords_top_left=generator_settings.crops_coords_top_left,
            negative_crops_coords_top_left=generator_settings.negative_crops_coords_top_left,
            pipeline_action=pipeline_action,
            generator_name=self.application_settings.current_image_generator,
            random_seed=generator_settings.random_seed,
            model_path=model_path,
            scheduler=scheduler,
            version=generator_settings.version,
            use_compel=generator_settings.use_compel,
            steps=generator_settings.steps,
            ddim_eta=generator_settings.ddim_eta,
            scale=generator_settings.scale / 100,
            seed=self.generator_settings.seed,
            strength=strength / 100,
            n_samples=generator_settings.n_samples,
            images_per_batch=generator_settings.images_per_batch,
            generate_infinite_images=generator_settings.generate_infinite_images,
            clip_skip=generator_settings.clip_skip,
            width=self.application_settings.working_width,
            height=self.application_settings.working_height,
            target_size=generator_settings.target_size,
            original_size=generator_settings.original_size,
            negative_target_size=generator_settings.negative_target_size,
            negative_original_size=generator_settings.negative_original_size,
            lora_scale=generator_settings.lora_scale,
            additional_prompts=kwargs.get("additional_prompts", []),
            callback=kwargs.get("callback", None),
            image_preset=ImagePreset(generator_settings.image_preset),
            quality_effects=(
                QualityEffects(generator_settings.quality_effects)
                if generator_settings.quality_effects != ""
                and generator_settings.quality_effects is not None
                else QualityEffects.STANDARD
            ),
            image=image,
            mask=mask,
            controlnet_conditioning_scale=self.controlnet_settings.conditioning_scale
            / 100.0,
            generator_section=section,
            custom_path=custom_path,
            controlnet_enabled=controlnet_enabled,
            controlnet=self.controlnet_settings.controlnet,
            nsfw_filter=self.application_settings.nsfw_filter,
            outpaint_mask_blur=self.outpaint_settings.mask_blur,
            controlnet_image=controlnet_image,
        )
        return image_request

    def input_image_changed(self, section: str, setting: str, value: Any):
        self.emit_signal(
            SignalCode.INPUT_IMAGE_SETTINGS_CHANGED,
            {
                "section": section,
                "setting": setting,
                "value": value,
                "image_request": self.create_image_request(),
            },
        )

    def update_image_positions(self):
        self.emit_signal(SignalCode.CANVAS_UPDATE_IMAGE_POSITIONS)

    def create_new_layer(self, **kwargs) -> CanvasLayer:
        self.begin_layer_operation("create")
        layer = CanvasLayer.objects.create(**kwargs)
        data = {"layer_id": layer.id}
        DrawingPadSettings.objects.create(**data)
        ControlnetSettings.objects.create(**data)
        ImageToImageSettings.objects.create(**data)
        OutpaintSettings.objects.create(**data)
        BrushSettings.objects.create(**data)
        MetadataSettings.objects.create(**data)
        if not layer:
            self.cancel_layer_operation("create")
            return
        self.commit_layer_operation("create", [layer.id])
        return layer

    def begin_layer_operation(
        self, action: str, layer_ids: list[int] | None = None
    ):
        self.emit_signal(
            SignalCode.LAYER_OPERATION_BEGIN,
            {"action": action, "layer_ids": layer_ids or []},
        )

    def commit_layer_operation(
        self, action: str, layer_ids: list[int] | None = None
    ):
        self.emit_signal(
            SignalCode.LAYER_OPERATION_COMMIT,
            {"action": action, "layer_ids": layer_ids or []},
        )

    def cancel_layer_operation(self, action: str):
        self.emit_signal(
            SignalCode.LAYER_OPERATION_CANCEL,
            {"action": action},
        )
