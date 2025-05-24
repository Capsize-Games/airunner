import pytest
from unittest.mock import patch
from airunner.utils.settings.get_qsettings import get_qsettings


def test_get_qsettings():
    import importlib

    gqs_mod = importlib.import_module("airunner.utils.settings.get_qsettings")

    class DummyQSettings:
        def __init__(self, org, app):
            self.org = org
            self.app = app

    old_org = getattr(gqs_mod, "AIRUNNER_ORGANIZATION", None)
    old_app = getattr(gqs_mod, "AIRUNNER_APPLICATION_NAME", None)
    old_qsettings = getattr(gqs_mod, "QSettings", None)
    gqs_mod.AIRUNNER_ORGANIZATION = "DummyOrg"
    gqs_mod.AIRUNNER_APPLICATION_NAME = "DummyApp"
    gqs_mod.QSettings = DummyQSettings
    try:
        s = gqs_mod.get_qsettings()
        assert isinstance(s, DummyQSettings)
        assert s.org == "DummyOrg"
        assert s.app == "DummyApp"
    finally:
        if old_org is not None:
            gqs_mod.AIRUNNER_ORGANIZATION = old_org
        if old_app is not None:
            gqs_mod.AIRUNNER_APPLICATION_NAME = old_app
        if old_qsettings is not None:
            gqs_mod.QSettings = old_qsettings
        else:
            delattr(gqs_mod, "QSettings")
