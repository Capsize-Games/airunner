"""Run explicitly authorized language-data installation in an owned process."""

from pathlib import Path

from airunner_common.settings import AIRUNNER_BASE_PATH
from airunner_services.url_safety import is_offline_mode

PACKAGES = (
    "punkt", "punkt_tab", "averaged_perceptron_tagger",
    "averaged_perceptron_tagger_eng",
)


def download_nltk_data(directory: Path) -> None:
    """Install the fixed resource set inside the configured data root."""
    if is_offline_mode():
        raise RuntimeError("Language-data installation requires online mode")
    destination = directory.expanduser().resolve()
    root = Path(AIRUNNER_BASE_PATH).expanduser().resolve()
    if not destination.is_relative_to(root):
        raise ValueError("Language-data directory is outside the data root")
    destination.mkdir(parents=True, exist_ok=True)
    # Keep NLTK initialization in the installation worker.
    import nltk

    for package in PACKAGES:
        if not nltk.download(
            package, download_dir=str(destination),
            quiet=True, raise_on_error=True,
        ):
            raise RuntimeError("NLTK data installation failed")
