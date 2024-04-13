def stop_profiler(pr):
    pr.disable()
    pr.print_stats(sort="time")
