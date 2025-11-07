import multiprocessing
import hashlib
from typing import Optional, List, Dict
from pathlib import Path
import twisted.internet._signals
import scrapy.utils.ossignal
import trafilatura
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

from airunner.components.settings.data.path_settings import PathSettings
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


# Patch signals for subprocesses
def _patch_signals_for_subprocess():
    if multiprocessing.current_process().name != "MainProcess":
        try:
            twisted.internet._signals.install = lambda *a, **kw: None
            if hasattr(twisted.internet._signals, "SignalReactorMixin"):
                twisted.internet._signals.SignalReactorMixin.install = (
                    lambda *a, **kw: None
                )
        except Exception:
            pass
        try:
            scrapy.utils.ossignal.install_shutdown_handlers = (
                lambda *a, **kw: None
            )
        except Exception:
            pass


_patch_signals_for_subprocess()

# Dynamically resolve cache directory based on PathSettings
try:
    base_path = PathSettings.objects.first().base_path
    CACHE_DIR = Path(base_path) / "cache" / ".webcache"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    # Fallback to local .webcache if PathSettings is unavailable (e.g., during tests)
    CACHE_DIR = Path(__file__).parent / ".webcache"
    CACHE_DIR.mkdir(exist_ok=True)

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

__all__ = ["WebContentExtractor"]


class WebContentExtractor:
    """Fetches, extracts, cleans, summarizes, and caches main content from web pages."""

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
        """Fetch, extract, and summarize main content as plaintext from a URL, using cache if available."""
        cached = WebContentExtractor.get_cached(url)
        if use_cache and cached:
            return cached

        text = WebContentExtractor._fetch_with_trafilatura(url)
        if text:
            summarized_text = WebContentExtractor._summarize_text(text)
            WebContentExtractor.set_cache(url, summarized_text)
            return summarized_text

        return None

    @staticmethod
    def extract(content: str) -> Optional[str]:
        """Extract main content from HTML using trafilatura."""
        try:
            downloaded = trafilatura.extract(
                content, include_comments=False, include_tables=False
            )
            if downloaded:
                return downloaded
        except Exception as e:
            logger.error(f"Trafilatura extraction failed: {e}")
        return None

    @staticmethod
    def extract_markdown(content: str) -> Optional[str]:
        """Extract main content from HTML as Markdown using trafilatura."""
        try:
            return trafilatura.extract(
                content,
                output_format="markdown",
                include_comments=False,
                include_tables=True,
                include_links=True,
                include_formatting=True,
            )
        except Exception as e:
            logger.error(f"Trafilatura Markdown extraction failed: {e}")
        return None

    @staticmethod
    def extract_json(content: str) -> Optional[Dict]:
        """Extract structured content from HTML as JSON using trafilatura."""
        try:
            import json

            result = trafilatura.extract(
                content,
                output_format="json",
                include_comments=False,
                include_tables=True,
                include_links=True,
                include_formatting=True,
            )
            return json.loads(result) if result else None
        except Exception as e:
            logger.error(f"Trafilatura JSON extraction failed: {e}")
        return None

    @staticmethod
    def fetch_and_extract_markdown(
        url: str, use_cache: bool = True
    ) -> Optional[str]:
        """Fetch and extract content as Markdown from a URL."""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                return WebContentExtractor.extract_markdown(downloaded)
        except Exception as e:
            logger.error(f"Trafilatura Markdown fetch failed for {url}: {e}")
        return None

    @staticmethod
    def _fetch_with_trafilatura(url: str) -> Optional[str]:
        """Fetch content using trafilatura."""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                return trafilatura.extract(
                    downloaded, include_comments=False, include_tables=False
                )
        except Exception as e:
            logger.error(f"Trafilatura failed for {url}: {e}")
        return None

    @staticmethod
    def _summarize_text(text: str) -> str:
        """Summarize the extracted text using Sumy."""
        try:
            parser = PlaintextParser.from_string(text, Tokenizer("english"))
            summarizer = LsaSummarizer()
            summary = summarizer(parser.document, 2)  # Limit to 2 sentences
            return "\n\n".join(str(sentence) for sentence in summary)
        except Exception as e:
            logger.error(f"Sumy summarization failed: {e}")
            return text

    @staticmethod
    def content_from_search_results(
        consolidated_results: List[Dict], top_n: int
    ) -> List[str]:
        url_items = [
            item
            for item in consolidated_results
            if item.get("link") and item.get("link") != "#"
        ]
        url_items = url_items[:top_n]
        clean_documents = []
        for item in url_items:
            url = item["link"]
            try:
                text = WebContentExtractor.fetch_and_extract(url)
                if text:
                    clean_documents.append(text)
                else:
                    logger.warning(f"No main content extracted for {url}")
            except Exception as e:
                logger.error(f"Error extracting content for {url}: {e}")
        return clean_documents
