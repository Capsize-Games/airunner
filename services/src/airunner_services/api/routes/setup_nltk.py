"""Install setup language data without blocking the API event loop."""

import asyncio

PACKAGES = (
    "punkt", "punkt_tab", "averaged_perceptron_tagger",
    "averaged_perceptron_tagger_eng",
)


async def install_nltk_data() -> list[str]:
    """Return installed packages; reject a false downloader result."""
    # Keep NLTK's import-time initialization out of API route discovery.
    import nltk

    installed: list[str] = []
    for package in PACKAGES:
        succeeded = await asyncio.to_thread(
            nltk.download, package, quiet=True, raise_on_error=True,
        )
        if not succeeded:
            raise RuntimeError("NLTK data installation failed")
        installed.append(package)
    return installed
