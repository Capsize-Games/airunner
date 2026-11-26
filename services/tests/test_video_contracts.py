"""Happy/sad/bad tests for LTX video contracts + MCP payloads."""

import pytest

from airunner_services.mcp.video_payloads import build_video_payload
from airunner_services.video.contracts import (
    VideoGenerationRequest,
    validate_frame_count,
)


def test_happy_default_request_is_720p_97_frames():
    req = VideoGenerationRequest(prompt="a tram in rain")
    assert (req.width, req.height) == (1280, 720)
    assert req.num_frames == 97 and req.fps == 24


@pytest.mark.parametrize("frames", [9, 81, 97, 121, 241])
def test_happy_frame_lattice_accepted(frames):
    assert validate_frame_count(frames) == frames


@pytest.mark.parametrize("frames", [0, 8, 96, 100, 242, -97])
def test_sad_bad_frame_counts_rejected(frames):
    with pytest.raises(ValueError):
        validate_frame_count(frames)


def test_bad_dimension_not_multiple_of_16_rejected():
    with pytest.raises(Exception):
        VideoGenerationRequest(prompt="x", width=1281)


def test_bad_empty_prompt_rejected():
    with pytest.raises(Exception):
        VideoGenerationRequest(prompt="")


def test_bad_steps_above_distilled_range_rejected():
    with pytest.raises(Exception):
        VideoGenerationRequest(prompt="x", steps=64)


def test_mcp_payload_happy_and_bad_checkpoint():
    payload = build_video_payload("a tram in rain")
    assert payload["num_frames"] == 97
    with pytest.raises(ValueError):
        build_video_payload("a tram", checkpoint="int4")
    with pytest.raises(ValueError):
        build_video_payload("a tram", num_frames=96)
