from PySide6.QtCore import QThread

from airunner.enums import WorkerType
from airunner.workers.audio_processor_worker import AudioProcessorWorker
from airunner.workers.llm_generate_worker import LLMGenerateWorker
from airunner.workers.sd_worker import SDWorker
from airunner.workers.tts_generator_worker import TTSGeneratorWorker
from airunner.workers.tts_vocalizer_worker import TTSVocalizerWorker
from airunner.workers.audio_capture_worker import AudioCaptureWorker
from airunner.workers.agent_worker import AgentWorker
from airunner.workers.latents_worker import LatentsWorker
from airunner.workers.mask_generator_worker import MaskGeneratorWorker
from airunner.workers.model_scanner_worker import ModelScannerWorker

WORKERS = []
THREADS = []


def create_worker(worker_class_, **kwargs):
    if worker_class_ is WorkerType.LLMGenerateWorker:
        worker_class_ = LLMGenerateWorker
    elif worker_class_ is WorkerType.SDWorker:
        worker_class_ = SDWorker
    elif worker_class_ is WorkerType.TTSGeneratorWorker:
        worker_class_ = TTSGeneratorWorker
    elif worker_class_ is WorkerType.TTSVocalizerWorker:
        worker_class_ = TTSVocalizerWorker
    elif worker_class_ is WorkerType.AudioCaptureWorker:
        worker_class_ = AudioCaptureWorker
    elif worker_class_ is WorkerType.AudioProcessorWorker:
        worker_class_ = AudioProcessorWorker
    elif worker_class_ is WorkerType.AgentWorker:
        worker_class_ = AgentWorker
    elif worker_class_ is WorkerType.LatentsWorker:
        worker_class_ = LatentsWorker
    elif worker_class_ is WorkerType.MaskGeneratorWorker:
        worker_class_ = MaskGeneratorWorker
    elif worker_class_ is WorkerType.ModelScannerWorker:
        worker_class_ = ModelScannerWorker

    prefix = worker_class_.__name__
    worker = worker_class_(prefix=prefix, **kwargs)
    worker_thread = QThread()
    worker.moveToThread(worker_thread)
    worker.finished.connect(worker_thread.quit)
    worker_thread.started.connect(worker.start)
    worker_thread.start()
    WORKERS.append(worker)
    THREADS.append(worker_thread)
    return worker
