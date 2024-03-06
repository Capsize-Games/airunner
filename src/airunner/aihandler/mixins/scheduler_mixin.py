import diffusers
from airunner.settings import AVAILABLE_SCHEDULERS_BY_ACTION
from airunner.enums import Scheduler, SignalCode, SchedulerAlgorithm
from airunner.settings import SCHEDULER_CLASSES, DEFAULT_SCHEDULER


class SchedulerMixin:
    def __init__(self):
        self.scheduler_name: str = DEFAULT_SCHEDULER
        self.schedulers: dict = SCHEDULER_CLASSES
        self.registered_schedulers: dict = {}
        self.current_scheduler_name: str = ""
        self.do_change_scheduler: bool = False
        self._scheduler = None

    @property
    def scheduler_section(self):
        return self.sd_request.generator_settings.section

    def clear_scheduler(self):
        self.logger.debug("Clearing scheduler")
        self.scheduler_name = ""
        self.current_scheduler_name = ""
        self.do_change_scheduler = True
        self._scheduler = None

    def load_scheduler(self, force_scheduler_name=None, config=None, local_files_only=True):
        if self.is_sd_xl_turbo:
            return None
        if (
            not force_scheduler_name and
            self._scheduler and not self.do_change_scheduler and
            self.settings["generator_settings"]["scheduler"] != self.sd_request.generator_settings.scheduler
        ):
            return self._scheduler
        self.current_scheduler_name = force_scheduler_name if force_scheduler_name else self.sd_request.generator_settings.scheduler
        self.logger.debug(f"Loading scheduler")
        scheduler_name = force_scheduler_name if force_scheduler_name else self.scheduler_name
        if not force_scheduler_name and scheduler_name not in AVAILABLE_SCHEDULERS_BY_ACTION[self.scheduler_section]:
            scheduler_name = AVAILABLE_SCHEDULERS_BY_ACTION[self.scheduler_section][0]
        scheduler_class_name = self.schedulers[scheduler_name]
        scheduler_class = getattr(diffusers, scheduler_class_name)

        kwargs = {
            "subfolder": "scheduler",
            "local_files_only": local_files_only,
        }
        if self.current_model_branch:
            kwargs["variant"] = self.current_model_branch

        if config:
            config = dict(config)
            if scheduler_name == Scheduler.DPM_PP_2M_K.value:
                config["use_karras_sigmas"] = True

            algorithm_type = config.get("algorithm_type", None)
            if scheduler_name == Scheduler.DPM_PP_2M_SDE_K.value:
                algorithm_type = SchedulerAlgorithm.SDE_DPM_SOLVER_PLUS_PLUS
            elif scheduler_name == Scheduler.DPM_2M_SDE_K.value:
                algorithm_type = SchedulerAlgorithm.SDE_DPM_SOLVER
            elif scheduler_name.startswith("DPM"):
                if scheduler_name.find("++") != -1:
                    algorithm_type = SchedulerAlgorithm.DPM_SOLVER_PLUS_PLUS
                else:
                    algorithm_type = SchedulerAlgorithm.DPM_SOLVER
            if algorithm_type is not None:
                config["algorithm_type"] = algorithm_type.value

            self._scheduler = scheduler_class.from_config(config)
        else:
            if scheduler_name == Scheduler.DPM_PP_2M_K.value:
                kwargs["use_karras_sigmas"] = True
            if scheduler_name.startswith("DPM"):
                if scheduler_name.find("++") != -1:
                    algorithm_type = SchedulerAlgorithm.DPM_SOLVER_PLUS_PLUS
                else:
                    algorithm_type = SchedulerAlgorithm.DPM_SOLVER
                kwargs["algorithm_type"] = algorithm_type.value
            try:
                self.logger.debug(
                    f"Loading scheduler `{scheduler_name}` "
                    f"from pretrained path `{self.model_path}`"
                )
                self._scheduler = scheduler_class.from_pretrained(
                    self.model_path,
                    **kwargs
                )
            except NotImplementedError as e:
                self.logger.error(
                    f"Unable to load scheduler {scheduler_name} "
                    f"from {self.sd_request.generator_settings.model}"
                )
        return self._scheduler

    def change_scheduler(self):
        if not self.do_change_scheduler or not self.pipe:
            return
        if self.sd_request.generator_settings.model and self.sd_request.generator_settings.model != "":
            config = self._scheduler.config if self._scheduler else None
            self.pipe.scheduler = self.load_scheduler(config=config)
            self.do_change_scheduler = False
        else:
            self.logger.warning(
                "Unable to change scheduler, model_path is not set"
            )

    def prepare_scheduler(self):
        scheduler_name = self.sd_request.generator_settings.scheduler
        if self.scheduler_name != scheduler_name:
            self.logger.debug("Preparing scheduler")
            self.emit(
                SignalCode.LOG_STATUS_SIGNAL,
                f"Preparing scheduler {scheduler_name}"
            )
            self.scheduler_name = scheduler_name
            self.do_change_scheduler = True
        else:
            self.do_change_scheduler = False