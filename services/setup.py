"""Canonical setup.py for the services package surface."""

from setuptools import setup

from airunner_common.package_metadata import build_services_setup_kwargs


setup(**build_services_setup_kwargs(package_source_dir="src"))
