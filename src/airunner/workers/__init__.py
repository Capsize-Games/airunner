__all__ = [
    "AgentWorker",
    "AudioCaptureWorker",
    "AudioProcessorWorker",
    "DirectoryWatcher",
    "LLMGenerateWorker",
    "LLMResponseWorker",
    "MaskGeneratorWorker",
    "ModelScannerWorker",
    "SDWorker",
    "TTSGeneratorWorker",
    "TTSVocalizerWorker",
    "WatchStateWorker",
    "CivitAIDownloadWorker",
    "DownloadWorker",
    "Worker",
]


def __getattr__(name):
    if name == "AgentWorker":
        from .agent_worker import AgentWorker

        return AgentWorker
    elif name == "AudioCaptureWorker":
        from .audio_capture_worker import AudioCaptureWorker

        return AudioCaptureWorker
    elif name == "AudioProcessorWorker":
        from .audio_processor_worker import AudioProcessorWorker

        return AudioProcessorWorker
    elif name == "DirectoryWatcher":
        from .directory_watcher import DirectoryWatcher

        return DirectoryWatcher
    elif name == "LLMGenerateWorker":
        from .llm_generate_worker import LLMGenerateWorker

        return LLMGenerateWorker
    elif name == "LLMResponseWorker":
        from .llm_response_worker import LLMResponseWorker

        return LLMResponseWorker
    elif name == "MaskGeneratorWorker":
        from .mask_generator_worker import MaskGeneratorWorker

        return MaskGeneratorWorker
    elif name == "ModelScannerWorker":
        from .model_scanner_worker import ModelScannerWorker

        return ModelScannerWorker
    elif name == "SDWorker":
        from .sd_worker import SDWorker

        return SDWorker
    elif name == "TTSGeneratorWorker":
        from .tts_generator_worker import TTSGeneratorWorker

        return TTSGeneratorWorker
    elif name == "TTSVocalizerWorker":
        from .tts_vocalizer_worker import TTSVocalizerWorker

        return TTSVocalizerWorker
    elif name == "WatchStateWorker":
        from .watch_state_worker import WatchStateWorker

        return WatchStateWorker
    elif name == "CivitAIDownloadWorker":
        from .civit_ai_download_worker import CivitAIDownloadWorker

        return CivitAIDownloadWorker
    elif name == "DownloadWorker":
        from .download_worker import DownloadWorker

        return DownloadWorker
    elif name == "Worker":
        from .worker import Worker

        return Worker
    raise AttributeError(f"module {__name__} has no attribute {name}")
