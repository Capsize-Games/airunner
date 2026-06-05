"""Runtime enum facade for service-owned art manager code."""

from __future__ import annotations

from airunner_services.contract_enums import EngineResponseCode
from airunner_services.contract_enums import GeneratorSection
from airunner_services.contract_enums import ImageGenerator
from airunner_services.contract_enums import ModelStatus
from airunner_services.contract_enums import ModelType
from airunner_services.contract_enums import Scheduler
from airunner_services.contract_enums import StableDiffusionVersion
from airunner_services.utils.application.enum_resolver import (
    handler_state_type,
)
from airunner_services.utils.application.enum_resolver import (
    model_action_type,
)
from airunner_services.utils.application.enum_resolver import signal_code_proxy

SignalCode = signal_code_proxy()
ModelAction = model_action_type()
HandlerState = handler_state_type()


__all__ = [
    "EngineResponseCode",
    "GeneratorSection",
    "HandlerState",
    "ImageGenerator",
    "ModelAction",
    "ModelStatus",
    "ModelType",
    "Scheduler",
    "SignalCode",
    "StableDiffusionVersion",
]
