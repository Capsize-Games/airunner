from setuptools import setup, find_packages

setup(
    name='airunner-gfpgan',
    version="1.0.0",
    author="Capsize LLC",
    description="GFPGAN for AI Runner",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    keywords="ai, stable diffusion, art, ai art, stablediffusion, upscale, gfpgan",
    license="AGPL-3.0",
    author_email="contact@capsizegames.com",
    url="https://github.com/Capsize-Games/airunner",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.10.0",
    install_requires=[
        "basicsr==1.4.2",
        "facexlib==0.2.5",
        "realesrgan==",
    ],
    dependency_links=[]
)
