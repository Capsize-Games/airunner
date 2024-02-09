# AI Runner Contribution Guide

Thank you for your interest in contributing to AI Runner. This guide provides an overview of our project's conventions and practices. Please ensure all commits are signed.

---

## Coding Conventions

We follow the PEP 8 style guide for Python code. You can find the complete guide [here](https://pep8.org/). 

---

## Logging Practices

- Use `self.logger` for logging within classes.

**Examples**:
- `self.logger.debug("...")`
- `self.logger.info("...")`
- `self.logger.warning("...")`
- `self.logger.error("...")`

---

## Signal and Slot Management

We utilize a `SignalMediator` class to manage signal-slot connections across different classes without direct imports.

**Example**:

In the `__init__` function of a class, connect a slot:

`self.register(SignalCode.SOME_CODE_SIGNAL, self.on_some_signal)`

Then, define the slot function:

```python
def on_some_signal(self, message):
    # Implement functionality here
    ...
```

To emit the signal (from any class):

`self.emit(SignalCode.SOME_CODE_SIGNAL, "Hello World!")`

Note: We use the `SignalCode` enum to define signal codes. The message parameter is optional and can be any object type.

---

## Inter-Class Function Calls

We employ a `ServiceLocator` class to call functions defined in one class from another class, avoiding direct imports.

**Example**:

Register a function:

`self.register_service(ServiceCode.SOME_CODE, self.some_function)`

Define the function:

```python
def some_function(self, message):
    # Implement functionality here
    ...
```

To call the function (from any class):

`self.get_service(ServiceCode.SOME_CODE)("Hello World!")`

---

## Widgets, templates and resources (icons)

### Widgets

Widgets are stored under `src/airunner/widgets`. Each widget has a `templates` 
directory which contains template files for the widget (see below for more information).

- Widgets all extends from `BaseWidget`.
- Classes are named `ExampleWidget` where `Example` is the name of the widget and `Widget` is the suffix.
- See existing widgets for examples of how to extend `BaseWidget` and use the `widget_class_` attribute.

### Templates

- Templates are stored in a `templates` directory inside of each `widget` directory
- Use `pyside6-designer` to edit templates
- Build templates with `python bin/build_ui.py`
- See existing widgets for examples of how to use templates

### Icons

Icons are managed with resource files which are in turn managed with `pyside6-designer` 
and built with a custom script (see the following list).

- Use [svgrepo](https://www.svgrepo.com/) for icons
- Icons are stored in `src/airunner/icons/dark` and `src/airunner/icons/light` for dark and light themes respectively.
- Use `pyside6-designer` to add or edit icons
- Build resources with `python bin/build_ui.py`