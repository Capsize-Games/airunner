# Shadowlogger

Simple wrapper for built-in logger module which intercepts all logs and shadows them, preventing sensitive information from being leaked.

---

![img.png](img.png)

[![Upload Python Package](https://github.com/Capsize-Games/shadowlogger/actions/workflows/python-publish.yml/badge.svg)](https://github.com/Capsize-Games/shadowlogger/actions/workflows/python-publish.yml)

---

## Installation

```bash
pip install shadowlogger
```

---

## Usage

```python
import shadowlogger

# Activate shadowlogger
shadowlogger.manager.install()

# Deactivate shadowlogger
shadowlogger.manager.uninstall()
```

or 

```python
from shadowlogger.shadowlogger import ShadowLogger


class MyCustomLogger(ShadowLogger):
    # override these to customize the logger
    prefix: str
    name: str
    message_format: str
    log_level: int
    
    # override this to handle the formatted message
    def handle_message(self, formatted_message: str, level_name: str):
        pass
```

---

## Testing

```bash
python -m unittest discover -s tests
```
