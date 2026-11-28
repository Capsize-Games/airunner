"""Unit tests for the espeak WAV normalization helpers.

_scan_wav_chunks and _validate_wav_format were extracted to keep
_normalize_wav within the long-function threshold. These tests pin
the chunk walk, the size repair, and the format consistency rules.
"""

import struct

import pytest

from airunner_services.runtimes.espeak_cli_renderer import (
    EspeakCliRenderer,
    EspeakRenderError,
)


def _fmt_chunk(channels=1, rate=22050, bits=16, audio_format=1):
    block_align = channels * (bits // 8)
    byte_rate = rate * block_align
    payload = struct.pack(
        "<HHIIHH",
        audio_format,
        channels,
        rate,
        byte_rate,
        block_align,
        bits,
    )
    return b"fmt " + struct.pack("<I", len(payload)) + payload


def _wav(fmt=None, data=b"1234", extra_chunks=b""):
    fmt = fmt if fmt is not None else _fmt_chunk()
    body = (
        b"WAVE"
        + fmt
        + extra_chunks
        + b"data"
        + struct.pack("<I", len(data))
        + data
    )
    return b"RIFF" + struct.pack("<I", len(body)) + body


def test_scan_finds_fmt_and_data():
    normalized = bytearray(_wav())
    fmt, data_size = EspeakCliRenderer._scan_wav_chunks(normalized)
    assert fmt[1] == 1  # channels
    assert fmt[2] == 22050  # sample rate
    assert data_size == 4


def test_scan_repairs_truncated_data_size():
    wav_bytes = _wav(data=b"1234")
    # Corrupt the declared data size to something larger than available.
    broken = bytearray(wav_bytes)
    data_off = wav_bytes.index(b"data") + 4
    struct.pack_into("<I", broken, data_off, 9999)
    fmt, data_size = EspeakCliRenderer._scan_wav_chunks(broken)
    assert data_size == 4
    assert struct.unpack_from("<I", broken, data_off)[0] == 4


def test_scan_rejects_oversize_non_data_chunk():
    fmt = _fmt_chunk()
    bogus = b"BOGU" + struct.pack("<I", 9999) + b"xx"
    buf = bytearray(
        b"WAVE" + fmt + bogus
    )
    with pytest.raises(EspeakRenderError):
        EspeakCliRenderer._scan_wav_chunks(buf)


def test_scan_rejects_short_fmt_chunk():
    short = b"fmt " + struct.pack("<I", 4) + b"1234"
    buf = bytearray(b"WAVE" + short + b"xxxx")
    with pytest.raises(EspeakRenderError):
        EspeakCliRenderer._scan_wav_chunks(buf)


def test_validate_accepts_consistent_params():
    fmt = (1, 1, 22050, 44100, 2, 16)
    assert EspeakCliRenderer._validate_wav_format(fmt, 100) == (1, 22050, 2)


def test_validate_rejects_bad_block_align():
    fmt = (1, 1, 22050, 44100, 3, 16)
    with pytest.raises(EspeakRenderError):
        EspeakCliRenderer._validate_wav_format(fmt, 100)


def test_validate_rejects_unsupported_bits():
    fmt = (1, 1, 22050, 44100, 2, 12)
    with pytest.raises(EspeakRenderError):
        EspeakCliRenderer._validate_wav_format(fmt, 100)


def test_validate_rejects_misaligned_data_size():
    fmt = (1, 1, 22050, 44100, 2, 16)
    with pytest.raises(EspeakRenderError):
        EspeakCliRenderer._validate_wav_format(fmt, 101)


def test_normalize_wav_roundtrip():
    wav_bytes = _wav(data=b"12345678")
    out = EspeakCliRenderer._normalize_wav(wav_bytes)
    assert out[:4] == b"RIFF" and out[8:12] == b"WAVE"
    assert len(out) == len(wav_bytes)


def test_normalize_wav_rejects_garbage():
    with pytest.raises(EspeakRenderError):
        EspeakCliRenderer._normalize_wav(b"not a wav file at all.....")
