import cProfile


def start_profiler():
    pr = cProfile.Profile()
    pr.enable()
    return pr


