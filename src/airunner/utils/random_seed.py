import random
from airunner.settings import MAX_SEED


_random_generator = random.Random()


def random_seed():
    return _random_generator.randint(0, MAX_SEED)

