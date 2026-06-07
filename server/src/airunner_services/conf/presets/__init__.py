"""Deployment mode presets for the settings system.

Each preset overrides :mod:`airunner_services.conf.default_settings` with
mode-appropriate values.  The active preset is selected automatically
based on the ``DEPLOYMENT_MODE`` setting or the ``AIRUNNER_DEPLOYMENT_MODE``
environment variable.
"""
