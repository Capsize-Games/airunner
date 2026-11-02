"""Health reports the service distribution rather than a sibling's release."""

import importlib
import asyncio

from airunner_services.api.routes import health


def test_health_version_prefers_service_over_installed_siblings(monkeypatch):
    versions = importlib.import_module("airunner_services.utils.application.get_version")
    installed = {
        "airunner": "6.0.0",
        "airunner-native": "6.1.4",
        "airunner-common": "6.1.8",
        "airunner-services": "6.1.9",
    }
    monkeypatch.setattr(versions, "package_version", installed.__getitem__)

    assert versions.get_version() == "6.1.9"
    assert health.build_health_payload("healthy")["version"] == "6.1.9"
    assert asyncio.run(health.root())["version"] == "6.1.9"


def test_checkout_version_fallback_remains_available(monkeypatch):
    versions = importlib.import_module("airunner_services.utils.application.get_version")

    def missing(_name):
        raise versions.PackageNotFoundError()

    monkeypatch.setattr(versions, "package_version", missing)
    monkeypatch.setattr(versions, "_load_checkout_version", lambda: "checkout-version")

    assert versions.get_version() == "checkout-version"
    assert health.build_health_payload("healthy")["version"] == "checkout-version"
