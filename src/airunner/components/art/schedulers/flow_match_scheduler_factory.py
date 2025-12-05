"""Flow Match Scheduler Factory.

Creates flow-matching schedulers (for FLUX and Z-Image models) with the
appropriate configuration based on display name.

Flow-matching models use a different mathematical formulation than DDPM/DDIM
models, so they require specialized schedulers:
- FlowMatchEulerDiscreteScheduler: Basic Euler method
- FlowMatchLCMScheduler: Latent Consistency Model scheduler
"""

from typing import Any, Dict, Optional, Union
from diffusers.schedulers import FlowMatchEulerDiscreteScheduler

from airunner.enums import Scheduler


# Try to import FlowMatchLCMScheduler (may not be available in all versions)
try:
    from diffusers.schedulers import FlowMatchLCMScheduler
    HAS_LCM_SCHEDULER = True
except ImportError:
    HAS_LCM_SCHEDULER = False
    FlowMatchLCMScheduler = None


# Map display names to scheduler classes and config overrides
# IMPORTANT: Explicitly set flags to False when not used to prevent
# config pollution from previously loaded schedulers
FLOW_MATCH_SCHEDULER_CONFIG: Dict[str, Dict[str, Any]] = {
    Scheduler.FLOW_MATCH_EULER.value: {
        "class": FlowMatchEulerDiscreteScheduler,
        "config": {
            "use_karras_sigmas": False,
            "stochastic_sampling": False,
        },
    },
    Scheduler.FLOW_MATCH_LCM.value: {
        "class": FlowMatchLCMScheduler if HAS_LCM_SCHEDULER else FlowMatchEulerDiscreteScheduler,
        "config": {
            "use_karras_sigmas": False,
            "stochastic_sampling": False,
        },
    },
}

# All flow-match scheduler display names
FLOW_MATCH_SCHEDULER_NAMES = list(FLOW_MATCH_SCHEDULER_CONFIG.keys())


def is_flow_match_scheduler(scheduler_name: str) -> bool:
    """Check if a scheduler name is a flow-match scheduler.
    
    Args:
        scheduler_name: The display name of the scheduler.
        
    Returns:
        True if the scheduler is a flow-match type.
    """
    return scheduler_name in FLOW_MATCH_SCHEDULER_NAMES


def create_flow_match_scheduler(
    scheduler_name: str,
    base_config: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Union[
    FlowMatchEulerDiscreteScheduler,
    Any,  # FlowMatchLCMScheduler
]:
    """Create a flow-match scheduler with appropriate configuration.
    
    Args:
        scheduler_name: Display name of the scheduler from Scheduler enum.
        base_config: Optional base configuration from existing scheduler.
        **kwargs: Additional keyword arguments to pass to from_config().
        
    Returns:
        Configured flow-match scheduler instance.
        
    Raises:
        ValueError: If scheduler_name is not a recognized flow-match scheduler.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if scheduler_name not in FLOW_MATCH_SCHEDULER_CONFIG:
        raise ValueError(
            f"Unknown flow-match scheduler: {scheduler_name}. "
            f"Valid options: {FLOW_MATCH_SCHEDULER_NAMES}"
        )
    
    config_entry = FLOW_MATCH_SCHEDULER_CONFIG[scheduler_name]
    scheduler_class = config_entry["class"]
    config_overrides = config_entry["config"]
    
    logger.info(
        f"[SCHEDULER FACTORY] Creating '{scheduler_name}' with class={scheduler_class.__name__}, "
        f"overrides={config_overrides}"
    )
    
    # Handle LCM scheduler not being available
    if scheduler_name == Scheduler.FLOW_MATCH_LCM.value and not HAS_LCM_SCHEDULER:
        logger.warning(
            "FlowMatchLCMScheduler not available in this diffusers version, "
            "falling back to FlowMatchEulerDiscreteScheduler"
        )
    
    # Build final config
    if base_config:
        final_config = dict(base_config)
        final_config.update(config_overrides)
        final_config.update(kwargs)
        scheduler = scheduler_class.from_config(final_config)
    else:
        # Create with default config + overrides
        final_config = dict(config_overrides)
        final_config.update(kwargs)
        scheduler = scheduler_class(**final_config)

    # Ensure override flags are definitely applied even if from_config drops them
    try:
        if hasattr(scheduler, "register_to_config"):
            scheduler.register_to_config(**config_overrides)
        for attr, value in config_overrides.items():
            if hasattr(scheduler, attr):
                setattr(scheduler, attr, value)
    except Exception:
        # Best-effort; scheduler will still run with whatever config it has
        logger.debug("Could not force-apply scheduler overrides", exc_info=True)
    
    # Log the final config that was applied
    logger.info(
        f"[SCHEDULER FACTORY] Created {scheduler.__class__.__name__} with "
        f"karras={scheduler.config.get('use_karras_sigmas', False)}, "
        f"stochastic={scheduler.config.get('stochastic_sampling', False)}"
    )
    return scheduler


def get_flow_match_scheduler_class(
    scheduler_name: str,
) -> type:
    """Get the scheduler class for a flow-match scheduler name.
    
    Args:
        scheduler_name: Display name of the scheduler.
        
    Returns:
        The scheduler class.
        
    Raises:
        ValueError: If scheduler_name is not recognized.
    """
    if scheduler_name not in FLOW_MATCH_SCHEDULER_CONFIG:
        raise ValueError(f"Unknown flow-match scheduler: {scheduler_name}")
    
    return FLOW_MATCH_SCHEDULER_CONFIG[scheduler_name]["class"]


def get_flow_match_scheduler_config_overrides(
    scheduler_name: str,
) -> Dict[str, Any]:
    """Get the config overrides for a flow-match scheduler.
    
    Args:
        scheduler_name: Display name of the scheduler.
        
    Returns:
        Dict of config overrides to apply.
        
    Raises:
        ValueError: If scheduler_name is not recognized.
    """
    if scheduler_name not in FLOW_MATCH_SCHEDULER_CONFIG:
        raise ValueError(f"Unknown flow-match scheduler: {scheduler_name}")
    
    return dict(FLOW_MATCH_SCHEDULER_CONFIG[scheduler_name]["config"])
