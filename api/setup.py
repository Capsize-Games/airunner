"""Canonical setup.py for the API package surface."""

from setuptools import setup

from package_metadata import build_setup_kwargs


setup(**build_setup_kwargs(package_source_dir="src"))