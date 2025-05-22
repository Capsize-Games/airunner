# Darklock

Completely disable the internet and other services, only allowing whitelists
through.

---

![img.png](img.png)

[![Upload Python Package](https://github.com/Capsize-Games/darklock/actions/workflows/python-publish.yml/badge.svg)](https://github.com/Capsize-Games/darklock/actions/workflows/python-publish.yml)

---

## Installation

```bash
pip install darklock
```

---

## Usage

Import into your application at the top of the main entry file (e.g. `main.py`).

Install the darklock for the service you want to restrict.

```python
import darklock

darklock.network.install()
darklock.os.install()
```

Uninstall the darklock for the service you no longer want to restrict.

```python
import darklock

darklock.network.uninstall()
darklock.os.uninstall()
```

---

## Testing

```bash
python -m unittest discover -s tests
```
