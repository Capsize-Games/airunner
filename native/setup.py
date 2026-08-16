"""Canonical setup.py for the native package surface."""

from setuptools import setup

from airunner_common.package_metadata import build_native_setup_kwargs


setup(**build_native_setup_kwargs(package_source_dir="src"))
