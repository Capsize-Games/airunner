import multiprocessing


def _patch_signals_for_subprocess():
    if multiprocessing.current_process().name != "MainProcess":
        try:
            import twisted.internet._signals

            twisted.internet._signals.install = lambda *a, **kw: None
            if hasattr(twisted.internet._signals, "SignalReactorMixin"):
                twisted.internet._signals.SignalReactorMixin.install = (
                    lambda *a, **kw: None
                )
        except Exception:
            pass
        try:
            import scrapy.utils.ossignal

            scrapy.utils.ossignal.install_shutdown_handlers = (
                lambda *a, **kw: None
            )
        except Exception:
            pass


_patch_signals_for_subprocess()

import os
import hashlib
import logging
from typing import Optional
from pathlib import Path
import trafilatura

from airunner.data.models import PathSettings

# Dynamically resolve cache directory based on PathSettings
try:
    base_path = PathSettings.objects.first().base_path
    CACHE_DIR = Path(base_path) / "cache" / ".webcache"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    # Fallback to local .webcache if PathSettings is unavailable (e.g., during tests)
    CACHE_DIR = Path(__file__).parent / ".webcache"
    CACHE_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)

__all__ = ["WebContentExtractor"]


class WebContentExtractor:
    """Fetches, extracts, cleans, and caches main content from web pages."""

    CACHE_DIR = CACHE_DIR
    CACHE_EXPIRY_DAYS = None  # No expiry for now

    @staticmethod
    def _url_to_cache_path(url: str) -> Path:
        h = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return WebContentExtractor.CACHE_DIR / f"{h}.txt"

    @staticmethod
    def get_cached(url: str) -> Optional[str]:
        path = WebContentExtractor._url_to_cache_path(url)
        if path.exists():
            try:
                return path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to read cache for {url}: {e}")
        return None

    @staticmethod
    def set_cache(url: str, text: str):
        path = WebContentExtractor._url_to_cache_path(url)
        try:
            path.write_text(text, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to write cache for {url}: {e}")

    @staticmethod
    def fetch_and_extract(url: str, use_cache: bool = True) -> Optional[str]:
        """Fetch and extract main content as plaintext from a URL, using cache if available.
        Handles Scrapy reactor errors gracefully for repeated calls in the same process (e.g., in tests).
        If Scrapy cannot run (e.g., reactor error), fall back to direct requests + trafilatura extraction.
        Always uses disk-based cache (never in-memory) for all fetches.
        Follows a single link from the main page to one more page, and extracts from both.
        Scrapy/Twisted is always run in the main thread of the main interpreter. If not, uses multiprocessing to delegate.
        """
        import sys
        import threading

        def _scrapy_worker(url, result_dict):
            _patch_signals_for_subprocess()
            from scrapy.crawler import CrawlerProcess
            from scrapy import Spider, Request
            import trafilatura
            import logging

            logger = logging.getLogger(__name__)
            result = {"texts": []}

            class SinglePageSpider(Spider):
                name = "single_page_spider"
                custom_settings = {
                    "DOWNLOAD_TIMEOUT": 15,
                    "LOG_ENABLED": False,
                }

                def start_requests(self):
                    # Scrapy 2.13+ prefers async def start(), but for compatibility, we provide both
                    yield Request(
                        url,
                        callback=self.parse,
                        errback=self.errback,
                        meta={"depth": 0},
                    )

                async def start(self):
                    # Scrapy 2.13+ async start method
                    yield Request(
                        url,
                        callback=self.parse,
                        errback=self.errback,
                        meta={"depth": 0},
                    )

                def parse(self, response):
                    html = response.text
                    text = trafilatura.extract(
                        html, include_comments=False, include_tables=False
                    )
                    if text:
                        result["texts"].append(text)
                    if response.meta.get("depth", 0) == 0:
                        links = response.css("a::attr(href)").getall()
                        links = [
                            l
                            for l in links
                            if l
                            and (l.startswith("http") or l.startswith("/"))
                        ]
                        if links:
                            next_url = response.urljoin(links[0])
                            yield Request(
                                next_url,
                                callback=self.parse,
                                errback=self.errback,
                                meta={"depth": 1},
                            )

                def errback(self, failure):
                    logger.warning(f"Scrapy failed for {url}: {failure}")

            try:
                process = CrawlerProcess(settings={"LOG_ENABLED": False})
                process.crawl(SinglePageSpider)
                process.start()
            except Exception as e:
                logger.error(f"Scrapy error in subprocess: {e}")
            result_dict["texts"] = result["texts"]

        # Always check disk cache first
        cached = WebContentExtractor.get_cached(url)
        if use_cache and cached:
            return cached
        # Only run Scrapy in the main thread of the main interpreter
        if (
            multiprocessing.current_process().name != "MainProcess"
            or not hasattr(sys, "ps1")
            and not sys.argv[0]
        ):
            # Not in main interpreter, delegate to a subprocess
            manager = multiprocessing.Manager()
            result_dict = manager.dict()
            p = multiprocessing.Process(
                target=_scrapy_worker, args=(url, result_dict)
            )
            p.start()
            p.join()
            texts = result_dict.get("texts", [])
        else:
            # In main interpreter main thread
            result_dict = {"texts": []}
            _scrapy_worker(url, result_dict)
            texts = result_dict.get("texts", [])
        all_text = "\n\n".join(texts)
        if all_text:
            WebContentExtractor.set_cache(url, all_text)
            return all_text
        # Fallback: requests + trafilatura
        try:
            import requests

            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                text = trafilatura.extract(
                    resp.text,
                    include_comments=False,
                    include_tables=False,
                )
                if text:
                    WebContentExtractor.set_cache(url, text)
                    return text
        except Exception as e2:
            logger.error(
                f"Fallback requests+trafilatura failed for {url}: {e2}"
            )
        return None
