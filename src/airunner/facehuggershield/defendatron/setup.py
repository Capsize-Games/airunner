from setuptools import setup, find_packages

setup(
    name="defendatron",
    version="0.1.11",
    author="Capsize LLC",
    description="",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    keywords="",
    license="GPL-3.0",
    author_email="contact@capsizegames.com",
    url="https://github.com/Capsize-Games/defendatron",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.10.0",
    install_requires=[
        "nullscream==0.1.5",
        "darklock==0.1.6",
        "shadowlogger==0.1.1",
    ],
    dependency_links=[
    ],
)
