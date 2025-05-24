from airunner.api.llm_services import LLMAPIService
from airunner.api.art_services import ARTAPIService
from airunner.api.tts_services import TTSAPIService
from airunner.api.stt_services import STTAPIService
from airunner.api.video_services import VideoAPIService
from airunner.api.nodegraph_services import NodegraphAPIService
from airunner.utils.audio.sound_device_manager import SoundDeviceManager
from airunner.api.image_filter_services import ImageFilterAPIServices
from airunner.api.embedding_services import EmbeddingAPIServices
from airunner.api.lora_services import LoraAPIServices
from airunner.api.canvas_services import CanvasAPIService
from airunner.api.chatbot_services import ChatbotAPIService


class APIManager:
    """
    Manages all API services and dispatching for AI Runner.
    This class is decoupled from the App lifecycle and GUI logic.
    """

    def __init__(self, emit_signal):
        if emit_signal is None:

            def emit_signal(*args, **kwargs):
                # No-op fallback for legacy/worker code
                pass

            self._emit_signal = emit_signal
        else:
            self._emit_signal = emit_signal
        self.llm = LLMAPIService(emit_signal=self._emit_signal)
        self.art = ARTAPIService(emit_signal=self._emit_signal)
        self.image_filter = ImageFilterAPIServices(
            emit_signal=self._emit_signal
        )
        self.embedding = EmbeddingAPIServices(emit_signal=self._emit_signal)
        self.lora = LoraAPIServices(emit_signal=self._emit_signal)
        self.canvas = CanvasAPIService(emit_signal=self._emit_signal)
        self.chatbot = ChatbotAPIService(emit_signal=self._emit_signal)
        self.tts = TTSAPIService(emit_signal=self._emit_signal)
        self.stt = STTAPIService(emit_signal=self._emit_signal)
        self.video = VideoAPIService(emit_signal=self._emit_signal)
        self.nodegraph = NodegraphAPIService(emit_signal=self._emit_signal)
        self.sounddevice_manager = SoundDeviceManager()

    @property
    def emit_signal(self):
        return self._emit_signal
