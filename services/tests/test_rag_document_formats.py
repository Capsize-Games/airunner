"""Service RAG format allow-list and loader-routing regressions."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from airunner_services.llm.managers.agent.document_loader import (
    _FILE_LOADERS,
    load_documents_from_file,
)
from airunner_services.llm.managers.request_rag_preparation import (
    load_rag_document_payload,
    prepare_request_rag,
)
from airunner_services.llm.tools.rag_tools_helpers._shared import (
    SUPPORTED_DOCUMENT_EXTENSIONS as TOOL_SUPPORTED_EXTENSIONS,
)
from airunner_services.llm.workers.mixins.rag_indexing_mixin import (
    RAGIndexingMixin,
)
from airunner_services.runtimes.document_formats import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    UNSUPPORTED_BINARY_DOCUMENT_EXTENSIONS,
)


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TIME_MACHINE_MOBI = (
    _PROJECT_ROOT
    / "services"
    / "tests"
    / "fixtures"
    / "rag_formats"
    / "the-time-machine"
    / "source.mobi"
)


def test_supported_format_inventory_matches_tools_and_real_loaders() -> None:
    """Every advertised format has a loader or the text fallback."""
    assert TOOL_SUPPORTED_EXTENSIONS == SUPPORTED_DOCUMENT_EXTENSIONS
    assert set(_FILE_LOADERS) | {".txt"} == set(SUPPORTED_DOCUMENT_EXTENSIONS)
    assert not set(UNSUPPORTED_BINARY_DOCUMENT_EXTENSIONS) & set(
        SUPPORTED_DOCUMENT_EXTENSIONS
    )


def test_worker_accepts_html_and_mobi_and_rejects_unparsed_office_files(
    tmp_path: Path,
) -> None:
    documents = tmp_path / "documents"
    documents.mkdir()
    worker = RAGIndexingMixin()
    worker.path_settings = SimpleNamespace(
        documents_path=str(documents), base_path=str(tmp_path)
    )
    worker.logger = SimpleNamespace(warning=lambda *_args, **_kwargs: None)
    worker.emit_signal = lambda *_args, **_kwargs: None

    for extension in (".html", ".htm", ".mobi"):
        candidate = documents / f"sample{extension}"
        candidate.write_bytes(b"fixture bytes")
        assert worker._validate_document_path(str(candidate)) == str(candidate)

    for extension in sorted(UNSUPPORTED_BINARY_DOCUMENT_EXTENSIONS):
        candidate = documents / f"sample{extension}"
        candidate.write_bytes(b"PK\x03\x04binary container")
        assert worker._validate_document_path(str(candidate)) is None


def test_html_loader_extracts_visible_text_and_omits_scripts(tmp_path: Path) -> None:
    path = tmp_path / "source.html"
    path.write_text(
        "<html><body><h1>Harbor Notes</h1>"
        "<p>The blue heron nests beside the north pier.</p>"
        "<script>secret injected phrase</script></body></html>",
        encoding="utf-8",
    )

    documents = load_documents_from_file(str(path))

    assert len(documents) == 1
    assert "blue heron" in documents[0].page_content
    assert "secret injected phrase" not in documents[0].page_content
    assert documents[0].metadata["file_type"] == ".html"


def test_reviewed_mobi_fixture_uses_the_mobi_loader() -> None:
    """Exercise the retained public-domain MOBI fixture through its loader."""
    documents = load_documents_from_file(str(_TIME_MACHINE_MOBI))

    assert documents
    body = "\n".join(document.page_content for document in documents)
    assert "Time Traveller" in body
    assert documents[0].metadata["file_type"] == ".mobi"


@pytest.mark.parametrize("extension", sorted(UNSUPPORTED_BINARY_DOCUMENT_EXTENSIONS))
def test_unparsed_office_containers_fail_closed(
    tmp_path: Path, extension: str
) -> None:
    path = tmp_path / f"binary{extension}"
    path.write_bytes(b"PK\x03\x04not plain text")

    with pytest.raises(ValueError, match="Unsupported document format"):
        load_documents_from_file(str(path))


def test_request_payload_routes_mobi_bytes_and_html_bytes() -> None:
    calls = []

    class FakeRagManager:
        def load_bytes_into_rag(self, content_bytes, *, source_name, file_ext):
            calls.append(("bytes", bytes(content_bytes), source_name, file_ext))

        def load_html_into_rag(self, content, *, source_name):
            calls.append(("html", content, source_name))

    manager = FakeRagManager()
    load_rag_document_payload(
        manager,
        {"file_type": ".mobi", "content": b"mobi bytes", "source_name": "mobi"},
    )
    load_rag_document_payload(
        manager,
        {
            "file_type": ".html",
            "content": b"<p>bird</p>",
            "source_name": "html",
        },
    )

    assert calls == [
        ("bytes", b"mobi bytes", "mobi", ".mobi"),
        ("html", "<p>bird</p>", "html"),
    ]


@pytest.mark.parametrize("file_type, expected_extension", [("pdf", ".pdf"), ("mobi", ".mobi")])
def test_request_payload_normalizes_dotless_binary_formats(
    file_type: str, expected_extension: str
) -> None:
    calls = []

    class FakeRagManager:
        def load_bytes_into_rag(self, content_bytes, *, source_name, file_ext):
            calls.append((bytes(content_bytes), source_name, file_ext))
            return "uploaded-id"

    doc_id = load_rag_document_payload(
        FakeRagManager(),
        {
            "file_type": file_type,
            "content": b"binary document",
            "source_name": f"fixture{expected_extension}",
        },
    )

    assert doc_id == "uploaded-id"
    assert calls == [
        (b"binary document", f"fixture{expected_extension}", expected_extension)
    ]


def test_request_payload_infers_binary_format_from_source_name() -> None:
    calls = []

    class FakeRagManager:
        def load_bytes_into_rag(self, content_bytes, *, source_name, file_ext):
            calls.append((bytes(content_bytes), source_name, file_ext))
            return "uploaded-id"

    doc_id = load_rag_document_payload(
        FakeRagManager(),
        {"content": b"pdf bytes", "source_name": "manual.pdf"},
    )

    assert doc_id == "uploaded-id"
    assert calls == [(b"pdf bytes", "manual.pdf", ".pdf")]


@pytest.mark.parametrize("file_type", [".txt", ".md"])
def test_request_payload_decodes_text_bytes(file_type: str) -> None:
    calls = []

    class FakeRagManager:
        def load_html_into_rag(self, content, *, source_name):
            calls.append((content, source_name))
            return "uploaded-text-id"

    doc_id = load_rag_document_payload(
        FakeRagManager(),
        {
            "file_type": file_type,
            "content": "Selected bytes contain readable text.".encode("utf-8"),
            "source_name": f"notes{file_type}",
        },
    )

    assert doc_id == "uploaded-text-id"
    assert calls == [("Selected bytes contain readable text.", f"notes{file_type}")]


def test_request_payload_rejects_path_only_zim_and_dotless_office() -> None:
    manager = SimpleNamespace(
        load_bytes_into_rag=lambda *_args, **_kwargs: pytest.fail(
            "ZIM and Office payloads must not use the binary loader"
        ),
        load_html_into_rag=lambda *_args, **_kwargs: pytest.fail(
            "ZIM and Office payloads must not use the HTML fallback"
        ),
    )

    for payload in (
        {"file_type": ".zim", "content": b"zim bytes"},
        {"file_type": "docx", "content": b"PK\x03\x04binary"},
    ):
        with pytest.raises(ValueError):
            load_rag_document_payload(manager, payload)


def test_request_payload_rejects_unparsed_office_containers() -> None:
    manager = SimpleNamespace(
        load_bytes_into_rag=lambda *_args, **_kwargs: pytest.fail(
            "unsupported Office bytes must not enter the text/HTML path"
        ),
        load_html_into_rag=lambda *_args, **_kwargs: pytest.fail(
            "unsupported Office bytes must not enter the text/HTML path"
        ),
    )

    with pytest.raises(ValueError, match="Unsupported document format"):
        load_rag_document_payload(
            manager,
            {"file_type": ".docx", "content": b"PK\x03\x04binary"},
        )


def test_explicit_request_missing_file_fails_preparation(tmp_path: Path) -> None:
    manager = SimpleNamespace(
        ensure_indexed_files=lambda _paths: pytest.fail(
            "a missing source must fail before index dispatch"
        )
    )

    with pytest.raises(ValueError, match="does not exist"):
        prepare_request_rag(
            manager,
            SimpleNamespace(rag_files=[str(tmp_path / "missing.txt")]),
            [],
        )


@pytest.mark.parametrize(
    "extension", sorted(UNSUPPORTED_BINARY_DOCUMENT_EXTENSIONS)
)
def test_explicit_request_unsupported_file_fails_preparation(
    tmp_path: Path, extension: str
) -> None:
    path = tmp_path / f"unsupported{extension}"
    path.write_bytes(b"PK\x03\x04binary")
    manager = SimpleNamespace(
        ensure_indexed_files=lambda _paths: pytest.fail(
            "an unsupported file must fail before index dispatch"
        )
    )

    with pytest.raises(ValueError, match="Unsupported document format"):
        prepare_request_rag(
            manager, SimpleNamespace(rag_files=[str(path)]), []
        )


def test_explicit_request_false_index_result_fails_preparation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "selected.txt"
    path.write_text("selected source", encoding="utf-8")
    calls = []
    manager = SimpleNamespace(
        ensure_indexed_files=lambda paths: calls.append(paths) or False
    )

    with pytest.raises(ValueError, match="Could not index"):
        prepare_request_rag(
            manager, SimpleNamespace(rag_files=[str(path)]), []
        )
    assert calls == [[str(path)]]


def test_explicit_request_unsupported_payload_fails_preparation() -> None:
    manager = SimpleNamespace(
        load_html_into_rag=lambda *_args, **_kwargs: pytest.fail(
            "unsupported Office payload must not use the HTML fallback"
        ),
        load_bytes_into_rag=lambda *_args, **_kwargs: pytest.fail(
            "unsupported Office payload must not use the binary loader"
        ),
    )

    with pytest.raises(ValueError, match="Unsupported document format"):
        prepare_request_rag(
            manager,
            SimpleNamespace(
                rag_files=[
                    {
                        "file_type": ".docx",
                        "source_name": "upload.docx",
                        "content": b"PK\x03\x04binary",
                    }
                ]
            ),
            [],
        )


def test_auto_attached_index_failure_keeps_best_effort_fallback(
    monkeypatch,
) -> None:
    candidates = ["/docs/auto.txt"]
    calls = []
    monkeypatch.setattr(
        "airunner_services.llm.managers.request_rag_preparation._indexed_rag_candidates",
        lambda limit: candidates[:limit],
    )
    manager = SimpleNamespace(
        ensure_indexed_files=lambda paths: calls.append(paths) or False,
        logger=SimpleNamespace(
            debug=lambda *_args, **_kwargs: None,
            info=lambda *_args, **_kwargs: None,
        ),
    )
    request = SimpleNamespace(rag_files=None)

    assert prepare_request_rag(manager, request, ["search"]) == ()
    assert request.rag_files == candidates
    assert calls == [candidates]
