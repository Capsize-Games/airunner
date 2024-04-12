from tqdm import tqdm


class CustomTqdmProgressBar:
    def __init__(self, progress_bar):
        self.progress_bar = progress_bar
        self._lock = None

    def __call__(
        self,
        iterable=None,
        desc=None,
        total=None,
        leave=True,
        file=None,
        ncols=None,
        mininterval=0.1,
        maxinterval=10.0,
        miniters=None,
        ascii=None,
        disable=False,
        unit='it',
        unit_scale=False,
        dynamic_ncols=False,
        smoothing=0.3,
        bar_format=None,
        initial=0,
        position=None,
        postfix=None,
        unit_divisor=1000,
        write_bytes=None,
        lock_args=None,
        nrows=None,
        colour=None,
        delay=0,
        gui=False,
        **kwargs
    ):
        if total is None:
            total = self.progress_bar.maximum()
        self.tqdm_instance = tqdm(
            iterable=iterable,
            desc=desc,
            total=total,
            leave=leave,
            file=file,
            ncols=ncols,
            mininterval=mininterval,
            maxinterval=maxinterval,
            miniters=miniters,
            ascii=ascii,
            disable=disable,
            unit=unit,
            unit_scale=unit_scale,
            dynamic_ncols=dynamic_ncols,
            smoothing=smoothing,
            bar_format=bar_format,
            initial=initial,
            position=position,
            postfix=postfix,
            unit_divisor=unit_divisor,
            write_bytes=write_bytes,
            lock_args=lock_args,
            nrows=nrows,
            colour=colour,
            delay=delay,
            gui=gui,
            **kwargs
        )
        return self.tqdm_instance

    @property
    def n(self):
        return self.tqdm_instance.n

    @property
    def total(self):
        return self.tqdm_instance.total

    def update(self, n=1):
        self.tqdm_instance.update(n)
        self.progress_bar.setValue(self.tqdm_instance.n)

    def close(self):
        self.tqdm_instance.close()
        self.progress_bar.setValue(self.progress_bar.maximum())

    def set_lock(self, lock):
        self._lock = lock

    def get_lock(self):
        return self._lock

    def clear(self):
        if hasattr(self, '_lock'):
            del self._lock




