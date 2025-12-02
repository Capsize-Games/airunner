import multiprocessing
import hashlib
import random
from typing import Optional, List, Dict, Set
from pathlib import Path
from urllib.parse import urlparse
import twisted.internet._signals
import scrapy.utils.ossignal
import trafilatura
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

from airunner.components.settings.data.path_settings import PathSettings
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


# Rotating User Agents - looks like real browsers
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


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
def _get_base_path() -> Path:
    """Get the base path for cache, respecting Flatpak environment."""
    import os
    if os.environ.get("AIRUNNER_FLATPAK") == "1":
        xdg_data_home = os.environ.get(
            "XDG_DATA_HOME",
            os.path.expanduser("~/.local/share")
        )
        return Path(xdg_data_home) / "airunner"
    return Path.home() / ".local" / "share" / "airunner"

try:
    path_settings = PathSettings.objects.first()
    if path_settings and path_settings.base_path:
        base_path = Path(path_settings.base_path)
    else:
        # Use Flatpak-aware path as fallback
        base_path = _get_base_path()
    CACHE_DIR = base_path / "cache" / ".webcache"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    BLOCKLIST_FILE = base_path / ".scraper_blocklist"
except Exception:
    # Fallback using Flatpak-aware path
    base_path = _get_base_path()
    CACHE_DIR = base_path / "cache" / ".webcache"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    BLOCKLIST_FILE = base_path / ".scraper_blocklist"

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

__all__ = ["WebContentExtractor"]


class WebContentExtractor:
    """Fetches, extracts, cleans, summarizes, and caches main content from web pages."""

    CACHE_DIR = CACHE_DIR
    CACHE_EXPIRY_DAYS = None  # No expiry for now
    BLOCKLIST_FILE = BLOCKLIST_FILE
    _blocklist: Optional[Set[str]] = None  # Cache the blocklist in memory
    _current_user_agent: Optional[str] = None  # Rotates each session

    @staticmethod
    def _get_browser_headers() -> Dict[str, str]:
        """Generate browser-like headers with rotating user agent.

        Returns:
            Dictionary of HTTP headers that mimic a real browser
        """
        # Rotate user agent if not set or randomly (10% chance)
        if (
            WebContentExtractor._current_user_agent is None
            or random.random() < 0.1
        ):
            WebContentExtractor._current_user_agent = random.choice(
                USER_AGENTS
            )

        # Build realistic browser headers
        headers = {
            "User-Agent": WebContentExtractor._current_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",  # Do Not Track
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

        # Add referer for non-initial requests (looks more natural)
        if random.random() > 0.3:  # 70% of the time, add a referer
            referers = [
                "https://www.google.com/",
                "https://www.bing.com/",
                "https://duckduckgo.com/",
            ]
            headers["Referer"] = random.choice(referers)

        return headers

    @staticmethod
    def _get_base_url(url: str) -> str:
        """Extract domain (netloc only) from a full URL for blocklist matching.

        Returns just the domain without scheme for consistent blocking.
        Example: https://en.wikipedia.org/wiki/Page -> en.wikipedia.org
        """
        parsed = urlparse(url)
        return parsed.netloc

    @classmethod
    def _load_blocklist(cls) -> Set[str]:
        """
        Load the blocklist from file and merge with settings-based blacklist.
        Returns set of blocked domains (netloc only, no scheme).
        """
        if cls._blocklist is not None:
            return cls._blocklist

        cls._blocklist = set()

        # Load from file (user-specific automatic blocklist)
        if cls.BLOCKLIST_FILE.exists():
            try:
                content = cls.BLOCKLIST_FILE.read_text(encoding="utf-8")
                file_blocklist = {
                    line.strip()
                    .replace("http://", "")
                    .replace("https://", "")
                    .strip("/")
                    for line in content.splitlines()
                    if line.strip() and not line.strip().startswith("#")
                }
                cls._blocklist.update(file_blocklist)
                logger.debug(
                    f"Loaded {len(file_blocklist)} blocked domains from {cls.BLOCKLIST_FILE}"
                )
            except Exception as e:
                logger.warning(f"Failed to load scraper blocklist: {e}")

        # Merge with settings-based blacklist (project-wide configuration)
        from airunner.settings import AIRUNNER_SCRAPER_BLACKLIST

        settings_domains = set()
        for domain in AIRUNNER_SCRAPER_BLACKLIST:
            # Normalize: strip http/https scheme and trailing slash
            # wikipedia.org -> wikipedia.org
            # https://wikipedia.org -> wikipedia.org
            # en.wikipedia.org -> en.wikipedia.org
            normalized = (
                domain.replace("http://", "")
                .replace("https://", "")
                .strip("/")
            )
            settings_domains.add(normalized)

        cls._blocklist.update(settings_domains)
        logger.debug(
            f"Loaded {len(settings_domains)} domains from settings blacklist"
        )
        logger.info(
            f"Total blocklist size: {len(cls._blocklist)} domains (file + settings)"
        )

        return cls._blocklist

    @classmethod
    def get_blocklist(cls) -> Set[str]:
        """Public method to get the current blocklist for use in search queries.

        Returns:
            Set of blocked domain names (without scheme)
        """
        return cls._load_blocklist()

    @classmethod
    def _save_blocklist(cls):
        """Save the current blocklist to file."""
        if cls._blocklist is None:
            return

        try:
            # Sort for consistent ordering
            sorted_list = sorted(cls._blocklist)
            content = "\n".join(sorted_list) + "\n"
            cls.BLOCKLIST_FILE.write_text(content, encoding="utf-8")
            logger.info(
                f"Saved {len(cls._blocklist)} blocked domains to {cls.BLOCKLIST_FILE}"
            )
        except Exception as e:
            logger.warning(f"Failed to save scraper blocklist: {e}")

    @classmethod
    def _add_to_blocklist(cls, url: str):
        """Add a URL's base domain to the blocklist."""
        base_url = cls._get_base_url(url)
        blocklist = cls._load_blocklist()
        if base_url not in blocklist:
            blocklist.add(base_url)
            cls._save_blocklist()
            logger.info(f"Added {base_url} to scraper blocklist")

    @classmethod
    def _is_blocked(cls, url: str) -> bool:
        """Check if a URL's base domain is in the blocklist."""
        base_url = cls._get_base_url(url)
        blocklist = cls._load_blocklist()
        return base_url in blocklist

    @staticmethod
    def _url_to_cache_path(url: str) -> Path:
        h = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return WebContentExtractor.CACHE_DIR / f"{h}.txt"

    @staticmethod
    def _url_to_metadata_cache_path(url: str) -> Path:
        """Get cache path for metadata (JSON) version of URL."""
        h = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return WebContentExtractor.CACHE_DIR / f"{h}_meta.json"

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
    def get_cached_metadata(url: str) -> Optional[Dict]:
        """Get cached metadata for a URL if available."""
        path = WebContentExtractor._url_to_metadata_cache_path(url)
        if path.exists():
            try:
                import json

                return json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to read metadata cache for {url}: {e}")
        return None

    @staticmethod
    def set_cache(url: str, text: str):
        path = WebContentExtractor._url_to_cache_path(url)
        try:
            path.write_text(text, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to write cache for {url}: {e}")

    @staticmethod
    def set_metadata_cache(url: str, metadata: Dict):
        """Cache metadata for a URL."""
        path = WebContentExtractor._url_to_metadata_cache_path(url)
        try:
            import json

            path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to write metadata cache for {url}: {e}")

    @staticmethod
    def fetch_and_extract(url: str, use_cache: bool = True) -> Optional[str]:
        """Fetch, extract, and summarize main content as plaintext from a URL, using cache if available."""
        # Check if this domain is blocked
        if WebContentExtractor._is_blocked(url):
            logger.info(
                f"Skipping blocked domain: {WebContentExtractor._get_base_url(url)}"
            )
            return None

        cached = WebContentExtractor.get_cached(url)
        if use_cache and cached:
            return cached

        text = WebContentExtractor._fetch_with_trafilatura(url)
        if text:
            summarized_text = WebContentExtractor._summarize_text(text)
            WebContentExtractor.set_cache(url, summarized_text)
            return summarized_text
        else:
            # Failed to fetch - add to blocklist
            WebContentExtractor._add_to_blocklist(url)

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
    def fetch_and_extract_with_metadata_raw(
        url: str, use_cache: bool = True, summarize: bool = False
    ) -> Optional[Dict]:
        """Fetch and extract main content with metadata from a URL.

        Args:
            url: The URL to fetch and extract
            use_cache: Whether to use cache
            summarize: Whether to apply Sumy summarization (default: False for raw content)

        Returns:
            Dictionary with:
            - content: Clean text content (raw or summarized based on parameter)
            - title: Page title (from metadata)
            - description: Page description (from metadata)
            - author: Author name if available
            - publish_date: Publication date if available
            Returns None if extraction fails.
        """
        # Check if this domain is blocked
        if WebContentExtractor._is_blocked(url):
            logger.info(
                f"Skipping blocked domain: {WebContentExtractor._get_base_url(url)}"
            )
            return None

        # Check cache first (metadata includes both raw and summarized)
        if use_cache:
            cached_metadata = WebContentExtractor.get_cached_metadata(url)
            if cached_metadata:
                # If cache has the content type we need, return it
                if summarize and "content" in cached_metadata:
                    logger.debug(f"Using cached summarized metadata for {url}")
                    return cached_metadata
                elif not summarize and "raw_content" in cached_metadata:
                    logger.debug(f"Using cached raw metadata for {url}")
                    # Return with raw content as 'content'
                    result = cached_metadata.copy()
                    result["content"] = result.pop("raw_content")
                    return result

        try:
            # Fetch raw HTML with browser-like headers to avoid blocking
            headers = WebContentExtractor._get_browser_headers()

            # Use trafilatura's fetch_url with custom headers and config
            from trafilatura.settings import use_config

            config = use_config()
            config.set("DEFAULT", "USER_AGENT", headers["User-Agent"])

            # Fetch with custom headers
            html_content = trafilatura.fetch_url(url, config=config)

            if not html_content:
                logger.warning(f"Failed to fetch content from {url}")
                # Add to blocklist - site is blocking scrapers
                WebContentExtractor._add_to_blocklist(url)
                return None

            # Extract main text content
            main_text = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
            )

            if not main_text:
                logger.warning(f"No main text extracted from {url}")
                # Add to blocklist - likely blocking scrapers
                WebContentExtractor._add_to_blocklist(url)
                return None

            # Extract metadata
            metadata = trafilatura.extract_metadata(html_content)

            # Store both raw and summarized content
            summarized_text = WebContentExtractor._summarize_text(main_text)
            content_text = summarized_text if summarize else main_text

            result = {
                "content": content_text,
                "title": metadata.title if metadata else None,
                "description": metadata.description if metadata else None,
                "author": metadata.author if metadata else None,
                "publish_date": (
                    str(metadata.date) if metadata and metadata.date else None
                ),
            }

            # Cache both versions for future use
            if use_cache:
                cache_entry = result.copy()
                cache_entry["raw_content"] = main_text  # Store raw for later
                cache_entry["content"] = (
                    summarized_text  # Default to summarized
                )
                WebContentExtractor.set_metadata_cache(url, cache_entry)
                logger.debug(
                    f"Cached both raw and summarized content for {url}"
                )

            return result

        except Exception as e:
            logger.error(
                f"Extraction with metadata failed for {url}: {e}",
                exc_info=True,
            )
            # Add to blocklist on exception - likely blocking scrapers
            WebContentExtractor._add_to_blocklist(url)
            return None

    @staticmethod
    def fetch_and_extract_with_metadata(
        url: str, use_cache: bool = True
    ) -> Optional[Dict]:
        """Fetch, extract, and summarize main content with metadata from a URL.

        Args:
            url: The URL to fetch and extract
            use_cache: Whether to use cache

        Returns:
            Dictionary with:
            - content: Clean summarized text content
            - title: Page title (from metadata)
            - description: Page description (from metadata)
            - author: Author name if available
            - publish_date: Publication date if available
            Returns None if extraction fails.
        """
        # Use the raw method with summarization enabled
        return WebContentExtractor.fetch_and_extract_with_metadata_raw(
            url, use_cache=use_cache, summarize=True
        )

    @staticmethod
    def extract_with_links(url: str, content: str = None) -> Optional[Dict]:
        """Extract content, links, and metadata from a URL or HTML content.

        Args:
            url: The URL being processed (for absolute URL resolution)
            content: Optional HTML content. If not provided, will fetch from URL.

        Returns:
            Dictionary with:
            - content: Clean text content
            - links: List of dicts with url, anchor_text, context
            - metadata: Dict with title, description, author, publish_date
            Returns None if extraction fails.
        """
        try:
            pass

            # Fetch content if not provided
            if content is None:
                # Create custom config with shorter timeout
                import configparser

                config = configparser.ConfigParser()
                config.read_dict(
                    {
                        "DEFAULT": {
                            "DOWNLOAD_TIMEOUT": "8"  # 8 seconds instead of 30
                        }
                    }
                )

                content = trafilatura.fetch_url(url, config=config)
                if not content:
                    logger.warning(f"Failed to fetch content from {url}")
                    return None

            # Extract main text content
            main_text = trafilatura.extract(
                content,
                include_comments=False,
                include_tables=True,
            )

            if not main_text:
                logger.warning(f"No main text extracted from {url}")
                return None

            # Extract metadata using trafilatura
            metadata = trafilatura.extract_metadata(content)
            metadata_dict = {
                "title": metadata.title if metadata else None,
                "description": metadata.description if metadata else None,
                "author": metadata.author if metadata else None,
                "publish_date": (
                    str(metadata.date) if metadata and metadata.date else None
                ),
                "url": metadata.url if metadata else url,
            }

            # Extract links with context using BeautifulSoup
            links = WebContentExtractor._extract_links_from_html(
                url, content, main_text
            )

            return {
                "content": main_text,
                "links": links,
                "metadata": metadata_dict,
            }

        except Exception as e:
            logger.error(
                f"extract_with_links failed for {url}: {e}", exc_info=True
            )
            return None

    @staticmethod
    def _extract_links_from_html(
        base_url: str, html_content: str, main_text: str
    ) -> List[Dict]:
        """Extract links with anchor text and context from HTML.

        Args:
            base_url: Base URL for resolving relative links
            html_content: Raw HTML content
            main_text: Extracted main text content (for filtering relevant links)

        Returns:
            List of link dicts with url, anchor_text, context
        """
        try:
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin, urlparse

            soup = BeautifulSoup(html_content, "html.parser")
            links = []
            seen_urls = set()

            # Get the main content area (heuristic: largest text block)
            # This helps filter out navigation/footer links
            main_content_area = (
                soup.find("article") or soup.find("main") or soup.body or soup
            )

            for link_tag in main_content_area.find_all("a", href=True):
                href = link_tag.get("href", "").strip()

                # Skip empty, anchor-only, or javascript links
                if (
                    not href
                    or href.startswith("#")
                    or href.startswith("javascript:")
                ):
                    continue

                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)

                # Parse URL to filter by scheme
                parsed = urlparse(absolute_url)
                if parsed.scheme not in ("http", "https"):
                    continue

                # Skip duplicates
                if absolute_url in seen_urls:
                    continue
                seen_urls.add(absolute_url)

                # Get anchor text
                anchor_text = link_tag.get_text(strip=True)
                if not anchor_text:
                    continue

                # Get surrounding context (parent paragraph or nearby text)
                context = WebContentExtractor._get_link_context(
                    link_tag, anchor_text
                )

                # Filter out likely navigation/footer links by context
                if WebContentExtractor._is_likely_navigation_link(
                    anchor_text, context
                ):
                    continue

                links.append(
                    {
                        "url": absolute_url,
                        "anchor_text": anchor_text,
                        "context": context,
                    }
                )

            logger.info(f"Extracted {len(links)} links from {base_url}")
            return links

        except Exception as e:
            logger.error(f"Link extraction failed: {e}", exc_info=True)
            return []

    @staticmethod
    def _get_link_context(
        link_tag, anchor_text: str, max_context_chars: int = 200
    ) -> str:
        """Get surrounding text context for a link.

        Args:
            link_tag: BeautifulSoup tag object for the link
            anchor_text: The link's anchor text
            max_context_chars: Maximum characters of context to extract

        Returns:
            Context string with link position indicated
        """
        try:
            # Try to get parent paragraph
            parent_p = link_tag.find_parent(["p", "div", "li", "td"])
            if parent_p:
                context_text = parent_p.get_text(separator=" ", strip=True)

                # Truncate if too long
                if len(context_text) > max_context_chars:
                    # Try to center on the anchor text
                    anchor_pos = context_text.find(anchor_text)
                    if anchor_pos != -1:
                        start = max(0, anchor_pos - max_context_chars // 2)
                        end = min(
                            len(context_text),
                            anchor_pos
                            + len(anchor_text)
                            + max_context_chars // 2,
                        )
                        context_text = context_text[start:end]
                        if start > 0:
                            context_text = "..." + context_text
                        if end < len(context_text):
                            context_text = context_text + "..."

                return context_text

            # Fallback: just return the anchor text
            return anchor_text

        except Exception:
            return anchor_text

    @staticmethod
    def _is_likely_navigation_link(anchor_text: str, context: str) -> bool:
        """Heuristic to filter out navigation/footer links.

        Args:
            anchor_text: The link's anchor text
            context: Surrounding context

        Returns:
            True if likely a navigation/footer link
        """
        # Common navigation/footer patterns
        nav_patterns = [
            "home",
            "about",
            "contact",
            "privacy",
            "terms",
            "sitemap",
            "login",
            "register",
            "sign in",
            "sign up",
            "logout",
            "menu",
            "search",
            "subscribe",
            "follow us",
            "share",
            "previous",
            "next",
            "back to",
            "return to",
            "copyright",
            "all rights reserved",
        ]

        anchor_lower = anchor_text.lower()

        # Very short anchor text is often navigation
        if len(anchor_text) < 3:
            return True

        # Check for navigation patterns
        for pattern in nav_patterns:
            if pattern in anchor_lower:
                return True

        # Links with only symbols or numbers
        if (
            anchor_text.replace(" ", "")
            .replace("-", "")
            .replace("»", "")
            .replace("«", "")
            .isdigit()
        ):
            return True

        return False

    @staticmethod
    def fetch_and_extract_markdown(
        url: str, use_cache: bool = True
    ) -> Optional[str]:
        """Fetch and extract content as Markdown from a URL."""
        try:
            # Create custom config with shorter timeout
            import configparser

            config = configparser.ConfigParser()
            config.read_dict(
                {
                    "DEFAULT": {
                        "DOWNLOAD_TIMEOUT": "8"  # 8 seconds instead of 30
                    }
                }
            )

            downloaded = trafilatura.fetch_url(url, config=config)
            if downloaded:
                return WebContentExtractor.extract_markdown(downloaded)
        except Exception as e:
            logger.error(f"Trafilatura Markdown fetch failed for {url}: {e}")
        return None

    @staticmethod
    def _fetch_with_trafilatura(url: str) -> Optional[str]:
        """Fetch content using trafilatura with 8-second timeout and browser headers."""
        try:
            # Get browser headers for masquerading
            headers = WebContentExtractor._get_browser_headers()

            # Create custom config with shorter timeout and user agent
            from trafilatura.settings import use_config

            config = use_config()
            config.set(
                "DEFAULT", "DOWNLOAD_TIMEOUT", "8"
            )  # 8 seconds instead of 30
            config.set("DEFAULT", "USER_AGENT", headers["User-Agent"])

            downloaded = trafilatura.fetch_url(url, config=config)
            if downloaded:
                return trafilatura.extract(
                    downloaded, include_comments=False, include_tables=False
                )
        except Exception as e:
            logger.error(f"Trafilatura failed for {url}: {e}")
        return None

    @staticmethod
    def _summarize_text(text: str, max_sentences: int = 15) -> str:
        """Summarize the extracted text using Sumy.

        Args:
            text: Text to summarize
            max_sentences: Maximum number of sentences (default 15 for research purposes)

        Returns:
            Summarized text, or original if summarization fails
        """
        try:
            parser = PlaintextParser.from_string(text, Tokenizer("english"))
            summarizer = LsaSummarizer()
            # Extract more sentences for research - was 2, now 15
            summary = summarizer(parser.document, max_sentences)
            return "\n\n".join(str(sentence) for sentence in summary)
        except Exception as e:
            logger.error(f"Sumy summarization failed: {e}")
            # Return first 5000 chars if summarization fails (better than nothing)
            return text[:5000] if len(text) > 5000 else text

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
