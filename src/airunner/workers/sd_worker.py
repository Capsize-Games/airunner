import torch
from airunner.enums import QueueType, SignalCode, ModelType, ModelStatus
from airunner.workers.worker import Worker
torch.backends.cuda.matmul.allow_tf32 = True


class SDWorker(Worker):
    queue_type = QueueType.GET_LAST_ITEM

    def __init__(self, prefix="SDWorker"):
        self.signals = [
            (SignalCode.RESET_APPLIED_MEMORY_SETTINGS, self.on_reset_applied_memory_settings),
            (SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL, self.unload_safety_checker),
            (SignalCode.SD_CANCEL_SIGNAL, self.on_sd_cancel_signal),
            (SignalCode.SD_MOVE_TO_CPU_SIGNAL, self.on_move_to_cpu),
            (SignalCode.START_AUTO_IMAGE_GENERATION_SIGNAL, self.on_start_auto_image_generation_signal),
            (SignalCode.STOP_AUTO_IMAGE_GENERATION_SIGNAL, self.on_stop_auto_image_generation_signal),
            (SignalCode.DO_GENERATE_SIGNAL, self.on_do_generate_signal),
            (SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL, self.on_interrupt_image_generation_signal),
            (SignalCode.CHANGE_SCHEDULER_SIGNAL, self.on_change_scheduler_signal),
            (SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self.on_model_status_changed_signal),
            (SignalCode.SD_TOKENIZER_LOAD_SIGNAL, self.on_tokenizer_load_signal),
            (SignalCode.SD_TOKENIZER_UNLOAD_SIGNAL, self.on_tokenizer_unload_signal),
            (SignalCode.SD_LOAD_SIGNAL, self.on_load_stablediffusion_signal),
            (SignalCode.SD_UNLOAD_SIGNAL, self.on_unload_stablediffusion_signal),
            (SignalCode.CONTROLNET_LOAD_SIGNAL, self.on_load_controlnet_signal),
            (SignalCode.CONTROLNET_UNLOAD_SIGNAL, self.on_unload_controlnet_signal),
            (SignalCode.CONTROLNET_LOAD_MODEL_SIGNAL, self.on_controlnet_load_model_signal),
            (SignalCode.CONTROLNET_UNLOAD_MODEL_SIGNAL, self.on_unload_controlnet_model_signal),
            (SignalCode.CONTROLNET_PROCESSOR_LOAD_SIGNAL, self.on_controlnet_load_processor_signal),
            (SignalCode.CONTROLNET_PROCESSOR_UNLOAD_SIGNAL, self.on_controlnet_unload_processor_signal),
            (SignalCode.SCHEDULER_LOAD_SIGNAL, self.on_scheduler_load_signal),
            (SignalCode.SCHEDULER_UNLOAD_SIGNAL, self.on_scheduler_unload_signal),
            (SignalCode.LORA_UPDATE_SIGNAL, self.on_update_lora_signal),
            (SignalCode.LORA_ADD_SIGNAL, self.on_add_lora_signal),
            (SignalCode.EMBEDDING_UPDATE_SIGNAL, self.update_embedding),
            (SignalCode.EMBEDDING_ADD_SIGNAL, self.add_embedding),
            (SignalCode.EMBEDDING_SCAN_SIGNAL, self.scan_for_embeddings),
            (SignalCode.EMBEDDING_DELETE_MISSING_SIGNAL, self.delete_missing_embeddings),
            (SignalCode.EMBEDDING_GET_ALL_SIGNAL, self.get_embeddings),
            (SignalCode.SAFETY_CHECKER_MODEL_LOAD_SIGNAL, self.on_safety_checker_model_load_signal),
            (SignalCode.SAFETY_CHECKER_MODEL_UNLOAD_SIGNAL, self.on_safety_checker_model_unload_signal),
            (SignalCode.FEATURE_EXTRACTOR_LOAD_SIGNAL, self.on_feature_extractor_load_signal),
            (SignalCode.FEATURE_EXTRACTOR_UNLOAD_SIGNAL, self.on_feature_extractor_unload_signal),
            (SignalCode.SAFETY_CHECKER_LOAD_SIGNAL, self.on_safety_checker_load_signal),
        ]
        self.sd = None
        super().__init__(prefix=prefix)

    def on_safety_checker_model_load_signal(self, message):
        if self.sd:
            self.sd.on_safety_checker_model_load_signal(message)

    def on_safety_checker_model_unload_signal(self, message):
        if self.sd:
            self.sd.on_safety_checker_model_unload_signal(message)

    def on_feature_extractor_load_signal(self, message):
        if self.sd:
            self.sd.on_feature_extractor_load_signal(message)

    def on_feature_extractor_unload_signal(self, message):
        if self.sd:
            self.sd.on_feature_extractor_unload_signal(message)

    def on_safety_checker_load_signal(self, message):
        if self.sd:
            self.sd.on_safety_checker_load_signal(message)

    def update_embedding(self, message):
        if self.sd:
            self.sd.update_embedding(message)

    def add_embedding(self, message):
        if self.sd:
            self.sd.add_embedding(message)

    def scan_for_embeddings(self, message):
        if self.sd:
            self.sd.scan_for_embeddings(message)

    def delete_missing_embeddings(self, message):
        if self.sd:
            self.sd.delete_missing_embeddings(message)

    def get_embeddings(self, message):
        if self.sd:
            self.sd.get_embeddings(message)

    def on_update_lora_signal(self, message):
        if self.sd:
            self.sd.on_update_lora_signal(message)

    def on_add_lora_signal(self, message):
        if self.sd:
            self.sd.on_add_lora_signal(message)

    def on_scheduler_load_signal(self, message):
        if self.sd:
            self.sd.on_scheduler_load_signal(message)

    def on_scheduler_unload_signal(self, message):
        if self.sd:
            self.sd.on_scheduler_unload_signal(message)

    def on_controlnet_load_model_signal(self, message: dict):
        if self.sd:
            self.sd.on_controlnet_load_model_signal(message)

    def on_controlnet_unload_model_signal(self, message: dict):
        if self.sd:
            self.sd.on_controlnet_unload_model_signal(message)

    def on_controlnet_load_processor_signal(self, message: dict):
        if self.sd:
            self.sd.on_controlnet_load_processor_signal(message)

    def on_controlnet_unload_processor_signal(self, message: dict):
        if self.sd:
            self.sd.on_controlnet_unload_processor_signal(message)

    def on_load_controlnet_signal(self, message: dict):
        if self.sd:
            self.sd.on_load_controlnet_signal(message)

    def on_unload_controlnet_signal(self, message: dict):
        if self.sd:
            self.sd.on_unload_controlnet_signal(message)

    def on_unload_controlnet_model_signal(self, message: dict):
        if self.sd:
            self.sd.on_unload_controlnet_model_signal(message)

    def on_load_stablediffusion_signal(self, data: dict = None):
        if self.sd:
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.SD,
                    "status": ModelStatus.LOADING,
                    "path": ""
                }
            )
            self.sd.load_stable_diffusion_model()

    def on_unload_stablediffusion_signal(self, data: dict = None):
        if self.sd:
            self.sd.on_unload_stablediffusion_signal(data)

    def on_tokenizer_load_signal(self, data: dict = None):
        if self.sd:
            self.sd.on_tokenizer_load_signal(data)

    def on_tokenizer_unload_signal(self, data: dict = None):
        if self.sd:
            self.sd.on_tokenizer_unload_signal(data)

    def start_worker_thread(self):
        if self.settings["sd_enabled"]:
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.SD,
                    "status": ModelStatus.LOADING,
                    "path": ""
                }
            )
        from airunner.aihandler.stablediffusion.sd_handler import SDHandler
        self.sd = SDHandler()

    def handle_message(self, message):
        if self.sd:
            self.sd.run()

    def on_reset_applied_memory_settings(self, _data: dict):
        if self.sd:
            self.sd.reset_applied_memory_settings()

    def unload_safety_checker(self, _data: dict):
        if self.sd:
            self.sd.unload_safety_checker()

    def on_sd_cancel_signal(self, _data: dict = None):
        print("on_sd_cancel_signal")

    def on_move_to_cpu(self, _data: dict = None):
        if self.sd:
            self.sd.move_pipe_to_cpu()

    def on_start_auto_image_generation_signal(self, _message: dict):
        # self.sd_mode = SDMode.DRAWING
        # self.generate()
        pass

    def on_stop_auto_image_generation_signal(self, _message: dict = None):
        #self.sd_mode = SDMode.STANDARD
        pass

    def on_do_generate_signal(self, message: dict):
        if self.sd:
            self.sd.handle_generate_signal(message)

    def on_interrupt_image_generation_signal(self, _message: dict = None):
        if self.sd:
            self.sd.interrupt_image_generation_signal()

    def on_change_scheduler_signal(self, data: dict):
        if self.sd:
            self.sd.load_scheduler(force_scheduler_name=data["scheduler"])

    def on_model_status_changed_signal(self, message: dict):
        if self.sd:
            self.sd.model_status_changed(message)
