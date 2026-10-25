"""Regression tests for audit wave-2 art + data fixes.

Covers clamps, decode guards, confinement, allowlists, redaction,
paging/delete guards, URL validation, and the single-head merge.
"""

from __future__ import annotations

import os
import sys
import zipfile

import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

from airunner_services.art.managers.rmbg.rmbg_model_manager import (
    RMBGModelManager,
    RMBGModelSpec,
    hash_model_code_files,
)
from airunner_services.art.managers.stablediffusion import image_request
from airunner_services.art.managers.stablediffusion import (
    image_to_image_request,
)
from airunner_services.art.managers.stablediffusion import model_loader
from airunner_services.art.managers.stablediffusion import (
    download_huggingface as art_hf,
)
from airunner_services.art.managers.stablediffusion.mixins import (
    sd_pipeline_management_mixin as pipe_mixin,
)
from airunner_services.art.managers.zimage.mixins import (
    zimage_single_file_transformer_helper as zsf_helper,
)
from airunner_services.art.managers.zimage.native import (
    zimage_text_encoder_loader_helper as ztel_helper,
)
from airunner_services.art.runtime_enums import ModelStatus


class _GuardBase(DeclarativeBase):
    pass


class _GuardRow(_GuardBase):
    __tablename__ = "guard_rows"

    id = Column(Integer, primary_key=True)
    name = Column(String)

    def to_dataclass(self):
        return {"id": self.id, "name": self.name}


class TestImageRequestClamps:
    def test_steps_clamped(self) -> None:
        cls = image_request.ImageRequest
        assert cls(steps=9999).steps == 150
        assert cls(steps=-5).steps == 1
        assert cls(steps=20).steps == 20

    def test_dimensions_clamped_and_snapped(self) -> None:
        cls = image_request.ImageRequest
        assert cls(width=7, height=7).width == 128
        assert cls(width=4096, height=4096).height == 2048
        assert cls(width=1000, height=1000).width == 1000 - (1000 % 8)
        assert cls(width=1023, height=1023).width % 8 == 0

    def test_batch_counts_clamped(self) -> None:
        cls = image_request.ImageRequest
        assert cls(n_samples=999).n_samples == 16
        assert cls(n_samples=0).n_samples == 1
        assert cls(images_per_batch=64).images_per_batch == 8
        assert cls(images_per_batch=0).images_per_batch == 1

    def test_strength_clamped(self) -> None:
        cls = image_request.ImageRequest
        assert cls(strength=5.0).strength == 1.0
        assert cls(strength=-2.0).strength == 0.0

    def test_batch_cap_constant(self) -> None:
        assert image_request.MAX_BATCHES_PER_REQUEST <= 64


class TestImageToImageStrength:
    def test_create_clamps_strength(self) -> None:
        make = image_to_image_request.create_image_to_image_request
        assert make("img", "prompt", strength=9.0).strength == 1.0
        assert make("img", "prompt", strength=-1.0).strength == 0.0

    def test_validate_rejects_out_of_range(self) -> None:
        mod = image_to_image_request
        good = mod.ImageToImageRequest(
            input_image="img", prompt="p", strength=0.5
        )
        assert mod.validate_image_to_image_request(good) is True
        bad = mod.ImageToImageRequest(
            input_image="img", prompt="p", strength=7.0
        )
        assert mod.validate_image_to_image_request(bad) is False


class TestBinaryToImageGuards:
    def test_raw_header_caps_refused(self) -> None:
        from airunner_services.utils.image.convert_binary_to_image import (
            RAW_MAGIC,
            convert_binary_to_image,
        )

        evil = RAW_MAGIC + (40000).to_bytes(4, "big") + (1).to_bytes(
            4, "big"
        )
        assert convert_binary_to_image(evil) is None
        negative = RAW_MAGIC + (0).to_bytes(4, "big") + (8).to_bytes(
            4, "big"
        )
        assert convert_binary_to_image(negative) is None

    def test_raw_pixel_budget_refused(self) -> None:
        from airunner_services.utils.image.convert_binary_to_image import (
            RAW_MAGIC,
            convert_binary_to_image,
        )

        # 8000x8000 = 64M pixels > 50M cap, header only (no payload).
        evil = RAW_MAGIC + (8000).to_bytes(4, "big") + (8000).to_bytes(
            4, "big"
        )
        assert convert_binary_to_image(evil) is None

    def test_oversized_png_header_refused(self) -> None:
        import struct
        import zlib

        from airunner_services.utils.image.convert_binary_to_image import (
            convert_binary_to_image,
        )

        ihdr = struct.pack(">IIBBBBB", 20000, 20000, 8, 2, 0, 0, 0)
        chunk = b"IHDR" + ihdr
        png = (
            b"\x89PNG\r\n\x1a\n"
            + struct.pack(">I", 13)
            + chunk
            + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
        )
        assert convert_binary_to_image(png) is None

    def test_valid_png_decodes(self, tmp_path) -> None:
        from PIL import Image

        from airunner_services.utils.image.convert_binary_to_image import (
            convert_binary_to_image,
        )

        target = tmp_path / "tiny.png"
        Image.new("RGB", (4, 4), (1, 2, 3)).save(target)
        img = convert_binary_to_image(target.read_bytes())
        assert img is not None
        assert img.size == (4, 4)


class TestDeleteImageConfinement:
    def test_deletes_inside_base(self, tmp_path) -> None:
        from airunner_services.utils.image.delete_image import delete_image

        victim = tmp_path / "a.png"
        victim.write_bytes(b"x")
        assert delete_image(str(victim), base_dir=str(tmp_path)) is True
        assert not victim.exists()

    def test_refuses_outside_base(self, tmp_path) -> None:
        from airunner_services.utils.image.delete_image import delete_image

        base = tmp_path / "images"
        base.mkdir()
        outside = tmp_path / "secret.png"
        outside.write_bytes(b"x")
        assert delete_image(str(outside), base_dir=str(base)) is False
        assert outside.exists()

    def test_refuses_missing(self, tmp_path) -> None:
        from airunner_services.utils.image.delete_image import delete_image

        assert (
            delete_image(str(tmp_path / "nope.png"), base_dir=str(tmp_path))
            is False
        )


class TestSchedulerAllowlist:
    def test_allows_known_scheduler(self) -> None:
        import logging

        assert (
            model_loader.resolve_scheduler_class(
                "DDIMScheduler", logging.getLogger("t")
            )
            is not None
        )
        assert (
            model_loader.resolve_scheduler_class(
                "FlowMatchEulerDiscreteScheduler",
                logging.getLogger("t"),
            )
            is not None
        )

    def test_refuses_arbitrary_class(self) -> None:
        import logging

        assert (
            model_loader.resolve_scheduler_class(
                "os", logging.getLogger("t")
            )
            is None
        )
        assert (
            model_loader.resolve_scheduler_class(
                "SchedulerMixin", logging.getLogger("t")
            )
            is None
        )


class TestHuggingFaceRepoId:
    def test_valid_repo_id(self) -> None:
        assert art_hf.validate_repo_id("owner/model-name_2") == (
            "owner/model-name_2"
        )

    def test_invalid_repo_ids(self) -> None:
        for bad in ["", "../etc", "/abs", "no-slash", "a/b/c", "a/.."]:
            with pytest.raises(ValueError):
                art_hf.validate_repo_id(bad)

    def test_downloader_validates(self) -> None:
        with pytest.raises(ValueError):
            art_hf.HuggingFaceDownloader().download("../../etc", "v")

    def test_prepare_request_validates(self) -> None:
        from airunner_services.downloads.huggingface import (
            prepare_huggingface_download_request,
        )

        with pytest.raises(ValueError):
            prepare_huggingface_download_request("../evil")


class TestCivitaiValidation:
    def test_parse_rejects_foreign_host(self) -> None:
        from airunner_services.downloads.civitai import parse_civitai_url

        with pytest.raises(ValueError):
            parse_civitai_url("https://evil.example.com/models/1234")

    def test_parse_accepts_civitai_host(self) -> None:
        from airunner_services.downloads.civitai import parse_civitai_url

        parsed = parse_civitai_url(
            "https://civitai.com/models/1234?modelVersionId=56"
        )
        assert parsed["model_id"] == "1234"
        assert parsed["model_version_id"] == "56"

    def test_fetch_rejects_nonnumeric_id(self) -> None:
        from airunner_services.downloads.civitai import fetch_model_info

        with pytest.raises(ValueError):
            fetch_model_info("../../etc/passwd")

    def test_search_rejects_bad_limit(self) -> None:
        from airunner_services.downloads.civitai import search_models

        with pytest.raises(ValueError):
            search_models(limit=9999)

    def test_fetch_validates_url_before_request(
        self, monkeypatch
    ) -> None:
        import airunner_services.downloads.civitai as civitai

        seen: dict = {}

        def fake_validate(url: str) -> None:
            seen["url"] = url

        def fake_get(url, **kwargs):
            seen["fetched"] = url

            class _Resp:
                def raise_for_status(self) -> None:
                    return None

                def json(self):
                    return {}

            return _Resp()

        monkeypatch.setattr(
            "airunner_services.url_safety.validate_url_for_fetch",
            fake_validate,
        )
        monkeypatch.setattr(civitai.requests, "get", fake_get)
        civitai.fetch_model_info("1234")
        assert seen["url"].startswith("https://civitai.com/api/v1/models/")


class TestRMBGCodePinning:
    def test_matching_pins_pass(self, tmp_path) -> None:
        (tmp_path / "BiRefNet_config.py").write_text("CONFIG = 1\n")
        (tmp_path / "birefnet.py").write_text("MODEL = 1\n")
        pins = hash_model_code_files(str(tmp_path))
        manager = RMBGModelManager(
            RMBGModelSpec(code_hashes=dict(pins))
        )
        manager._verify_model_code(str(tmp_path))

    def test_mismatch_refuses(self, tmp_path) -> None:
        (tmp_path / "BiRefNet_config.py").write_text("CONFIG = 1\n")
        (tmp_path / "birefnet.py").write_text("MODEL = 1\n")
        manager = RMBGModelManager(
            RMBGModelSpec(code_hashes={"BiRefNet_config.py": "0" * 64})
        )
        with pytest.raises(ImportError):
            manager._verify_model_code(str(tmp_path))

    def test_unpinned_warns(self, tmp_path, caplog) -> None:
        import logging

        (tmp_path / "BiRefNet_config.py").write_text("CONFIG = 1\n")
        (tmp_path / "birefnet.py").write_text("MODEL = 1\n")
        with caplog.at_level(logging.WARNING):
            RMBGModelManager()._verify_model_code(str(tmp_path))
        assert "not hash-pinned" in caplog.text


class TestQuantizedCacheSweep:
    def test_sweep_removes_only_stale_tmp(self, tmp_path) -> None:
        import time

        stale = tmp_path / "tmp-quant-abc"
        stale.mkdir()
        fresh = tmp_path / "tmp-quant-fresh"
        fresh.mkdir()
        keep = tmp_path / "deadbeef-4bit"
        keep.mkdir()
        old = time.time() - 100000
        os.utime(stale, (old, old))
        removed = ztel_helper.sweep_stale_tmp_dirs(
            cache_root=tmp_path, max_age_seconds=60
        )
        assert removed == 1
        assert not stale.exists()
        assert fresh.exists()
        assert keep.exists()

    def test_sweep_missing_root(self, tmp_path) -> None:
        assert (
            ztel_helper.sweep_stale_tmp_dirs(
                cache_root=tmp_path / "absent"
            )
            == 0
        )


class TestWeightsMemoryGuard:
    def test_refuses_when_file_exceeds_ram(
        self, tmp_path, monkeypatch
    ) -> None:
        target = tmp_path / "model.safetensors"
        target.write_bytes(b"0" * 8)
        monkeypatch.setattr(
            zsf_helper.os.path, "getsize", lambda path: 10**12
        )
        monkeypatch.setattr(
            zsf_helper, "_available_ram_bytes", lambda: 1024
        )
        with pytest.raises(MemoryError):
            zsf_helper._check_weights_fit_in_memory(str(target))

    def test_missing_file_raises(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            zsf_helper._check_weights_fit_in_memory(
                str(tmp_path / "absent.safetensors")
            )


class TestSingleFileRestriction:
    def _mixin(self, model_path: str):
        mixin = pipe_mixin.SDPipelineManagementMixin()

        class _Pipe:
            @classmethod
            def from_single_file(cls, *args, **kwargs):
                return "PIPE"

        mixin._pipeline_class = _Pipe
        mixin.model_path = model_path
        mixin.use_from_single_file = True

        class _Logger:
            def info(self, *a, **k):
                return None

            def error(self, *a, **k):
                return None

        mixin.logger = _Logger()
        return mixin

    def test_pickle_extension_refused(self) -> None:
        mixin = self._mixin("/models/whatever.ckpt")
        with pytest.raises(ValueError):
            mixin._set_pipe("/cfg", {})

    def test_safetensors_allowed(self) -> None:
        mixin = self._mixin("/models/whatever.safetensors")
        mixin._set_pipe("/cfg", {})
        assert mixin._pipe == "PIPE"

    def test_oom_marks_failed_and_unloads(self) -> None:
        import torch

        mixin = pipe_mixin.SDPipelineManagementMixin()
        calls: dict = {}

        class _Pipe:
            def to(self, device):
                raise torch.OutOfMemoryError("out of memory")

        class _Logger:
            def info(self, *a, **k):
                return None

            def error(self, *a, **k):
                calls["logged"] = True

        mixin._pipe = _Pipe()
        mixin._device = "cuda"
        mixin.logger = _Logger()
        mixin.model_type = "txt2img"
        mixin.change_model_status = lambda *a: calls.setdefault(
            "status", a[1]
        )
        mixin._unload_pipe = lambda: calls.setdefault("unloaded", True)
        mixin._move_pipe_to_device()
        assert calls.get("status") == ModelStatus.FAILED
        assert calls.get("unloaded") is True


_ZIMAGE_PRETRAINED = (
    "services/src/airunner_services/art/managers/zimage/mixins/"
    "zimage_pretrained_loader_helper.py"
)
_ZIMAGE_SINGLE_FILE = (
    "services/src/airunner_services/art/managers/zimage/mixins/"
    "zimage_single_file_transformer_helper.py"
)


class TestTrustRemoteCodePinned:
    @pytest.mark.parametrize(
        "module_path",
        [_ZIMAGE_PRETRAINED, _ZIMAGE_SINGLE_FILE],
    )
    def test_transformers_calls_pin_trust(self, module_path: str) -> None:
        import pathlib

        roots = [
            pathlib.Path.cwd(),
            pathlib.Path(__file__).resolve().parents[2],
        ]
        text = None
        for root in roots:
            candidate = root / module_path
            if candidate.exists():
                text = candidate.read_text()
                break
        assert text is not None, f"missing {module_path}"
        assert "trust_remote_code=False" in text


class TestDocumentLoaderGuards:
    def test_text_file_cap(self, tmp_path) -> None:
        from airunner_services.llm.managers.agent import document_loader

        big = tmp_path / "big.txt"
        big.write_bytes(b"x" * (document_loader.MAX_TEXT_FILE_BYTES + 1))
        with pytest.raises(ValueError):
            document_loader._read_text_file(str(big))

    def test_html_strips_script_and_style(self) -> None:
        from airunner_services.llm.managers.agent import document_loader

        html = (
            "<html><head><style>.a{}</style><script>evil()</script>"
            "</head><body><p>keep me</p></body></html>"
        )
        text = document_loader._html_to_text(html)
        assert "keep me" in text
        assert "evil" not in text

    def test_epub_entry_budget(self, tmp_path) -> None:
        from airunner_services.llm.managers.agent import document_loader

        target = tmp_path / "book.epub"
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr(
                "OEBPS/content.html",
                "<html><body><p>" + ("x" * 100) + "</p></body></html>",
            )
        with zipfile.ZipFile(target, "r") as archive:
            with pytest.raises(ValueError):
                cap = document_loader._read_epub_entry_capped
                cap(archive, "OEBPS/content.html", remaining=5)

    def test_epub_page_heuristic_fallback(self) -> None:
        from airunner_services.llm.managers.agent import document_loader

        entries = ["OEBPS/page_1.xhtml"] + [
            f"OEBPS/chapter_{i}.html" for i in range(10)
        ]
        ordered = document_loader._sorted_epub_entries(entries)
        assert len(ordered) == len(entries)

    def test_mobi_containment_escape(self, tmp_path, monkeypatch) -> None:
        import sys
        import types

        from airunner_services.llm.managers.agent import document_loader

        target = tmp_path / "book.mobi"
        target.write_bytes(b"0" * 16)
        fake = types.ModuleType("mobi")

        def fake_extract(path):
            inner = tmp_path / "inner"
            inner.mkdir(exist_ok=True)
            out = inner / "book.html"
            out.write_text("<html><body><p>hi</p></body></html>")
            return (str(tmp_path / "elsewhere"), "/etc/passwd")

        fake.extract = fake_extract
        monkeypatch.setitem(sys.modules, "mobi", fake)
        with pytest.raises(ValueError):
            document_loader._load_mobi_document(str(target), {})

    def test_mobi_size_cap(self, tmp_path, monkeypatch) -> None:
        import sys
        import types

        from airunner_services.llm.managers.agent import document_loader

        target = tmp_path / "book.mobi"
        target.write_bytes(b"0" * 16)
        fake = types.ModuleType("mobi")
        fake.extract = lambda path: (str(tmp_path), str(target))
        monkeypatch.setitem(sys.modules, "mobi", fake)
        monkeypatch.setattr(
            document_loader.os.path, "getsize", lambda path: 10**12
        )
        with pytest.raises(ValueError):
            document_loader._load_mobi_document(str(target), {})

    def test_zim_batches(self, tmp_path, monkeypatch) -> None:
        import sys
        import types

        from airunner_services.llm.managers.agent import document_loader

        fake_reader = types.ModuleType("airunner_services.zimreader")

        class _Zim:
            def __init__(self, path):
                return None

            def get_all_entry_paths(self, limit=None):
                return [f"article_{i}" for i in range(5)]

            def get_article(self, path):
                return f"<html><body><p>{path}</p></body></html>"

        fake_reader.ZIMReader = _Zim
        monkeypatch.setitem(
            sys.modules, "airunner_services.zimreader", fake_reader
        )
        batches = list(
            document_loader._iter_zim_documents(
                str(tmp_path / "x.zim"), {}, batch_size=2
            )
        )
        assert len(batches) == 3
        assert sum(len(batch) for batch in batches) == 5

    def test_pdf_unreadable_raises_value_error(self, tmp_path) -> None:
        pytest.importorskip("pypdf", reason="pypdf not installed")
        from airunner_services.llm.managers.agent import document_loader

        target = tmp_path / "empty.pdf"
        target.write_bytes(b"%PDF-1.4\n%EOF\n")
        with pytest.raises(ValueError):
            document_loader._load_pdf_document(str(target), {})


class TestBaseManagerGuards:
    def test_redaction(self) -> None:
        from airunner_services.database.base_manager import (
            _redacted_kwargs,
        )

        redacted = _redacted_kwargs(
            {"api_key": "sekret", "name": "plain", "TOKEN": "t"}
        )
        assert redacted == {
            "api_key": "***",
            "name": "plain",
            "TOKEN": "***",
        }

    def test_update_requires_pk(self) -> None:
        from airunner_services.database.base_manager import (
            RealBaseManager,
        )

        manager = RealBaseManager(object)
        assert manager.update(name="x") is False
        assert manager.update(None, name="x") is False

    def test_delete_guards(self) -> None:
        from airunner_services.database.base_manager import (
            RealBaseManager,
        )

        manager = RealBaseManager(object)
        assert manager.delete() is False
        assert manager.delete_by() is False
        assert manager.delete_all() == -1

    def _sqlite_manager(self, tmp_path, monkeypatch):
        import airunner_services.database.session as session_mod
        from airunner_services.database.base_manager import (
            RealBaseManager,
        )

        monkeypatch.setenv(
            "AIRUNNER_DATABASE_URL",
            f"sqlite:///{tmp_path / 'guards.sqlite3'}",
        )
        session_mod.reset_engine()

        engine = session_mod._get_engine("default")
        _GuardBase.metadata.create_all(engine)
        return RealBaseManager(_GuardRow), session_mod, _GuardRow

    def test_paging_and_eager_passthrough(
        self, tmp_path, monkeypatch
    ) -> None:
        manager, session_mod, _Row = self._sqlite_manager(
            tmp_path, monkeypatch
        )
        try:
            with session_mod.session_scope() as session:
                for i in range(5):
                    session.add(_Row(name=f"n{i}"))
            assert len(manager.all()) == 5
            assert len(manager.all(limit=2)) == 2
            assert len(manager.all(limit=2, offset=4)) == 1
            assert len(manager.filter_by(name="n0")) == 1
            assert len(manager.filter(_Row.name == "n1")) == 1
            found = manager.filter(_Row.name == "n2", limit=1)
            assert found[0]["name"] == "n2"
        finally:
            session_mod.reset_engine()

    def test_bulk_delete_row_cap(self, tmp_path, monkeypatch) -> None:
        import airunner_services.database.base_manager as base_mod

        manager, session_mod, _Row = self._sqlite_manager(
            tmp_path, monkeypatch
        )
        try:
            with session_mod.session_scope() as session:
                for i in range(5):
                    session.add(_Row(name="bulk"))
            monkeypatch.setattr(base_mod, "MAX_BULK_DELETE_ROWS", 3)
            assert manager.delete_by(name="bulk") is False
            assert len(manager.filter_by(name="bulk")) == 5
        finally:
            session_mod.reset_engine()


class TestSessionSecrets:
    def test_validator_rejects_hostile_tenant(self) -> None:
        import airunner_services.database.session as session_mod

        assert (
            session_mod._validate_tenant_identifier("tenant_01")
            == "tenant_01"
        )
        for bad in [
            "a;b",
            "x y",
            "../etc",
            '" OR 1=1 --',
            "t" * 64,
            "",
            "tenant-1",
        ]:
            with pytest.raises(ValueError):
                session_mod._validate_tenant_identifier(bad)

    def test_tenant_url_hides_password(self) -> None:
        import airunner_services.database.session as session_mod

        rendered = session_mod._tenant_db_url(
            "postgresql://bob:s3cret@db:5432/app", "tenant_7"
        )
        assert "s3cret" not in rendered
        assert "tenant_7" in rendered
        assert "search_path" in rendered
        args = session_mod._tenant_connect_args(
            "postgresql://bob:s3cret@db:5432/app"
        )
        assert args == {"password": "s3cret"}

    def test_ensure_tenant_ready_rejects_before_connect(
        self, monkeypatch
    ) -> None:
        import airunner_services.database.session as session_mod

        monkeypatch.setenv("AIRUNNER_DB_TENANCY", "multi")
        monkeypatch.setenv(
            "AIRUNNER_DATABASE_URL",
            "postgresql://bob:s3cret@db:5432/app",
        )
        monkeypatch.delenv("AIRUNNER_MIGRATION_RUNNING", raising=False)

        def _boom(*args, **kwargs):
            raise AssertionError("engine must not be created")

        monkeypatch.setattr(
            session_mod, "create_configured_engine", _boom
        )
        import airunner_services.database.setup_database  # noqa: F401

        setup_module = sys.modules[
            "airunner_services.database.setup_database"
        ]

        def _no_setup(*args, **kwargs):
            raise AssertionError("setup must not run")

        monkeypatch.setattr(setup_module, "setup_database", _no_setup)
        with pytest.raises(ValueError):
            session_mod._ensure_tenant_ready('evil"; DROP TABLE x --')


class TestGeolocationGuards:
    def test_normalize_accepts_zip_plus_four(self) -> None:
        from airunner_services.api.routes.geolocation import (
            normalize_zipcode,
        )

        assert normalize_zipcode("90210") == "90210"
        assert normalize_zipcode("90210-1234") == "90210"

    def test_normalize_rejects_hostile(self) -> None:
        from airunner_services.api.routes.geolocation import (
            normalize_zipcode,
        )

        bad_zips = [
            "",
            "ABCDE",
            "1234",
            "123456",
            "../etc",
            "90210;DROP",
        ]
        for bad in bad_zips:
            with pytest.raises(ValueError):
                normalize_zipcode(bad)

    def test_invalid_zip_returns_empty(self) -> None:
        import asyncio

        from airunner_services.api.routes import geolocation

        response = asyncio.run(geolocation.geolocate_zip("not-a-zip"))
        assert response.lat is None
        assert response.lon is None


class TestKiwixCaps:
    def test_parse_caps_entries(self) -> None:
        import xml.etree.ElementTree as ET

        from airunner_services.kiwix_api import KiwixAPI

        entries = "".join(
            f"<entry><id>{i}</id><title>t{i}</title>"
            f"<link rel='http://opds-spec.org/acquisition/open-access' "
            f"href='https://x/{i}.meta4'/></entry>"
            for i in range(KiwixAPI.MAX_ENTRIES + 10)
        )
        root = ET.fromstring(
            "<feed xmlns='http://www.w3.org/2005/Atom'>"
            + entries
            + "</feed>"
        )
        assert len(KiwixAPI._parse_entries(root)) == KiwixAPI.MAX_ENTRIES

    def test_param_caps_exist(self) -> None:
        from airunner_services.kiwix_api import KiwixAPI

        assert KiwixAPI.MAX_FEED_BYTES >= 1024
        assert KiwixAPI.MAX_PARAM_LENGTH <= 128


class TestAlembicMergeHead:
    def _versions_dir(self):
        import pathlib

        roots = [
            pathlib.Path.cwd(),
            pathlib.Path(__file__).resolve().parents[2],
        ]
        for root in roots:
            candidate = (
                root
                / "services/src/airunner_services/database/alembic/versions"
            )
            if candidate.is_dir():
                return candidate
        raise AssertionError("versions dir not found")

    def _graph(self):
        import ast

        revisions: dict[str, set[str]] = {}

        def _literal_strings(node):
            if isinstance(node, ast.Constant) and isinstance(
                node.value, str
            ):
                return {node.value}
            if isinstance(node, (ast.Tuple, ast.List)):
                found: set[str] = set()
                for element in node.elts:
                    found |= _literal_strings(element)
                return found
            return set()

        for path in self._versions_dir().glob("*.py"):
            tree = ast.parse(path.read_text())
            values: dict[str, set[str]] = {}
            for node in tree.body:
                if isinstance(node, ast.AnnAssign) and isinstance(
                    node.target, ast.Name
                ):
                    values[node.target.id] = _literal_strings(node.value)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            values[target.id] = _literal_strings(
                                node.value
                            )
            revs = values.get("revision", set())
            assert len(revs) == 1, path.name
            revisions[next(iter(revs))] = values.get(
                "down_revision", set()
            )
        referenced: set[str] = set()
        for refs in revisions.values():
            referenced |= set(refs)
        heads = sorted(set(revisions) - referenced)
        return revisions, heads

    def test_single_merge_head(self) -> None:
        revisions, heads = self._graph()
        assert heads == ["f3a2c9e4b710"]
        # Only the two TRUE heads: 48b1/5a4d/b1c4 are already merged
        # by d2ab5f1c9a7e and must not be re-merged.
        assert set(revisions["f3a2c9e4b710"]) == {
            "a7c93f2e1b4d",
            "d951d2fd378d",
        }

    def test_no_bare_drop_column_in_cited_migrations(self) -> None:
        base = self._versions_dir()
        names = [
            "500b6c395d38_add_knowledge_migrated_flag.py",
            "9623fe2fc53a_add_service_settings_fields.py",
            "970363fddcd6_add_n_ctx_and_enable_tools_to_llm_.py",
            "d4184aabeff9_remove_allow_online_mode_column_.py",
            "f0b1f4cf8f41_add_document_size_to_application_settings.py",
            "080398045849_add_auto_extract_knowledge.py",
        ]
        for name in names:
            text = (base / name).read_text()
            assert "op.drop_column" not in text, name
