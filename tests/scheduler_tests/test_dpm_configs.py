#!/usr/bin/env python3
"""
Test script to verify DPM scheduler configurations are different.
"""
from diffusers import DPMSolverMultistepScheduler

configs = {
    "DPM": {
        "algorithm_type": "dpmsolver++",
        "use_karras_sigmas": False,
        "solver_order": 1,
    },
    "DPM++ 2M": {
        "algorithm_type": "dpmsolver++",
        "use_karras_sigmas": False,
    },
    "DPM++ 2M Karras": {
        "algorithm_type": "dpmsolver++",
        "use_karras_sigmas": True,
    },
    "DPM++ 2M SDE Karras": {
        "algorithm_type": "sde-dpmsolver++",
        "use_karras_sigmas": True,
        "solver_type": "midpoint",
    },
    "DPM 2M SDE Karras": {
        "algorithm_type": "sde-dpmsolver++",
        "use_karras_sigmas": True,
        "solver_type": "heun",
    },
}

print("=" * 80)
print("DPM SCHEDULER CONFIGURATION TEST")
print("=" * 80)

schedulers = {}
for name, config in configs.items():
    try:
        s = DPMSolverMultistepScheduler(num_train_timesteps=1000, **config)
        schedulers[name] = s
        print(f"\n✅ {name}:")
        print(f"   algorithm_type: {s.config.algorithm_type}")
        print(f"   solver_type: {s.config.solver_type}")
        print(f"   use_karras_sigmas: {s.config.use_karras_sigmas}")
        print(f"   solver_order: {s.config.solver_order}")
    except Exception as e:
        print(f"\n❌ {name} FAILED: {e}")

print("\n" + "=" * 80)
print("CHECKING FOR DUPLICATES")
print("=" * 80)

# Check if any two configs are identical
names = list(schedulers.keys())
duplicates_found = False
for i, name1 in enumerate(names):
    for name2 in names[i + 1 :]:
        s1 = schedulers[name1]
        s2 = schedulers[name2]
        if (
            s1.config.algorithm_type == s2.config.algorithm_type
            and s1.config.solver_type == s2.config.solver_type
            and s1.config.use_karras_sigmas == s2.config.use_karras_sigmas
            and s1.config.solver_order == s2.config.solver_order
        ):
            print(
                f"\n⚠️  DUPLICATE: '{name1}' and '{name2}' have identical configs!"
            )
            duplicates_found = True

if not duplicates_found:
    print("\n✅ All scheduler configs are UNIQUE!")

print("=" * 80)
