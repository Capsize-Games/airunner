import sounddevice as sd
import numpy as np


def log_audio_devices():
    devices = sd.query_devices()
    print("Available audio devices:")
    for i, device in enumerate(devices):
        print(
            f"Device {i}: {device['name']}, Max Output Channels: {device['max_output_channels']}, Default Sample Rate: {device['default_samplerate']}"
        )


def play_test_tone():
    samplerate = 44100  # Standard sample rate
    duration = 2  # seconds
    frequency = 440.0  # Hz (A4)

    print(f"Playing test tone at {samplerate} Hz...")
    t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
    tone = 0.5 * np.sin(2 * np.pi * frequency * t)

    try:
        with sd.OutputStream(samplerate=samplerate, channels=1):
            sd.play(tone, samplerate=samplerate)
            sd.wait()
        print("Test tone played successfully.")
    except Exception as e:
        print(f"Failed to play test tone: {e}")


if __name__ == "__main__":
    log_audio_devices()
    play_test_tone()
