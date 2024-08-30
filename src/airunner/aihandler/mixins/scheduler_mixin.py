import os
import threading
import time
from queue import Queue

import diffusers
from airunner.enums import (
    Scheduler,
    ModelStatus, ModelType, HandlerState
)
from airunner.settings import (
    SCHEDULER_CLASSES,
    DEFAULT_SCHEDULER
)


class SchedulerMixin:
    def __init__(self):
        self.scheduler_name: str = DEFAULT_SCHEDULER
        self.schedulers: dict = SCHEDULER_CLASSES
        self.registered_schedulers: dict = {}
        self.current_scheduler_name: str = ""
        self.do_change_scheduler: bool = False
        self.scheduler = None
        self.__scheduler_status = ModelStatus.UNLOADED
        self.__scheduler_queue = Queue()
        self._controlnet_queue_watcher_thread = threading.Thread(target=self.__scheduler_watch_queue)
        self._controlnet_queue_watcher_thread.start()

    @property
    def __scheduler_ready(self):
        return (
            self.current_state == HandlerState.READY and
            self.__scheduler_status == ModelStatus.LOADED
        )

    def __scheduler_watch_queue(self):
        while True:
            if self.current_state == HandlerState.READY and not self.__scheduler_queue.empty():
                action = self.__scheduler_queue.get()
                action()
                self.__scheduler_queue.task_done()
            time.sleep(1)

    def __scheduler_can_run_action(self, action):
        if not self.__scheduler_ready:
            if action not in self.__scheduler_queue.queue:
                self.__scheduler_queue.put(action)
            return False
        return True

    @property
    def scheduler_section(self):
        return self.sd_request.section

    def on_scheduler_load_signal(self, _data: dict = None):
        self.load_scheduler()

    def on_scheduler_unload_signal(self, _data: dict = None):
        self.unload_scheduler()

    def clear_scheduler(self):
        self.logger.debug("Clearing scheduler")
        self.scheduler_name = ""
        self.current_scheduler_name = ""
        self.do_change_scheduler = True
        self.scheduler = None

    @property
    def __scheduler_path(self) -> str:
        return os.path.expanduser(
            os.path.join(
                self.settings["path_settings"]["base_path"],
                "art/models",
                self.settings["generator_settings"]["version"],
                "txt2img",
                "scheduler",
                "scheduler_config.json"
            )
        )

    def __change_scheduler_model_status(self, status):
        self.__scheduler_status = status
        self.change_model_status(ModelType.SCHEDULER, status, self.__scheduler_path)

    def load_scheduler(self, force_scheduler_name=None, config=None):
        if self.__scheduler_status is ModelStatus.LOADING:
            return
        scheduler_name = force_scheduler_name if force_scheduler_name else self.settings["generator_settings"]["scheduler"]
        kwargs = {
            "subfolder": "scheduler",
            "local_files_only": True,
        }
        for scheduler in self.settings["schedulers"]:
            if scheduler["display_name"] == scheduler_name:
                scheduler_name = Scheduler[scheduler["name"]]
                scheduler_class_name = SCHEDULER_CLASSES[scheduler_name]
                scheduler_class = getattr(diffusers, scheduler_class_name)
                try:
                    self.__change_scheduler_model_status(ModelStatus.LOADING)
                    self.scheduler = scheduler_class.from_pretrained(
                        self.__scheduler_path,
                        **kwargs
                    )
                    self.__change_scheduler_model_status(ModelStatus.READY)
                    self.current_scheduler_name = scheduler_name
                    self.logger.debug(f"Loaded scheduler {scheduler_name}")
                except Exception as e:
                    self.logger.error(f"Failed to load scheduler {scheduler_name}: {e}")
                    self.__change_scheduler_model_status(ModelStatus.FAILED)

                self.apply_scheduler_to_pipe()

                return scheduler

    def unload_scheduler(self):
        self.logger.debug("Unloading scheduler")
        self.scheduler_name = ""
        self.current_scheduler_name = ""
        self.do_change_scheduler = True
        self.scheduler = None
        self.__change_scheduler_model_status(ModelStatus.UNLOADED)

    def change_scheduler(self):
        if not self.do_change_scheduler or not self.pipe:
            return

        if self.sd_request.generator_settings.model and self.sd_request.generator_settings.model != "":
            config = self.scheduler.config if self.scheduler else None
            self.load_scheduler(config=config)
            self.do_change_scheduler = False
        else:
            self.logger.warning("Unable to change scheduler, model_path is not set")

    def prepare_scheduler(self):
        scheduler_name = self.sd_request.generator_settings.scheduler
        if self.scheduler_name != scheduler_name:
            self.logger.debug("Preparing scheduler")
            self.scheduler_name = scheduler_name
            self.do_change_scheduler = True
        else:
            self.do_change_scheduler = False

    def apply_scheduler_to_pipe(self):
        if not self.__scheduler_can_run_action(self.apply_scheduler_to_pipe):
            if self.pipe:
                self.pipe.scheduler = self.scheduler
                self.__change_scheduler_model_status(ModelStatus.LOADED)

    def remove_scheduler_from_pipe(self):
        if self.__scheduler_can_run_action(self.remove_scheduler_from_pipe):
            if self.pipe:
                self.pipe.scheduler = None
                self.__change_scheduler_model_status(ModelStatus.READY)
