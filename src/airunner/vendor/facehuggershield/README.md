# Facehugger Shield Suite

Facehugger Shield Suite is a collection of Python modules designed to provide robust security, privacy, and control over your application's operations. The suite is composed of several tools that can be used independently or together to restrict access, intercept unwanted behaviors, and lock down your environment.

---

## Overview

- **Facehugger Shield**: Automatically locks down operations for specific modules, originally designed to restrict access to the Huggingface library, but can be used with any library. It leverages the other tools in this suite to provide comprehensive protection.
- **Nullscream**: Allows you to import noop (no-operation) functions and classes as drop-in replacements for blacklisted modules, making them importable but not executable.
- **Darklock**: Completely disables internet and other services, only allowing whitelisted operations through.
- **Shadowlogger**: Intercepts all logs and shadows them, preventing sensitive information from being leaked.
- **Defendatron**: A simple coordinator for the above modules, allowing you to activate or deactivate them as needed.

---

## Usage

### Facehugger Shield

Import in your application's main entry file (e.g. `main.py`), and activate before importing any other libraries:

```python
import facehuggershield.huggingface

activate()
```

Now you can use Huggingface libraries (or any other restricted library) without worrying about telemetry, networking, or file writes.

See the `activate` function in `huggingface/__init__.py` for settings.

---

### Nullscream

Import and activate Nullscream at the top of your main entry file:

```python
import nullscream

nullscream_blacklist = ["requests"]

nullscream.activate(
    blacklist=nullscream_blacklist,
)
```

Now when you import a blacklisted module (e.g. `requests`), you will get a noop version. To restore the original module:

```python
nullscream.uninstall(blacklist=["requests"])
```

---

### Darklock

Import and install Darklock for the services you want to restrict:

```python
import darklock

darklock.network.install()
darklock.os.install()
```

To remove restrictions:

```python
darklock.network.uninstall()
darklock.os.uninstall()
```

---

### Shadowlogger

Activate Shadowlogger to intercept and shadow all logs:

```python
import shadowlogger

shadowlogger.manager.install()
```

To deactivate:

```python
shadowlogger.manager.uninstall()
```

You can also subclass `ShadowLogger` to customize logging behavior.

---

### Defendatron

Defendatron coordinates the above modules:

```python
import defendatron

defendatron.activate()  # Activates all
defendatron.deactivate()  # Deactivates all

defendatron.nullscream.activate()
defendatron.shadowlogger.activate()
defendatron.darklock.activate()

defendatron.nullscream.deactivate()
defendatron.shadowlogger.deactivate()
defendatron.darklock.deactivate()
```

---

## How it Works

Facehugger Shield Suite uses a combination of module interception, network lockdown, and log interception to provide a secure and privacy-focused environment. By overriding or shadowing certain functions and modules, it prevents unwanted behaviors such as telemetry, unauthorized networking, and sensitive data leaks.

- **Nullscream** intercepts blacklisted modules and returns noop modules in their place, allowing them to be imported but not executed.
- **Darklock** locks down network and OS services, only allowing whitelisted operations.
- **Shadowlogger** intercepts and shadows all logs.
- **Defendatron** provides a unified interface to manage all these protections.

---

## Testing

Each module provides a test suite that can be run with:

```bash
python -m unittest discover -s tests
```

---

Facehugger Shield Suite is designed to provide the best settings for privacy and security, especially when working with third-party libraries that may not respect your application's boundaries.
