# Contributing to AI Runner

All commits must be signed.

If you would like to contribute to AI Runner see the contributing guidelines below.

---

## Code Style

- Use enums instead of strings for constants.
- Store enums in `enums.py`.
- Use `snake_case` for variables and functions.
- Use `PascalCase` for classes.
- Use `UPPER_SNAKE_CASE` for constants.
- Use `lowercase` for files and directories. Separate `PascalCase` classes with underscores.
- Use `"""docstrings"""` for documentation.
- Use `# TODO: ...` for todos.
- Use `# FIXME: ...` for bugs.
- Use `# NOTE: ...` for notes.
- Use `# HACK: ...` for hacks.
- Use `# XXX: ...` for warnings.

---

## Logging

- Use `self.logger` for logging in classes.

### Examples:
- `self.logger.debug("...")`
- `self.logger.info("...")`
- `self.logger.warning("...")`
- `self.logger.error("...")`

---

## Signals and Slots

We use a `SignalMediator` class (see `signal_mediator.py`) to connect signals and slots. 
This allows us to connect signals and slots in different classes without having to import the other class.

As most of our classes are extended from a base class (such as `BaseWidget` for 
Widget classes), we can use certain functions to connect signals and slots.

### Examples:

First connect a slot. This is typically done within the `__init__` function of a class.

`self.register("some_signal", self)`

Define the slot function

```
def on_some_signal(self, message):
    # Do something here
    ...
```

Emit the signal from some other class (or the same class)

`self.emit("some_signal", "Hello World!")`

The message parameter is optional and can be any type of object.

When defining a signal, use `anything_signal` where `anything` is a descriptive
but concise name for the signal.
All signals must be suffixed with `_signal`.

When defining a slot, you must use the name of the signal with `on_` prefixed
so that the signature of the function is `on_signal_name(self, message)`.

There are numerous examples of this in the codebase, some can be seen in `worker_manager.py`

---

## Calling functions from other classes

We use a `ServiceLocator` class (see `service_locator.py`) to access functions
which are defined in one class from another class without having to import the
class which defines the function.

### Example

Register a function with `self.register_service("some_function", self.some_function)`

Define the function

```
def some_function(self, message):
    # Do something here
    ...
```

Call the function from some other class (or the same class)

`self.get_service("some_function")("Hello World!")`