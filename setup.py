from setuptools import setup, find_packages

setup(
    name='airunner',
    version='1.8.9',
    license="",
    author="Capsize LLC",
    author_email="contact@capsize.gg",
    description="A Stable Diffusion GUI",
    packages=find_packages(),
    url="https://github.com/huggingface/diffusers",
    install_requires=[
        "aihandler==1.8.10",
    ]
)
