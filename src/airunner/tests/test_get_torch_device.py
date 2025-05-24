"""
Unit tests for airunner.utils.application.get_torch_device.get_torch_device
"""

import pytest


def test_get_torch_device_cpu(monkeypatch):
    monkeypatch.setattr("torch.cuda.is_available", lambda: False)
    monkeypatch.setattr("torch.device", lambda x: f"device:{x}")
    from airunner.utils import get_torch_device

    dev = get_torch_device()
    assert dev == "device:cpu"


def test_get_torch_device_cuda(monkeypatch):
    monkeypatch.setattr("torch.cuda.is_available", lambda: True)
    monkeypatch.setattr("torch.device", lambda x: f"device:{x}")
    from airunner.utils import get_torch_device

    dev = get_torch_device(2)
    assert dev == "device:cuda:2"
