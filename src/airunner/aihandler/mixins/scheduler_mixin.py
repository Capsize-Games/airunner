import traceback
import diffusers
from airunner.aihandler.settings import AVAILABLE_SCHEDULERS_BY_ACTION
from airunner.enums import Scheduler, SignalCode, SchedulerAlgorithm


class SchedulerMixin:
    scheduler_name: str = "Euler a"
    schedulers: dict = {
        "Euler a": "EulerAncestralDiscreteScheduler",
        "Euler": "EulerDiscreteScheduler",
        "LMS": "LMSDiscreteScheduler",
        "Heun": "HeunDiscreteScheduler",
        "DPM2": "DPMSolverSinglestepScheduler",
        "DPM++ 2M": "DPMSolverMultistepScheduler",
        "DPM2 Karras": "KDPM2DiscreteScheduler",
        "DPM2 a Karras": "KDPM2AncestralDiscreteScheduler",
        "DPM++ 2M Karras": "DPMSolverMultistepScheduler",
        "DPM++ 2M SDE Karras": "DPMSolverMultistepScheduler",
        "DDIM": "DDIMScheduler",
        "UniPC": "UniPCMultistepScheduler",
        "DDPM": "DDPMScheduler",
        "DEIS": "DEISMultistepScheduler",
        "DPM 2M SDE Karras": "DPMSolverMultistepScheduler",
        "PLMS": "PNDMScheduler",
        "DPM": "DPMSolverMultistepScheduler",

        "DDIM Inverse": "DDIMInverseScheduler",
        "IPNM": "IPNDMScheduler",
        "RePaint": "RePaintScheduler",
        "Karras Variance exploding": "KarrasVeScheduler",
        "VE-SDE": "ScoreSdeVeScheduler",
        "VP-SDE": "ScoreSdeVpScheduler",
        "VQ Diffusion": " VQDiffusionScheduler",
    }
    registered_schedulers: dict = {}
    do_change_scheduler = False
    _scheduler = None
    current_scheduler_name = None

    @property
    def scheduler_section(self):
        return self.action

    def clear_scheduler(self):
        self.logger.info("Clearing scheduler")
        self.scheduler_name = ""
        self.do_change_scheduler = True
        self._scheduler = None
        self.current_scheduler_name = None

    def load_scheduler(self, force_scheduler_name=None, config=None):
        if self.is_sd_xl_turbo:
            return None
        if (
            not force_scheduler_name and
            self._scheduler and not self.do_change_scheduler and
            self.options.get(f"scheduler") == self.current_scheduler_name
        ):
            return self._scheduler

        if not self.model_path or self.model_path == "":
            traceback.print_stack()
            raise Exception("Chicken / egg problem, model path not set")
        self.current_scheduler_name = force_scheduler_name if force_scheduler_name else self.options.get(f"scheduler")

        self.logger.info(f"Loading scheduler " + self.scheduler_name + " "+self.scheduler_section)

        scheduler_name = force_scheduler_name if force_scheduler_name else self.scheduler_name
        if not force_scheduler_name and scheduler_name not in AVAILABLE_SCHEDULERS_BY_ACTION[self.scheduler_section]:
            scheduler_name = AVAILABLE_SCHEDULERS_BY_ACTION[self.scheduler_section][0]
        scheduler_class_name = self.schedulers[scheduler_name]
        scheduler_class = getattr(diffusers, scheduler_class_name)

        kwargs = {
            "subfolder": "scheduler"
        }
        if self.current_model_branch:
            kwargs["variant"] = self.current_model_branch

        if config:
            config = dict(config)
            if scheduler_name == Scheduler.DPM_PP_2M_K.value:
                config["use_karras_sigmas"] = True
            if scheduler_name == Scheduler.DPM_PP_2M_SDE_K.value:
                config["algorithm_type"] = SchedulerAlgorithm.SDE_DPM_SOLVER_PLUS_PLUS.value
            elif scheduler_name == Scheduler.DPM_2M_SDE_K.value:
                config["algorithm_type"] = SchedulerAlgorithm.SDE_DPM_SOLVER.value
            elif scheduler_name.startswith("DPM"):
                if scheduler_name.find("++") != -1:
                    config["algorithm_type"] = SchedulerAlgorithm.DPM_SOLVER_PLUS_PLUS.value
                else:
                    config["algorithm_type"] = SchedulerAlgorithm.DPM_SOLVER.value
            self._scheduler = scheduler_class.from_config(config)
        else:
            if scheduler_name == Scheduler.DPM_PP_2M_K.value:
                kwargs["use_karras_sigmas"] = True
            if scheduler_name.startswith("DPM"):
                if scheduler_name.find("++") != -1:
                    kwargs["algorithm_type"] = SchedulerAlgorithm.DPM_SOLVER_PLUS_PLUS.value
                else:
                    kwargs["algorithm_type"] = SchedulerAlgorithm.DPM_SOLVER.value
            try:
                self.logger.info(f"Loading scheduler " + scheduler_name)
                self._scheduler = scheduler_class.from_pretrained(self.model_path, **kwargs)
            except NotImplementedError as e:
                self.logger.error(f"Unable to load scheduler {scheduler_name} from {self.model_path}")
        return self._scheduler

    def change_scheduler(self):
        if not self.do_change_scheduler or not self.pipe:
            return
        if self.model_path and self.model_path != "":
            config = self._scheduler.config if self._scheduler else None
            self.pipe.scheduler = self.load_scheduler(config=config)
            self.do_change_scheduler = False
        else:
            self.logger.warning("Unable to change scheduler, model_path is not set")

    def prepare_scheduler(self):
        scheduler_name = self.options.get(f"scheduler", Scheduler.EULER_ANCESTRAL.value)
        if self.scheduler_name != scheduler_name:
            self.logger.info("Preparing scheduler " + self.options.get(f"scheduler", ""))
            self.emit(SignalCode.LOG_STATUS_SIGNAL, f"Preparing scheduler {scheduler_name}")
            self.scheduler_name = scheduler_name
            self.do_change_scheduler = True
        else:
            self.do_change_scheduler = False