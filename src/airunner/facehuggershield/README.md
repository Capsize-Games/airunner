# Facehugger Shield

Facehugger Shield automatically locks down operations
for specific modules. It was designed to non-destructively restrict access
to the Huggingface library, but can be used with any library.

---

![img.png](img.png)

[![Upload Python Package](https://github.com/Capsize-Games/facehuggershield/actions/workflows/python-publish.yml/badge.svg)](https://github.com/Capsize-Games/facehuggershield/actions/workflows/python-publish.yml)

---

## Usage

Facehugger Shield was specifically designed to override Huggingface libraries, so the following examples show how to do that.


Install with Huggingface libraries (or any other library you want to restrict).

```bash
pip install facehuggershield
```

Import in your application's main entry file (e.g. `main.py`), import `facehuggershield` before importing
any other libraries.

```python
import facehuggershield.huggingface

activate()
```

Now you can use Huggingface libraries without worrying about telemetry, networking or file writes.

---

## Settings

See the `activate` function in the [huggingface/__init__.py](https://github.com/Capsize-Games/facehuggershield/blob/master/src/facehuggershield/huggingface/__init__.py) file.

---

## How it works

Facehugger Shield uses [nullscream](https://github.com/Capsize-Games/nullscream) to intercept blacklisted modules and return Noop modules in their place.
The noop modules are empty classes with functions that return Magic noop classes.
The magic class functions in turn respond with Magic classes.

This allows anything on the blacklist to be importable, but not executable.

By overriding certain functions in the [transformers](https://github.com/huggingface/transformers) library, Facehugger is able to prevent the use of Huggingface Hub.

Facehugger Shield also makes use of [darklock](https://github.com/Capsize-Games/darklock) to lock down network services, and [shadowlogger](https://github.com/Capsize-Games/shadowlogger) to intercept and reroute logs.

These libraries are combined under [defendatron](https://github.com/Capsize-Games/defendatron), a simple coordinator library.

Facehugger Shield contains all of the required settings for defendatron, as well as the best Huggingface Library settings for privacy.
