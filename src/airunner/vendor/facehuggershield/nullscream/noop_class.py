class MagicType:

    def __getattr__(self, name):
        return MagicType()

    def __call__(self, *args, **kwargs):
        return MagicType()

    def __str__(self):
        return "MagicType instance"

    def __fspath__(self):
        return ""

    def __iter__(self):
        return iter([])

    def __mro_entries__(self, bases):
        return (MagicType,)  # Ensure it returns a tuple


class NoopClass:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return MagicType()

    def __getattr__(self, name):
        return MagicType()

    def __setattr__(self, key, value):
        pass
