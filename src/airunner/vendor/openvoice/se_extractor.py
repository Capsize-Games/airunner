import os
import glob
import torch
import hashlib
import librosa
import base64
from glob import glob
import numpy as np
from pydub import AudioSegment
import torchaudio

model_size = "medium"
model = None


def split_audio_vad(audio_path, audio_name, target_dir, split_seconds=10.0):
    # Initialize Silero VAD model if not already done
    if not hasattr(split_audio_vad, "vad_model"):
        # Load Silero VAD model
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
        )
        split_audio_vad.vad_model = model
        split_audio_vad.get_speech_timestamps = utils[0]

    SAMPLE_RATE = 16000
    # Load audio with torchaudio
    waveform, sample_rate = torchaudio.load(audio_path)
    if sample_rate != SAMPLE_RATE:
        resampler = torchaudio.transforms.Resample(sample_rate, SAMPLE_RATE)
        waveform = resampler(waveform)

    # Convert to mono if needed (take first channel)
    if waveform.shape[0] > 1:
        waveform = waveform[0].unsqueeze(0)

    # Get speech timestamps
    speech_timestamps = split_audio_vad.get_speech_timestamps(
        waveform[0],
        split_audio_vad.vad_model,
        threshold=0.5,
        min_speech_duration_ms=100,
        min_silence_duration_ms=1000,
    )

    # Convert timestamps to segments
    segments = [(ts["start"], ts["end"]) for ts in speech_timestamps]
    segments = [
        (float(s) / SAMPLE_RATE, float(e) / SAMPLE_RATE) for s, e in segments
    ]

    audio_active = AudioSegment.silent(duration=0)
    audio = AudioSegment.from_file(audio_path)

    for start_time, end_time in segments:
        audio_active += audio[int(start_time * 1000) : int(end_time * 1000)]

    audio_dur = audio_active.duration_seconds
    print(f"after vad: dur = {audio_dur}")
    target_folder = os.path.join(target_dir, audio_name)
    wavs_folder = os.path.join(target_folder, "wavs")
    os.makedirs(wavs_folder, exist_ok=True)
    start_time = 0.0
    count = 0
    num_splits = int(np.round(audio_dur / split_seconds))
    assert num_splits > 0, "input audio is too short"
    interval = audio_dur / num_splits

    for i in range(num_splits):
        end_time = min(start_time + interval, audio_dur)
        if i == num_splits - 1:
            end_time = audio_dur
        output_file = f"{wavs_folder}/{audio_name}_seg{count}.wav"
        audio_seg = audio_active[int(start_time * 1000) : int(end_time * 1000)]
        audio_seg.export(output_file, format="wav")
        start_time = end_time
        count += 1
    return wavs_folder


def hash_numpy_array(audio_path):
    array, _ = librosa.load(audio_path, sr=None, mono=True)
    # Convert the array to bytes
    array_bytes = array.tobytes()
    # Calculate the hash of the array bytes
    hash_object = hashlib.sha256(array_bytes)
    hash_value = hash_object.digest()
    # Convert the hash value to base64
    base64_value = base64.b64encode(hash_value)
    return base64_value.decode("utf-8")[:16].replace("/", "_^")


def get_se(audio_path, vc_model, target_dir="processed"):
    version = vc_model.version
    print("OpenVoice version:", version)

    audio_name = f"{os.path.basename(audio_path).rsplit('.', 1)[0]}_{version}_{hash_numpy_array(audio_path)}"
    se_path = os.path.join(target_dir, audio_name, "se.pth")

    wavs_folder = split_audio_vad(
        audio_path, target_dir=target_dir, audio_name=audio_name
    )

    audio_segs = glob(f"{wavs_folder}/*.wav")
    if len(audio_segs) == 0:
        raise NotImplementedError("No audio segments found!")

    return vc_model.extract_se(audio_segs, se_save_path=se_path), audio_name
