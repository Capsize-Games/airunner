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