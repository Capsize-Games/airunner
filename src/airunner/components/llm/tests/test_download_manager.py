"""Test the HuggingFace download manager integration."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication
from airunner.components.llm.managers.download_huggingface import (
    DownloadHuggingFaceModel,
)
from airunner.enums import SignalCode


def main():
    """Test the download manager."""
    app = QApplication(sys.argv)

    print("=" * 80)
    print("HuggingFace Download Manager Test")
    print("=" * 80)
    print()
    print("This will download Ministral-3-8B-Instruct-2512 to:")
    print("  ~/.local/share/airunner/text/models/llm/causallm/")
    print()
    print("The download runs in a background thread")
    print("Watch for progress updates in the console")
    print()

    # Create download manager
    downloader = DownloadHuggingFaceModel()

    # Subscribe to signals for testing
    def on_complete(data):
        print("\n" + "=" * 80)
        print("DOWNLOAD COMPLETE!")
        print("=" * 80)
        print(f"Model path: {data['model_path']}")
        if data.get("quantization_config"):
            config = data["quantization_config"]
            print(
                f"Quantization: {config['bits']}-bit ({config['quant_type']})"
            )
            print(f"Estimated VRAM: {config.get('estimated_vram_gb', '?')} GB")
        print()
        print("You can now load this model in AI Runner!")
        app.quit()

    def on_failed(data):
        print("\n" + "=" * 80)
        print("DOWNLOAD FAILED!")
        print("=" * 80)
        print(f"Error: {data['error']}")
        app.quit()

    downloader.register(SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE, on_complete)
    downloader.register(SignalCode.HUGGINGFACE_DOWNLOAD_FAILED, on_failed)

    # Start download
    downloader.download(
        repo_id="mistralai/Ministral-3-8B-Instruct-2512",
        model_type="ministral3",
        setup_quantization=True,
        quantization_bits=4,
    )

    # Run event loop
    print("Download started...")
    print("Press Ctrl+C to cancel")
    print()

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nCancelling download...")
        downloader.cancel()
        sys.exit(0)


if __name__ == "__main__":
    main()
