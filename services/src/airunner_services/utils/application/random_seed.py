import random
from airunner_common.settings import AIRUNNER_MAX_SEED


_random_generator = random.Random()


def random_seed() -> int:
    """Return one random seed in the configured inclusive range."""
    return _random_generator.randint(0, AIRUNNER_MAX_SEED)
