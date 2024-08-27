import os
import diffusers
from airunner.settings import AVAILABLE_SCHEDULERS_BY_ACTION, BASE_PATH
from airunner.enums import (
    Scheduler,
    SignalCode,
    SchedulerAlgorithm, ModelStatus, ModelType
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
                BASE_PATH,
                "art/models",
                self.settings["generator_settings"]["version"],
                "txt2img",
                "scheduler",
                "scheduler_config.json"
            )
        )

    def load_scheduler(self, force_scheduler_name=None, config=None):
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
                    self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADING, self.__scheduler_path)
                    self.scheduler = scheduler_class.from_pretrained(
                        self.__scheduler_path,
                        **kwargs
                    )
                    self.change_model_status(ModelType.SCHEDULER, ModelStatus.READY, self.__scheduler_path)
                    self.current_scheduler_name = scheduler_name
                    self.logger.debug(f"Loaded scheduler {scheduler_name}")
                except Exception as e:
                    self.logger.error(f"Failed to load scheduler {scheduler_name}: {e}")
                    self.change_model_status(ModelType.SCHEDULER, ModelStatus.ERROR, self.__scheduler_path)

                if self.pipe:
                    self.pipe.scheduler = self.scheduler
                return scheduler

    def unload_scheduler(self):
        self.logger.debug("Unloading scheduler")
        self.scheduler_name = ""
        self.current_scheduler_name = ""
        self.do_change_scheduler = True
        self.scheduler = None
        self.change_model_status(ModelType.SCHEDULER, ModelStatus.UNLOADED, "")

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
        if self.pipe and self.pipe.scheduler:
            self.pipe.scheduler = self.scheduler
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADED, self.__scheduler_path)

    def remove_scheduler_from_pipe(self):
        if self.pipe and self.pipe.scheduler:
            self.pipe.scheduler = None
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.READY, self.__scheduler_path)
