from setuptools import setup, find_packages

setup(
    name='airunner',
    version='1.8.10',
    author="Capsize LLC",
    description="A Stable Diffusion GUI",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="",
    keywords="ai, chatbot, chat, ai",
    license="AGPL-3.0",
    author_email="contact@capsize.gg",
    url="https://github.com/w4ffl35/airunner",
    package_dir={"": "sdrunner"},
    packages=find_packages("sdrunner"),
    python_requires=">=3.10.0",
    install_requires=[
        "aihandler==1.8.12",
    ]
)
