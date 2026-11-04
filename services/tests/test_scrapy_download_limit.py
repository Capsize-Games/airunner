"""Exercise Scrapy's real wire/decompression limits with local fixtures."""

from __future__ import annotations

import gzip
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

if importlib.util.find_spec("scrapy") is not None:
    from scrapy import Request
    from scrapy.core.downloader.handlers.http11 import _ResponseReader
    from scrapy.downloadermiddlewares.httpcompression import HttpCompressionMiddleware
    from scrapy.exceptions import IgnoreRequest
    from scrapy.http import Response
    from twisted.internet.defer import Deferred
else:
    _ResponseReader = None


def _service_limit() -> int:
    path = Path(__file__).parents[1] / "src/airunner_services/tools/scrapy/settings.py"
    spec = importlib.util.spec_from_file_location("crawl_limit_settings", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DOWNLOAD_MAXSIZE


@unittest.skipIf(_ResponseReader is None, "Scrapy runtime is not installed")
class DownloadLimitTests(unittest.TestCase):
    """Use real dependency methods without a network or Twisted reactor."""

    def test_wire_overflow_cancels_clears_buffer_and_rejects_late_chunks(self) -> None:
        limit = _service_limit()
        errors = []
        finished = Deferred()
        finished.addErrback(lambda failure: errors.append(failure.type.__name__))
        crawler = SimpleNamespace(
            signals=SimpleNamespace(send_catch_log=lambda **_kwargs: []),
            spider=None,
        )
        reader = _ResponseReader(
            finished, SimpleNamespace(), Request("https://fixture.invalid/"),
            limit, 0, True, crawler,
        )
        reader.transport = SimpleNamespace()
        reader.dataReceived(b"x" * limit)
        self.assertFalse(finished.called)
        self.assertEqual(len(reader._bodybuf.getvalue()), limit)
        reader.dataReceived(b"y")
        self.assertTrue(finished.called)
        self.assertEqual(errors, ["CancelledError"])
        self.assertEqual(reader._bodybuf.getvalue(), b"")
        reader.dataReceived(b"late data")
        self.assertEqual(reader._bodybuf.getvalue(), b"")
        self.assertEqual(reader._bytes_received, limit + 1)

    def test_compressed_body_cannot_expand_past_service_limit(self) -> None:
        limit = _service_limit()
        request = Request(
            "https://fixture.invalid/", meta={"download_maxsize": limit},
        )
        response = Response(
            request.url,
            headers={"Content-Encoding": "gzip"},
            body=gzip.compress(b"x" * (limit + 1)),
        )
        middleware = HttpCompressionMiddleware()
        with self.assertRaises(IgnoreRequest):
            middleware.process_response(request, response)


if __name__ == "__main__":
    unittest.main()
