from contextlib import contextmanager


def test_import_document_uses_darklock_user_override(monkeypatch, tmp_path):
    """User-selected imports should temporarily allow the source path."""
    from airunner.components.documents import document_import as module

    source_path = tmp_path / "source.pdf"
    source_path.write_bytes(b"pdf-data")
    destination_root = tmp_path / "library"
    destination_root.mkdir()

    override_calls = []
    created_records = []

    @contextmanager
    def fake_override(paths=None, allow_any=False):
        override_calls.append(list(paths or []))
        yield

    class FakeRestrictOSAccess:
        def user_override(self, paths=None, allow_any=False):
            return fake_override(paths=paths, allow_any=allow_any)

    monkeypatch.setattr(module, "RestrictOSAccess", FakeRestrictOSAccess)
    monkeypatch.setattr(
        module.Document.objects,
        "filter_by",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        module.Document.objects,
        "create",
        lambda **kwargs: created_records.append(kwargs),
    )

    imported_path = module.import_document_to_library(
        str(source_path),
        str(destination_root),
    )

    assert override_calls == [[str(source_path)]]
    assert imported_path == str(destination_root / source_path.name)
    assert created_records == [
        {
            "path": str(destination_root / source_path.name),
            "active": False,
            "indexed": False,
        }
    ]
    assert (destination_root / source_path.name).read_bytes() == b"pdf-data"


def test_rag_document_suffixes_include_mobi():
    """MOBI files should be accepted anywhere RAG documents are filtered."""
    from airunner.components.documents import document_import as module

    assert ".mobi" in module.rag_document_suffixes()
    assert module.is_rag_document_path("/tmp/book.mobi") is True