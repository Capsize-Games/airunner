import random
from airunner.settings import AIRUNNER_MAX_SEED


_random_generator = random.Random()


def random_seed():
    return _random_generator.randint(0, AIRUNNER_MAX_SEED)

