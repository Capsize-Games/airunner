"""Bounded, no-playback eSpeak WAV renderer for headless TTS requests."""

from __future__ import annotations

import io
import math
import re
import struct
import subprocess
import tempfile
import threading
import wave
from typing import Callable, Optional


ESPEAK_EXECUTABLE = "/usr/bin/espeak-ng"
MAX_TEXT_LENGTH = 5000
MAX_WAV_BYTES = 8 * 1024 * 1024
MAX_CATALOG_BYTES = 256 * 1024
PROCESS_TIMEOUT_SECONDS = 8.0
VOICE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


class EspeakRenderError(RuntimeError):
    """Raised when bounded eSpeak synthesis or voice lookup fails."""


class EspeakCliRenderer:
    """Render plain text with the fixed, reviewed eSpeak NG executable."""

    def __init__(
        self,
        *,
        popen: Callable = subprocess.Popen,
        executable: str = ESPEAK_EXECUTABLE,
    ) -> None:
        self._popen = popen
        self._executable = executable
        self._voice_ids: Optional[tuple[str, ...]] = None

    @property
    def voice_ids(self) -> Optional[tuple[str, ...]]:
        """Return the last bounded CLI catalogue, without starting a process."""
        return self._voice_ids

    def render(self, text: str, *, voice: Optional[str], speed: float) -> bytes:
        """Synthesize bounded plain text into a validated streaming WAV."""
        text = self._validate_text(text)
        rate = self._rate_for_speed(speed)
        voice_id = voice or "en-us"
        if not VOICE_ID_RE.fullmatch(voice_id):
            raise EspeakRenderError("unsupported eSpeak voice")
        voices = self.catalogue()
        if voice_id not in voices:
            raise EspeakRenderError("unsupported eSpeak voice")
        argv = [
            self._executable,
            "--stdout",
            "--stdin",
            "-v",
            voice_id,
            "-s",
            str(rate),
        ]
        output = self._run_bounded(argv, text.encode("utf-8"), MAX_WAV_BYTES)
        return self._normalize_wav(output)

    def catalogue(self) -> tuple[str, ...]:
        """Read actual language IDs and omit MBROLA/path-backed entries."""
        if self._voice_ids is not None:
            return self._voice_ids
        output = self._run_bounded(
            [self._executable, "--voices"], b"", MAX_CATALOG_BYTES
        )
        try:
            lines = output.decode("utf-8", errors="strict").splitlines()
        except UnicodeDecodeError as exc:
            raise EspeakRenderError("eSpeak voice catalogue is malformed") from exc
        voices: set[str] = set()
        for line in lines[1:]:
            columns = line.split()
            if len(columns) < 5:
                continue
            voice_id, voice_name, voice_file = columns[1], columns[3], columns[4]
            file_parts = voice_file.lower().replace("\\", "/").split("/")
            if (
                not VOICE_ID_RE.fullmatch(voice_id)
                or "mbrola" in voice_name.lower()
                or any(part in {"mb", "mbrola"} for part in file_parts)
                or voice_file.startswith("/")
                or ".." in file_parts
            ):
                continue
            voices.add(voice_id)
        if not voices:
            raise EspeakRenderError("eSpeak reported no supported voices")
        self._voice_ids = tuple(sorted(voices))
        return self._voice_ids

    @staticmethod
    def _validate_text(text: str) -> str:
        if not isinstance(text, str) or not text.strip():
            raise EspeakRenderError("text must not be blank")
        if len(text) > MAX_TEXT_LENGTH or "\x00" in text:
            raise EspeakRenderError("text exceeds eSpeak input limits")
        return text

    @staticmethod
    def _rate_for_speed(speed: float) -> int:
        if isinstance(speed, bool) or not isinstance(speed, (float, int)):
            raise EspeakRenderError("speed must be a finite number")
        if not math.isfinite(speed):
            raise EspeakRenderError("speed must be a finite number")
        rate = round(float(speed) * 100)
        if not 50 <= rate <= 400:
            raise EspeakRenderError("speed is outside eSpeak's supported range")
        return rate

    def _run_bounded(
        self, argv: list[str], input_bytes: bytes, output_limit: int
    ) -> bytes:
        """Run one fixed-executable process, killing it on deadline or output cap."""
        try:
            with tempfile.TemporaryFile(mode="w+b") as stdin_file:
                stdin_file.write(input_bytes)
                stdin_file.seek(0)
                process = self._popen(
                    argv,
                    stdin=stdin_file,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    shell=False,
                    close_fds=True,
                    cwd="/",
                    env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
                )
        except OSError as exc:
            raise EspeakRenderError("eSpeak executable is unavailable") from exc

        chunks: list[bytes] = []
        total_bytes = 0
        overflow = threading.Event()
        read_error: list[BaseException] = []

        def collect_stdout() -> None:
            nonlocal total_bytes
            try:
                remaining = output_limit + 1
                while remaining:
                    chunk = process.stdout.read(min(65536, remaining))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total_bytes += len(chunk)
                    remaining -= len(chunk)
                if total_bytes > output_limit:
                    overflow.set()
                    process.kill()
            except BaseException as exc:  # passed to the caller after join
                read_error.append(exc)

        reader = threading.Thread(target=collect_stdout, daemon=True)
        reader.start()
        try:
            try:
                process.wait(timeout=PROCESS_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                reader.join(timeout=1.0)
                raise EspeakRenderError("eSpeak synthesis timed out")
            reader.join(timeout=1.0)
            if reader.is_alive():
                process.kill()
                process.wait()
                raise EspeakRenderError("eSpeak output did not close")
            if overflow.is_set():
                raise EspeakRenderError("eSpeak output exceeded the limit")
            if read_error:
                raise EspeakRenderError(
                    "could not read eSpeak output"
                ) from read_error[0]
            if process.returncode != 0:
                raise EspeakRenderError("eSpeak process failed")
            return b"".join(chunks)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            stdin_stream = getattr(process, "stdin", None)
            if stdin_stream and not stdin_stream.closed:
                stdin_stream.close()
            if process.stdout:
                process.stdout.close()

    @staticmethod
    def _normalize_wav(output: bytes) -> bytes:
        """Validate bounded PCM WAV data and fix streaming-size placeholders."""
        if len(output) < 44 or output[:4] != b"RIFF" or output[8:12] != b"WAVE":
            raise EspeakRenderError("eSpeak returned invalid WAV data")
        normalized = bytearray(output)
        struct.pack_into("<I", normalized, 4, len(normalized) - 8)
        cursor = 12
        format_params = None
        data_size = None
        while cursor + 8 <= len(normalized):
            chunk_id = bytes(normalized[cursor : cursor + 4])
            declared_size = struct.unpack_from("<I", normalized, cursor + 4)[0]
            payload_start = cursor + 8
            available = len(normalized) - payload_start
            chunk_size = declared_size
            if chunk_size > available:
                if chunk_id != b"data":
                    raise EspeakRenderError("eSpeak returned truncated WAV data")
                chunk_size = available
                struct.pack_into("<I", normalized, cursor + 4, chunk_size)
            if chunk_id == b"fmt ":
                if chunk_size < 16:
                    raise EspeakRenderError("eSpeak returned invalid WAV format")
                format_params = struct.unpack_from("<HHIIHH", normalized, payload_start)
            elif chunk_id == b"data":
                if data_size is not None:
                    raise EspeakRenderError("eSpeak returned multiple WAV data chunks")
                data_size = chunk_size
                break
            cursor = payload_start + chunk_size + (chunk_size & 1)
        if format_params is None or data_size is None or data_size <= 0:
            raise EspeakRenderError("eSpeak returned incomplete WAV data")
        (
            audio_format,
            channels,
            sample_rate,
            byte_rate,
            block_align,
            bits,
        ) = format_params
        sample_width = bits // 8
        if (
            audio_format != 1
            or channels <= 0
            or sample_rate <= 0
            or bits not in (8, 16, 24, 32)
            or block_align != channels * sample_width
            or byte_rate != sample_rate * block_align
            or data_size % block_align != 0
        ):
            raise EspeakRenderError("eSpeak returned unsupported WAV format")
        try:
            with wave.open(io.BytesIO(normalized), "rb") as wav_file:
                if (
                    wav_file.getcomptype() != "NONE"
                    or wav_file.getnchannels() != channels
                    or wav_file.getsampwidth() != sample_width
                    or wav_file.getframerate() != sample_rate
                ):
                    raise EspeakRenderError("eSpeak returned unsupported WAV format")
                frames = wav_file.readframes(wav_file.getnframes())
        except (wave.Error, EOFError) as exc:
            raise EspeakRenderError("eSpeak returned malformed WAV data") from exc
        if len(frames) != data_size:
            raise EspeakRenderError("eSpeak returned incomplete WAV frames")
        return bytes(normalized)
