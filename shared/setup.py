"""Canonical setup.py for the shared ``airunner_common`` package surface."""

from setuptools import setup

from airunner_common.package_metadata import (
    FACEHUGGERSHIELD_REQUIREMENT,
    README,
    VERSION,
)


setup(
    name="airunner-common",
    version=VERSION,
    author="Capsize LLC",
    description="Shared foundation (settings, contracts, layout) for AIRunner packages",
    long_description=README,
    long_description_content_type="text/markdown",
    license="Apache-2.0",
    author_email="contact@capsizegames.com",
    url="https://github.com/Capsize-Games/airunner",
    package_dir={"": "."},
    packages=["airunner_common"],
    python_requires=">=3.13.3",
    install_requires=[
        "python-dotenv==1.2.2",
        FACEHUGGERSHIELD_REQUIREMENT,
    ],
    include_package_data=True,
)
