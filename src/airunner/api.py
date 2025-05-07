from typing import Optional, Dict, List, Any

from NodeGraphQt import NodesPaletteWidget
from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import QObject, QPoint

from airunner.app import App
from airunner.data.models.conversation import Conversation
from airunner.data.models.workflow import Workflow
from airunner.gui.widgets.nodegraph.custom_node_graph import CustomNodeGraph
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.enums import (
    EngineResponseCode,
    GeneratorSection,
    ModelStatus,
    ModelType,
    SignalCode,
    LLMActionType,
)
from airunner.setup_database import setup_database
from airunner.utils.application.create_worker import create_worker
from airunner.gui.utils.ui_dispatcher import render_ui_from_spec
from airunner.handlers.stablediffusion.image_response import ImageResponse
from airunner.utils.application.ui_loader import (
    load_ui_file,
    load_ui_from_string,
)
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.utils.application.mediator_mixin import MediatorMixin


class APIServiceBase(MediatorMixin, SettingsMixin, QObject):
    def __init__(self, emit_signal):
        super().__init__()


class ImageFilterAPIServices(APIServiceBase):
    def cancel(self):
        self.emit_signal(SignalCode.CANVAS_CANCEL_FILTER_SIGNAL)

    def apply(self, filter_object: Any):
        self.emit_signal(
            SignalCode.CANVAS_APPLY_FILTER_SIGNAL,
            {"filter_object": filter_object},
        )

    def preview(self, filter_object: Any):
        self.emit_signal(
            SignalCode.CANVAS_PREVIEW_FILTER_SIGNAL,
            {"filter_object": filter_object},
        )


class EmbeddingAPIServices(APIServiceBase):
    def delete(self, embedding_widget):
        """
        Emit a signal to delete an embedding widget.
        :param embedding_widget: The widget to be deleted.
        """
        self.emit_signal(
            SignalCode.EMBEDDING_DELETE_SIGNAL,
            {"embedding_widget": embedding_widget},
        )

    def status_changed(self):
        self.emit_signal(SignalCode.EMBEDDING_STATUS_CHANGED)

    def update(self):
        self.emit_signal(SignalCode.EMBEDDING_UPDATE_SIGNAL)

    def get_all_results(self, embeddings: List):
        self.emit_signal(
            SignalCode.EMBEDDING_GET_ALL_RESULTS_SIGNAL,
            {"embeddings": embeddings},
        )


class LoraAPIServices(APIServiceBase):
    def update(self):
        self.emit_signal(SignalCode.LORA_UPDATE_SIGNAL)

    def status_changed(self):
        self.emit_signal(SignalCode.LORA_STATUS_CHANGED)

    def delete(self, lora_widget):
        """
        Emit a signal to delete a LoRA widget.
        :param lora_widget: The widget to be deleted.
        """
        self.emit_signal(
            SignalCode.LORA_DELETE_SIGNAL,
            {"lora_widget": lora_widget},
        )


class NodegraphAPIService(APIServiceBase):
    def node_executed(
        self, node_id: str, result: str, data: Optional[Dict] = None
    ):
        self.emit_signal(
            SignalCode.NODE_EXECUTION_COMPLETED_SIGNAL,
            {
                "node_id": node_id,
                "result": result,
                "output_data": data or {},
            },
        )

    def run_workflow(self, graph: CustomNodeGraph):
        self.emit_signal(SignalCode.RUN_WORKFLOW_SIGNAL, {"graph": self.graph})

    def pause_workflow(self, graph: CustomNodeGraph):
        self.emit_signal(SignalCode.PAUSE_WORKFLOW_SIGNAL, {"graph": graph})

    def stop_workflow(self, graph: CustomNodeGraph):
        self.emit_signal(SignalCode.STOP_WORKFLOW_SIGNAL, {"graph": graph})

    def register_graph(
        self,
        graph: CustomNodeGraph,
        nodes_palette: NodesPaletteWidget,
        finalize: callable,
    ):
        self.emit_signal(
            SignalCode.REGISTER_GRAPH_SIGNAL,
            {
                "graph": graph,
                "nodes_palette": nodes_palette,
                "callback": finalize,
            },
        )

    def load_workflow(self, workflow: Workflow, callback: callable):
        self.emit_signal(
            SignalCode.WORKFLOW_LOAD_SIGNAL,
            {
                "workflow": workflow,
                "callback": callback,
            },
        )

    def clear_workflow(self, callback: callable):
        self.emit_signal(
            SignalCode.CLEAR_WORKFLOW_SIGNAL,
            {"callback": callback},
        )


class VideoAPIService(APIServiceBase):
    def generate(self, data: Dict):
        self.emit_signal(SignalCode.VIDEO_GENERATE_SIGNAL, data)

    def frame_update(self, frame):
        self.emit_signal(
            SignalCode.VIDEO_FRAME_UPDATE_SIGNAL, {"frame": frame}
        )

    def generation_complete(self, path: str):
        self.emit_signal(
            SignalCode.VIDEO_GENERATED_SIGNAL,
            {"path": path},
        )

    def video_generate_step(self, percent, message: str):
        self.emit_signal(
            SignalCode.VIDEO_PROGRESS_SIGNAL,
            {"percent": percent, "message": message},
        )


class STTAPIService(APIServiceBase):
    def audio_processor_response(self, transcription: str):
        """
        Emit a signal with the audio processor response.
        :param transcription: The response from the audio processor.
        """
        self.emit_signal(
            SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
            {"transcription": transcription},
        )


class TTSAPIService(APIServiceBase):
    def toggle(self, enabled: bool):
        """
        Emit a signal to toggle TTS on or off.
        :param enabled: True to enable TTS, False to disable.
        """
        self.emit_signal(SignalCode.TOGGLE_TTS_SIGNAL, {"enabled": enabled})

    def add_to_stream(self, response: str):
        """
        Emit a signal to add text to the TTS stream.
        :param response: The text to add to the stream.
        """
        self.emit_signal(
            SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL,
            {"message": response},
        )

    def disable(self):
        """
        Emit a signal to disable TTS.
        """
        self.emit_signal(SignalCode.TTS_DISABLE_SIGNAL, {})


class CanvasAPIService(APIServiceBase):
    def recenter_grid(self):
        """
        Emit a signal to recenter the grid.
        """
        self.emit_signal(SignalCode.RECENTER_GRID_SIGNAL)

    def toggle_grid(self, val: bool):
        self.emit_signal(SignalCode.TOGGLE_GRID, {"show_grid": val})

    def generate_mask(self):
        """
        Emit a signal to generate a mask.
        """
        self.emit_signal(SignalCode.GENERATE_MASK)

    def mask_response(self, mask):
        self.emit_signal(
            SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL, {"mask": mask}
        )

    def image_updated(self):
        """
        Emit a signal indicating that the canvas image has been updated.
        """
        self.emit_signal(SignalCode.CANVAS_IMAGE_UPDATED_SIGNAL)

    def update_current_layer(self, point: QPoint):
        self.emit_signal(
            SignalCode.LAYER_UPDATE_CURRENT_SIGNAL,
            {"pivot_point_x": point.x(), "pivot_point_y": point.y()},
        )

    def mask_updated(self):
        """
        Emit a signal indicating that the mask has been updated.
        """
        self.emit_signal(SignalCode.MASK_UPDATED)

    def brush_color_changed(self, color: str):
        """
        Emit a signal when the brush color is changed.
        :param color: The new color of the brush.
        """
        self.emit_signal(
            SignalCode.BRUSH_COLOR_CHANGED_SIGNAL, {"color": color}
        )

    def image_from_path(self, path: str):
        """
        Emit a signal to load an image from the given path.
        :param path: The path to the image file.
        """
        self.emit_signal(
            SignalCode.CANVAS_LOAD_IMAGE_FROM_PATH_SIGNAL,
            {"image_path": path},
        )

    def clear(self):
        """
        Emit a signal to clear the canvas.
        """
        self.emit_signal(SignalCode.CANVAS_CLEAR, {})

    def undo(self):
        """
        Emit a signal to undo the last action on the canvas.
        """
        self.emit_signal(SignalCode.UNDO_SIGNAL)

    def redo(self):
        """
        Emit a signal to redo the last undone action on the canvas.
        """
        self.emit_signal(SignalCode.REDO_SIGNAL)

    def import_image(self):
        """
        Emit a signal to import an image into the canvas.
        """
        self.emit_signal(SignalCode.CANVAS_IMPORT_IMAGE_SIGNAL)

    def export_image(self):
        """
        Emit a signal to export the current canvas image.
        """
        self.emit_signal(SignalCode.CANVAS_EXPORT_IMAGE_SIGNAL)

    def paste_image(self):
        """
        Emit a signal to paste an image into the canvas.
        """
        self.emit_signal(SignalCode.CANVAS_PASTE_IMAGE_SIGNAL)

    def copy_image(self):
        """
        Emit a signal to copy the current canvas image.
        """
        self.emit_signal(SignalCode.CANVAS_COPY_IMAGE_SIGNAL)

    def cut_image(self):
        """
        Emit a signal to cut the current canvas image.
        """
        self.emit_signal(SignalCode.CANVAS_CUT_IMAGE_SIGNAL)

    def rotate_image_90_clockwise(self):
        """
        Emit a signal to rotate the current canvas image by 90 degrees.
        """
        self.emit_signal(SignalCode.CANVAS_ROTATE_90_CLOCKWISE_SIGNAL)

    def rotate_image_90_counterclockwise(self):
        """
        Emit a signal to rotate the current canvas image by 90 degrees counterclockwise.
        """
        self.emit_signal(SignalCode.CANVAS_ROTATE_90_COUNTER_CLOCKWISE_SIGNAL)

    def mask_layer_toggled(self):
        """
        Emit a signal to toggle the mask layer.
        """
        self.emit_signal(SignalCode.MASK_LAYER_TOGGLED)

    def show_layers(self):
        self.emit_signal(SignalCode.LAYERS_SHOW_SIGNAL)

    def layer_opacity_changed(self, value: int):
        self.emit_signal(SignalCode.LAYER_OPACITY_CHANGED_SIGNAL, value)

    def toggle_tool(self, tool: str, active: bool):
        self.emit_signal(
            SignalCode.TOGGLE_TOOL,
            {"tool": tool, "active": active},
        )

    def tool_changed(self, tool: str, active: bool):
        self.emit_signal(
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL,
            {"tool": tool, "active": active},
        )

    def do_draw(self, force: bool = False):
        self.emit_signal(
            SignalCode.SCENE_DO_DRAW_SIGNAL, {"force_draw": force}
        )

    def clear_history(self):
        self.emit_signal(SignalCode.HISTORY_UPDATED, {"undo": 0, "redo": 0})

    def update_history(self, undo: int, redo: int):
        """
        Emit a signal to update the history of the canvas.
        :param undo: The number of undo actions available.
        :param redo: The number of redo actions available.
        """
        self.emit_signal(
            SignalCode.HISTORY_UPDATED,
            {"undo": undo, "redo": redo},
        )

    def update_cursor(self, event: Any, apply_cursor: bool):
        self.emit_signal(
            SignalCode.CANVAS_UPDATE_CURSOR,
            {"event": event, "apply_cursor": apply_cursor},
        )

    def zoom_level_changed(self):
        self.emit_signal(SignalCode.CANVAS_ZOOM_LEVEL_CHANGED)

    def interrupt_image_generation(self):
        self.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL)

    def send_image_to_canvas(self, image_response: ImageResponse):
        self.emit_signal(
            SignalCode.SEND_IMAGE_TO_CANVAS_SIGNAL,
            {"image_response": image_response},
        )

    def input_image_changed(self, section: str, setting: str, value: Any):
        self.emit_signal(
            SignalCode.INPUT_IMAGE_SETTINGS_CHANGED,
            {"section": section, "setting": setting, "value": value},
        )

    def update_image_positions(self):
        self.emit_signal(SignalCode.CANVAS_UPDATE_IMAGE_POSITIONS)


class ARTAPIService(APIServiceBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.canvas = CanvasAPIService(emit_signal=self.emit_signal)
        self.embeddings = EmbeddingAPIServices(emit_signal=self.emit_signal)
        self.lora = LoraAPIServices(emit_signal=self.emit_signal)
        self.image_filter = ImageFilterAPIServices(
            emit_signal=self.emit_signal
        )

    def save_prompt(
        self,
        prompt: str,
        negative_prompt: str,
        secondary_prompt: str,
        secondary_negative_prompt: str,
    ):
        """
        Emit a signal to save the current prompt.
        :param prompt: The main prompt.
        :param negative_prompt: The negative prompt.
        :param secondary_prompt: The secondary prompt.
        :param secondary_negative_prompt: The secondary negative prompt.
        """
        self.emit_signal(
            SignalCode.SD_SAVE_PROMPT_SIGNAL,
            {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "secondary_prompt": secondary_prompt,
                "secondary_negative_prompt": secondary_negative_prompt,
            },
        )

    def load(self, saved_prompt: Optional[str] = None):
        self.emit_signal(
            SignalCode.SD_LOAD_PROMPT_SIGNAL, {"saved_prompt": saved_prompt}
        )

    def unload(self):
        self.emit_signal(SignalCode.SD_UNLOAD_SIGNAL)

    def model_changed(
        self,
        model: Optional[str],
        version: Optional[str] = None,
        pipeline: Optional[str] = None,
    ):
        data = {}
        if model is not None:
            data["model"] = model
        if version is not None:
            data["version"] = version
        if pipeline is not None:
            data["pipeline"] = pipeline
        self.emit_signal(SignalCode.SD_ART_MODEL_CHANGED, data)

    def load_safety_checker(self):
        self.emit_signal(SignalCode.SAFETY_CHECKER_LOAD_SIGNAL)

    def unload_safety_checker(self):
        self.emit_signal(SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL)

    def change_scheduler(self, val: str):
        self.emit_signal(
            SignalCode.CHANGE_SCHEDULER_SIGNAL, {"scheduler": val}
        )

    def lora_updated(self):
        """
        Emit a signal indicating that the LoRA has been updated.
        """
        self.emit_signal(SignalCode.LORA_UPDATED_SIGNAL, {})

    def embedding_updated(self):
        """
        Emit a signal indicating that the embedding has been updated.
        """
        self.emit_signal(SignalCode.EMBEDDING_UPDATED_SIGNAL, {})

    def final_progress_update(self, total: int):
        self.progress_update(total, total)

    def progress_update(self, step: int, total: int):
        """
        Emit a signal indicating the image generation progress.
        :param step: The current step in the progress.
        :param total: The total number of steps.
        """
        self.emit_signal(
            SignalCode.SD_PROGRESS_SIGNAL,
            {
                "step": step,
                "total": total,
            },
        )

    def pipeline_loaded(self, section: GeneratorSection):
        """
        Emit a signal indicating that the pipeline has been loaded.
        :param section: The section of the pipeline that has been loaded.
        """
        self.emit_signal(
            SignalCode.SD_PIPELINE_LOADED_SIGNAL,
            {"generator_section": section},
        )

    def generate_image_signal(self):
        self.emit_signal(SignalCode.SD_GENERATE_IMAGE_SIGNAL)

    def llm_image_generated(
        self,
        prompt: str,
        second_prompt: str,
        section: GeneratorSection,
        width: int,
        height: int,
    ):
        """
        Emit a signal indicating that an image has been generated by the LLM.
        :param prompt: The prompt used for image generation.
        :param second_prompt: The second prompt used for image generation.
        :param section: The section of the pipeline that generated the image.
        :param width: The width of the generated image.
        :param height: The height of the generated image.
        """
        self.emit_signal(
            SignalCode.LLM_IMAGE_PROMPT_GENERATED_SIGNAL,
            {
                "message": {
                    "prompt": prompt,
                    "second_prompt": second_prompt,
                    "type": section,
                    "width": width,
                    "height": height,
                }
            },
        )

    def stop_progress_bar(self):
        self.emit_signal(SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL)

    def clear_progress_bar(self):
        self.emit_signal(
            SignalCode.APPLICATION_STOP_SD_PROGRESS_BAR_SIGNAL,
            {"do_clear": True},
        )

    def missing_required_models(self, message: str):
        self.emit_signal(
            SignalCode.MISSING_REQUIRED_MODELS,
            {
                "title": "Model Not Found",
                "message": message,
            },
        )

    def send_request(
        self,
        image_request: Optional[ImageRequest] = None,
        data: Optional[Dict] = None,
    ):
        """ "
        Send a request to the image generator with the given request.
        :param image_request: Optional ImageRequest object.
        :return: None
        """
        data = data or {}
        image_request = data.get(
            "image_request", image_request or ImageRequest()
        )
        data.update({"image_request": image_request})
        self.emit_signal(SignalCode.DO_GENERATE_SIGNAL, data)

    def interrupt_generate(self):
        self.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL)

    def active_grid_area_updated(self):
        self.emit_signal(SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED)

    def update_generator_form_values(self):
        self.emit_signal(SignalCode.GENERATOR_FORM_UPDATE_VALUES_SIGNAL)

    def toggle_sd(self, enabled: bool, callback: callable, finalize: callable):
        self.emit_signal(
            SignalCode.TOGGLE_SD_SIGNAL,
            {
                "enabled": enabled,
                "callback": callback,
                "finalize": finalize,
            },
        )

    def load_non_sd(self, callback: callable):
        self.emit_signal(
            SignalCode.LOAD_NON_SD_MODELS,
            dict(callback=callable),
        )

    def unload_non_sd(self, callback: callable):
        self.emit_signal(
            SignalCode.UNLOAD_NON_SD_MODELS,
            dict(callback=callback),
        )


class ChatbotAPIService(APIServiceBase):
    def update_mood(self, mood: str):
        self.emit_signal(SignalCode.BOT_MOOD_UPDATED, {"mood": mood})


class LLMAPIService(APIServiceBase):
    def chatbot_changed(self):
        self.emit_signal(SignalCode.CHATBOT_CHANGED)

    def send_request(
        self,
        prompt: str,
        llm_request: Optional[LLMRequest] = None,
        action: LLMActionType = LLMActionType.CHAT,
        do_tts_reply: bool = True,
        node_id: Optional[str] = None,
    ):
        """
        Send a request to the LLM with the given prompt and action.

        :param prompt: The prompt to send to the LLM.
        :param llm_request: Optional LLMRequest object.
        :param action: The action type for the request.
        :param do_tts_reply: Whether to do text-to-speech reply.
        :return: None
        """
        llm_request = llm_request or LLMRequest.from_default()
        llm_request.do_tts_reply = do_tts_reply

        data = {
            "llm_request": True,
            "request_data": {
                "action": action,
                "prompt": prompt,
                "llm_request": llm_request,
                "do_tts_reply": do_tts_reply,
            },
        }
        if node_id is not None:
            data["node_id"] = node_id
        self.emit_signal(
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
            data,
        )

    def clear_history(self, **kwargs):
        """
        Emit a signal to clear the LLM history.
        """
        self.emit_signal(SignalCode.LLM_CLEAR_HISTORY_SIGNAL, kwargs)

    def converation_deleted(self, conversation_id: int):
        self.emit_signal(
            SignalCode.CONVERSATION_DELETED,
            {"conversation_id": conversation_id},
        )

    def model_changed(self, model_service: str):
        self.update_llm_generator_settings("model_service", model_service)
        self.emit_signal(
            SignalCode.LLM_MODEL_CHANGED,
            {
                "model_service": model_service,
            },
        )

    def reload_rag(self, target_files: Optional[List[str]] = None):
        self.emit_signal(
            SignalCode.RAG_RELOAD_INDEX_SIGNAL,
            {"target_files": target_files} if target_files else None,
        )

    def load_conversation(
        self, conversation_id: int, conversation: Conversation, chatbot_id: int
    ):
        self.emit_signal(
            SignalCode.LOAD_CONVERSATION,
            {
                "conversation_id": conversation_id,
                "conversation": conversation,
                "chatbot_id": chatbot_id,
            },
        )

    def interrupt(self):
        self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)

    def delete_messages_after_id(self, message_id: int):
        self.emit_signal(
            SignalCode.DELETE_MESSAGES_AFTER_ID,
            {"message_id": message_id},
        )


class API(App):
    def __init__(self, *args, **kwargs):
        self.llm = LLMAPIService(emit_signal=self.emit_signal)
        self.art = ARTAPIService(emit_signal=self.emit_signal)
        self.tts = TTSAPIService(emit_signal=self.emit_signal)
        self.stt = STTAPIService(emit_signal=self.emit_signal)
        self.video = VideoAPIService(emit_signal=self.emit_signal)
        self.nodegraph = NodegraphAPIService(emit_signal=self.emit_signal)

        # Extract the initialize_app flag and pass the rest to the parent App class
        self._initialize_app = kwargs.pop("initialize_app", True)
        initialize_gui = kwargs.pop("initialize_gui", True)
        self.signal_handlers = {
            SignalCode.SHOW_WINDOW_SIGNAL: self.show_hello_world_window,
            SignalCode.SHOW_DYNAMIC_UI_FROM_STRING_SIGNAL: self.show_dynamic_ui_from_string,
        }
        super().__init__(*args, initialize_gui=initialize_gui, **kwargs)
        self._initialize_model_scanner()

    def _initialize_model_scanner(self):
        from airunner.workers.model_scanner_worker import (
            ModelScannerWorker,
        )

        if self._initialize_app:
            setup_database()
            self.model_scanner_worker = create_worker(ModelScannerWorker)
            self.model_scanner_worker.add_to_queue("scan_for_models")

    def send_llm_text_streamed_signal(self, response: LLMResponse):
        """
        Send a TTS request with the given response."

        :param response: The LLMResponse object.
        :return: None
        """
        self.emit_signal(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL, {"response": response}
        )

    def show_hello_world_window(self):
        """
        Display a 'Hello, world!' popup window using the UI dispatcher.
        """
        spec = {
            "type": "window",
            "title": "Hello Window",
            "layout": "vertical",
            "widgets": [{"type": "label", "text": "Hello, world!"}],
        }
        dialog = QDialog(self.app.main_window)
        dialog.setWindowTitle(spec.get("title", "Untitled"))
        render_ui_from_spec(spec, dialog)
        dialog.exec()

    def show_dynamic_ui(self, ui_file_path: str):
        """
        Load and display a .ui file dynamically as a popup window.

        :param ui_file_path: Path to the .ui file.
        """
        dialog = QDialog(self.app.main_window)
        dialog.setWindowTitle("Dynamic UI")
        widget = load_ui_file(ui_file_path, dialog)
        layout = dialog.layout() or QVBoxLayout(dialog)
        layout.addWidget(widget)
        dialog.setLayout(layout)
        dialog.exec()

    def show_dynamic_ui_from_string(self, data: Dict):
        """
        Load and display a .ui file dynamically from a string as a popup window.

        :param ui_content: The content of the .ui file as a string.
        """
        ui_content = data.get("ui_content", "")

        class SignalHandler(QObject):
            def __init__(self, api: API):
                self.api = api
                super().__init__()

            def click_me_button(self):
                self.api.emit_signal(SignalCode.SHOW_WINDOW_SIGNAL)

        signal_handler = SignalHandler(api=self)
        dialog = QDialog(self.app.main_window)
        dialog.setWindowTitle("Dynamic UI with Signal")
        widget = load_ui_from_string(ui_content, dialog, signal_handler)
        layout = dialog.layout() or QVBoxLayout(dialog)
        layout.addWidget(widget)
        dialog.setLayout(layout)
        dialog.exec()

    def change_model_status(self, model: ModelType, status: ModelStatus):
        """
        Change the status of a model and emit a signal.
        :param model: The model type.
        :param status: The new status of the model.
        """
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {"model": model, "status": status},
        )

    def worker_response(self, code: EngineResponseCode, message: Dict):
        """
        Emit a signal indicating a response from the worker.
        :param code: The response code from the worker.
        :param message: The message from the worker.
        """
        self.emit_signal(
            SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL,
            {"code": code, "message": message},
        )

    def quit_application(self):
        """
        Emit a signal to quit the application.
        """
        self.emit_signal(SignalCode.QUIT_APPLICATION, {})

    def application_error(self, message: str):
        """
        Emit a signal indicating an application error.
        :param message: The error message.
        """
        self.emit_signal(
            SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
            {"message": message},
        )

    def application_status(self, message: str):
        """
        Emit a signal indicating application status.
        :param message: The status message.
        """
        self.emit_signal(
            SignalCode.APPLICATION_STATUS_INFO_SIGNAL,
            {"message": message},
        )

    def update_download_log(self, message: str):
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": message},
        )

    def set_download_progress(self, current: int, total: int):
        self.emit_signal(
            SignalCode.DOWNLOAD_PROGRESS,
            {"current": current, "total": total},
        )

    def clear_download_status(self):
        self.emit_signal(SignalCode.CLEAR_DOWNLOAD_STATUS_BAR)

    def set_download_status(self, message: str):
        self.emit_signal(
            SignalCode.SET_DOWNLOAD_STATUS_LABEL,
            {"message": message},
        )

    def download_complete(self):
        self.emit_signal(SignalCode.DOWNLOAD_COMPLETE)

    def clear_status_message(self):
        self.emit_signal(SignalCode.APPLICATION_CLEAR_STATUS_MESSAGE_SIGNAL)

    def main_window_loaded(self, main_window: Any):
        self.emit_signal(
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL,
            {"main_window": main_window},
        )

    def clear_prompts(self):
        self.emit_signal(SignalCode.CLEAR_PROMPTS)

    def keyboard_shortcuts_updated(self):
        self.emit_signal(SignalCode.KEYBOARD_SHORTCUTS_UPDATED)

    def reset_paths(self):
        self.emit_signal(SignalCode.APPLICATION_RESET_PATHS_SIGNAL)

    def application_settings_changed(
        self, setting_name: str, column_name: str, val: Any
    ):
        self.emit_signal(
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL,
            {
                "setting_name": setting_name,
                "column_name": column_name,
                "value": val,
            },
        )

    def widget_element_changed(self, element: str, value_name: str, val: Any):
        self.emit_signal(
            SignalCode.WIDGET_ELEMENT_CHANGED_SIGNAL,
            {
                "element": element,
                value_name: val,
            },
        )

    def delete_prompt(self, prompt_id: int):
        self.emit_signal(
            SignalCode.SD_ADDITIONAL_PROMPT_DELETE_SIGNAL,
            {"prompt_id": prompt_id},
        )
