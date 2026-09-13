"""Regression tests for release issue D02.

Proves temporary downloads are tied to an immutable server identity and
promoted safely:

- An interrupted-then-resumed download reconstructs the exact original
  bytes (real Range/If-Match-style resume against a fake transport).
- A 206 response whose identity (ETag) no longer matches the partial
  file's recorded identity is never appended to — the stale partial is
  discarded and the file is re-fetched fresh instead of silently
  splicing old and new content together.
- A 206 response with an invalid/mismatched Content-Range is rejected
  the same way.
- An unknown expected size (file_size <= 0, e.g. a failed HEAD request)
  never lets an arbitrary pre-existing temp file be treated as already
  complete and promoted.
- Cancellation leaves the partial temp file in place (resumable) and
  never touches an existing valid destination file.
- Promotion uses a single atomic os.replace(), not delete-then-rename.
- A partial file with no recorded identity is never trusted just
  because the current response also lacks an identity header (fail
  closed, not open, on unknown provenance).
- The "already complete" shortcut (existing temp size >= expected size)
  verifies identity via a real network request before promoting; it
  never promotes a same-sized stale/corrupt file with zero verification
  and zero network calls, but still avoids a full re-download when
  identity is confirmed to match.

Uses only a fake requests.get/requests.head transport (no real network)
and tmp_path directories (no real model files).
"""

from __future__ import annotations

from unittest import mock

import pytest

from airunner_services.downloads.huggingface_download_worker import (
    HuggingFaceDownloadWorker,
)

_MODULE = "airunner_services.downloads.huggingface_download_worker"


class _FakeResponse:
    """A minimal stand-in for requests.Response used as a context manager."""

    def __init__(self, *, status_code, headers, chunks, fail_after=None):
        self.status_code = status_code
        self.headers = headers
        self._chunks = chunks
        self._fail_after = fail_after

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=8192):
        for index, chunk in enumerate(self._chunks):
            if self._fail_after is not None and index >= self._fail_after:
                raise ConnectionError("simulated dropped connection")
            yield chunk


def _chunk_bytes(data: bytes, size: int = 4) -> list[bytes]:
    return [data[i : i + size] for i in range(0, len(data), size)]


@pytest.fixture()
def worker() -> HuggingFaceDownloadWorker:
    return HuggingFaceDownloadWorker()


@pytest.fixture()
def dirs(tmp_path):
    temp_dir = tmp_path / "temp"
    model_path = tmp_path / "final"
    temp_dir.mkdir()
    model_path.mkdir()
    return temp_dir, model_path


def test_interrupted_download_resumes_to_exact_bytes(worker, dirs) -> None:
    temp_dir, model_path = dirs
    full_content = b"0123456789ABCDEF" * 100  # 1600 bytes
    chunks = _chunk_bytes(full_content)
    split = len(chunks) // 2

    first_response = _FakeResponse(
        status_code=200,
        headers={
            "content-length": str(len(full_content)),
            "etag": '"v1"',
        },
        chunks=chunks,
        fail_after=split,
    )
    with mock.patch(f"{_MODULE}.requests.get", return_value=first_response):
        worker._download_file(
            repo_id="org/repo",
            filename="model.bin",
            file_size=len(full_content),
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
        )

    assert "model.bin" in worker._failed_files
    partial_bytes = (temp_dir / "model.bin").read_bytes()
    assert 0 < len(partial_bytes) < len(full_content)
    assert full_content.startswith(partial_bytes)

    resumed_worker = HuggingFaceDownloadWorker()
    remaining = full_content[len(partial_bytes) :]
    second_response = _FakeResponse(
        status_code=206,
        headers={
            "content-range": f"bytes {len(partial_bytes)}-{len(full_content) - 1}/{len(full_content)}",
            "content-length": str(len(remaining)),
            "etag": '"v1"',
        },
        chunks=_chunk_bytes(remaining),
    )
    with mock.patch(f"{_MODULE}.requests.get", return_value=second_response):
        resumed_worker._download_file(
            repo_id="org/repo",
            filename="model.bin",
            file_size=len(full_content),
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
        )

    assert (model_path / "model.bin").read_bytes() == full_content
    assert "model.bin" in resumed_worker._completed_files
    assert not (temp_dir / "model.bin").exists()
    assert not (temp_dir / "model.bin.identity").exists()


def test_changed_identity_discards_partial_and_refetches_fresh(
    worker, dirs
) -> None:
    temp_dir, model_path = dirs
    old_content = b"OLD-CONTENT-" * 20
    new_content = b"NEW-CONTENT-DIFFERENT-LENGTH-" * 15
    old_chunks = _chunk_bytes(old_content)
    split = len(old_chunks) // 2

    first_response = _FakeResponse(
        status_code=200,
        headers={"content-length": str(len(old_content)), "etag": '"v1"'},
        chunks=old_chunks,
        fail_after=split,
    )
    with mock.patch(f"{_MODULE}.requests.get", return_value=first_response):
        worker._download_file(
            repo_id="org/repo",
            filename="model.bin",
            file_size=len(old_content),
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
        )
    partial_bytes = (temp_dir / "model.bin").read_bytes()
    assert 0 < len(partial_bytes) < len(old_content)

    # The upstream file changed (different ETag) between attempts: the
    # 206 response for the old resume point must be rejected, and the
    # worker must re-fetch the whole (new) file fresh rather than
    # splicing new bytes onto the stale partial.
    mismatched_206 = _FakeResponse(
        status_code=206,
        headers={
            "content-range": f"bytes {len(partial_bytes)}-{len(old_content) - 1}/{len(old_content)}",
            "etag": '"v2-different"',
        },
        chunks=[],
    )
    fresh_full_response = _FakeResponse(
        status_code=200,
        headers={"content-length": str(len(new_content)), "etag": '"v2-different"'},
        chunks=_chunk_bytes(new_content),
    )
    resumed_worker = HuggingFaceDownloadWorker()
    with mock.patch(
        f"{_MODULE}.requests.get",
        side_effect=[mismatched_206, fresh_full_response],
    ):
        resumed_worker._download_file(
            repo_id="org/repo",
            filename="model.bin",
            file_size=len(new_content),
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
        )

    assert (model_path / "model.bin").read_bytes() == new_content
    assert "model.bin" in resumed_worker._completed_files


def test_invalid_content_range_discards_partial_and_refetches_fresh(
    worker, dirs
) -> None:
    temp_dir, model_path = dirs
    old_content = b"ABCDEFGH" * 20
    new_content = b"FRESH-FULL-CONTENT-" * 10
    old_chunks = _chunk_bytes(old_content)
    split = len(old_chunks) // 2

    first_response = _FakeResponse(
        status_code=200,
        headers={"content-length": str(len(old_content)), "etag": '"v1"'},
        chunks=old_chunks,
        fail_after=split,
    )
    with mock.patch(f"{_MODULE}.requests.get", return_value=first_response):
        worker._download_file(
            repo_id="org/repo",
            filename="model.bin",
            file_size=len(old_content),
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
        )
    partial_bytes = (temp_dir / "model.bin").read_bytes()

    # Same identity, but the Content-Range start does not match the
    # requested resume point (a proxy/cache serving the wrong slice).
    bad_range_206 = _FakeResponse(
        status_code=206,
        headers={
            "content-range": "bytes 0-9/999",
            "etag": '"v1"',
        },
        chunks=[],
    )
    fresh_full_response = _FakeResponse(
        status_code=200,
        headers={"content-length": str(len(new_content)), "etag": '"v1"'},
        chunks=_chunk_bytes(new_content),
    )
    resumed_worker = HuggingFaceDownloadWorker()
    with mock.patch(
        f"{_MODULE}.requests.get",
        side_effect=[bad_range_206, fresh_full_response],
    ):
        resumed_worker._download_file(
            repo_id="org/repo",
            filename="model.bin",
            file_size=len(new_content),
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
        )

    assert (model_path / "model.bin").read_bytes() == new_content
    assert len(partial_bytes) > 0  # sanity: there really was a partial file


def test_unknown_expected_size_never_promotes_arbitrary_temp_file(
    worker, dirs
) -> None:
    temp_dir, model_path = dirs
    (temp_dir / "model.bin").write_bytes(b"garbage-not-the-real-file")
    real_content = b"THE-REAL-FILE-CONTENT-" * 5

    # file_size <= 0 means the expected size is unknown (e.g. a failed
    # HEAD request upstream, see _download_gguf_model). The garbage temp
    # file must not be short-circuited as "already complete" just
    # because there is no size to compare it against: it must instead
    # be resumed/re-verified against a real server response, here an
    # invalid Content-Range that forces a fresh re-fetch of the real
    # content rather than promoting the garbage bytes as-is.
    invalid_range_response = _FakeResponse(
        status_code=206,
        headers={
            "content-range": "bytes 0-0/0",
            "content-length": "0",
        },
        chunks=[],
    )
    fresh_full_response = _FakeResponse(
        status_code=200,
        headers={"content-length": str(len(real_content))},
        chunks=_chunk_bytes(real_content),
    )
    with mock.patch(
        f"{_MODULE}.requests.get",
        side_effect=[invalid_range_response, fresh_full_response],
    ):
        worker._download_file(
            repo_id="org/repo",
            filename="model.bin",
            file_size=0,
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
        )

    # The garbage temp file must not have been promoted as-is; the real
    # content, freshly fetched, is what ends up at the final location.
    assert (model_path / "model.bin").read_bytes() == real_content


def test_cancellation_keeps_partial_temp_and_existing_destination(
    worker, dirs
) -> None:
    temp_dir, model_path = dirs
    (model_path / "model.bin").write_bytes(b"EXISTING-VALID-CONTENT")
    content = b"0123456789" * 50
    chunks = _chunk_bytes(content)

    def _cancel_after_first_chunk(chunk_size=8192):
        for index, chunk in enumerate(chunks):
            if index == 2:
                worker.is_cancelled = True
            yield chunk

    response = mock.MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    response.status_code = 200
    response.headers = {"content-length": str(len(content))}
    response.iter_content.side_effect = _cancel_after_first_chunk

    with mock.patch(f"{_MODULE}.requests.get", return_value=response):
        worker._download_file(
            repo_id="org/repo",
            filename="model.bin",
            file_size=len(content),
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
        )

    # Existing valid destination is untouched.
    assert (model_path / "model.bin").read_bytes() == b"EXISTING-VALID-CONTENT"
    # Partial temp state is retained (resumable), not deleted.
    assert (temp_dir / "model.bin").exists()
    assert len(temp_dir.joinpath("model.bin").read_bytes()) > 0
    assert "model.bin" not in worker._completed_files
    assert "model.bin" not in worker._failed_files


def test_no_recorded_identity_is_not_trusted_on_resume(worker, dirs) -> None:
    """A partial file with no identity sidecar (unknown provenance) must
    never be trusted just because Content-Range matches and the current
    response also lacks an identity header -- both signals being
    unavailable is not the same as being confirmed safe (release issue
    D02 review finding F3: this used to fail open, splicing new bytes
    onto the untrusted partial)."""
    temp_dir, model_path = dirs
    (temp_dir / "model.bin").write_bytes(b"OLD!")  # no .identity sidecar
    real_content = b"REALDATA"  # same length as the spliced result would be

    unsafe_206 = _FakeResponse(
        status_code=206,
        headers={"content-range": "bytes 4-7/8", "content-length": "4"},
        chunks=[b"NEW!"],
    )
    fresh_full_response = _FakeResponse(
        status_code=200,
        headers={"content-length": str(len(real_content))},
        chunks=_chunk_bytes(real_content),
    )
    with mock.patch(
        f"{_MODULE}.requests.get",
        side_effect=[unsafe_206, fresh_full_response],
    ):
        worker._download_file(
            repo_id="org/repo",
            filename="model.bin",
            file_size=len(real_content),
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
        )

    # Must be the freshly re-fetched content, never the spliced
    # b"OLD!NEW!" that fail-open behavior would have produced.
    assert (model_path / "model.bin").read_bytes() == real_content


def test_previously_recorded_empty_identity_is_not_trusted_either(
    worker, dirs
) -> None:
    """A sidecar that exists but recorded "no identity was available" on
    a prior attempt (stored_identity == "") must not be treated as
    matching a response that also lacks an identity header. Comparing
    two empty values as equal was a second fail-open path, functionally
    identical to the original bug, for any server that never sends
    ETag/Last-Modified: the first attempt writes an empty sidecar
    (rather than none at all), and every subsequent resume would then
    be trusted regardless of whether the remote content actually
    changed (second-review finding)."""
    temp_dir, model_path = dirs
    (temp_dir / "model.bin").write_bytes(b"OLD!")
    (temp_dir / "model.bin.identity").write_text("", encoding="utf-8")
    real_content = b"REALDATA"

    unsafe_206 = _FakeResponse(
        status_code=206,
        headers={"content-range": "bytes 4-7/8", "content-length": "4"},
        chunks=[b"NEW!"],
    )
    fresh_full_response = _FakeResponse(
        status_code=200,
        headers={"content-length": str(len(real_content))},
        chunks=_chunk_bytes(real_content),
    )
    with mock.patch(
        f"{_MODULE}.requests.get",
        side_effect=[unsafe_206, fresh_full_response],
    ):
        worker._download_file(
            repo_id="org/repo",
            filename="model.bin",
            file_size=len(real_content),
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
        )

    assert (model_path / "model.bin").read_bytes() == real_content


def test_already_complete_shortcut_verifies_identity_before_promoting(
    worker, dirs
) -> None:
    """A same-sized temp file with no recorded identity must not be
    promoted with zero verification and zero network calls just because
    its byte count matches file_size (release issue D02 review finding
    F3)."""
    temp_dir, model_path = dirs
    (temp_dir / "model.bin").write_bytes(b"STALE123")  # 8 bytes, no sidecar
    real_content = b"REALDATA"  # also 8 bytes, but genuinely different

    head_response = _FakeResponse(status_code=200, headers={}, chunks=[])
    fresh_full_response = _FakeResponse(
        status_code=200,
        headers={"content-length": str(len(real_content))},
        chunks=_chunk_bytes(real_content),
    )
    with mock.patch(
        f"{_MODULE}.requests.head", return_value=head_response
    ) as mock_head, mock.patch(
        f"{_MODULE}.requests.get", return_value=fresh_full_response
    ) as mock_get:
        worker._download_file(
            repo_id="org/repo",
            filename="model.bin",
            file_size=len(real_content),
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
        )

    assert mock_head.called
    assert mock_get.called
    assert (model_path / "model.bin").read_bytes() == real_content


def test_already_complete_shortcut_promotes_when_identity_matches(
    worker, dirs
) -> None:
    """The already-complete shortcut still avoids a full re-download when
    the temp file's recorded identity matches the server's current
    identity -- the verification fix must not regress this optimization
    into always re-downloading."""
    temp_dir, model_path = dirs
    content = b"GOODDATA"
    (temp_dir / "model.bin").write_bytes(content)
    (temp_dir / "model.bin.identity").write_text('"v1"', encoding="utf-8")

    head_response = _FakeResponse(
        status_code=200, headers={"etag": '"v1"'}, chunks=[]
    )
    with mock.patch(
        f"{_MODULE}.requests.head", return_value=head_response
    ), mock.patch(
        f"{_MODULE}.requests.get",
        side_effect=AssertionError(
            "must not re-download when identity matches"
        ),
    ):
        worker._download_file(
            repo_id="org/repo",
            filename="model.bin",
            file_size=len(content),
            temp_dir=temp_dir,
            model_path=model_path,
            api_key="",
        )

    assert (model_path / "model.bin").read_bytes() == content
    assert "model.bin" in worker._completed_files


def test_promotion_uses_atomic_replace_not_delete_then_rename(
    worker, dirs, monkeypatch
) -> None:
    temp_dir, model_path = dirs
    (temp_dir / "model.bin").write_bytes(b"new content")
    (model_path / "model.bin").write_bytes(b"old content")

    calls = []
    real_replace = __import__("os").replace

    def _tracking_replace(src, dst):
        calls.append((str(src), str(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(f"{_MODULE}.os.replace", _tracking_replace)

    ok = worker._verify_and_finalize(
        temp_path=temp_dir / "model.bin",
        final_path=model_path / "model.bin",
        filename="model.bin",
        expected_sha256=None,
    )

    assert ok is True
    assert len(calls) == 1
    assert (model_path / "model.bin").read_bytes() == b"new content"
