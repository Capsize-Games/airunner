"""Content validation mixin for DeepResearchAgent.

This mixin provides URL and content quality validation methods.
"""

import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ContentValidationMixin:
    """Provides content validation and filtering methods for research agents."""

    # Domain blacklist for sites that consistently block scraping
    BLACKLISTED_DOMAINS = {
        "nytimes.com",
        "wsj.com",
        "ft.com",  # Financial Times
        "economist.com",
        "bloomberg.com",
        "bakerinstitute.org",  # Consistently returns 403
    }

    @staticmethod
    def _is_domain_blacklisted(url: str) -> bool:
        """Check if a URL's domain is blacklisted.

        Args:
            url: Full URL to check

        Returns:
            True if domain is blacklisted, False otherwise
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove www. prefix for comparison
            if domain.startswith("www."):
                domain = domain[4:]

            # Check if any blacklisted domain matches
            for blacklisted in ContentValidationMixin.BLACKLISTED_DOMAINS:
                if domain == blacklisted or domain.endswith("." + blacklisted):
                    return True

            return False
        except Exception as e:
            logger.warning(f"Error parsing URL {url}: {e}")
            return False

    @staticmethod
    def _is_url_irrelevant_path(url: str) -> bool:
        """Check if URL path contains irrelevant sections.

        Filters out:
        - Games, puzzles, crosswords
        - Account/login pages
        - Shopping/products
        - Jobs/careers
        - General navigation (about, contact, etc.)

        Args:
            url: URL to check

        Returns:
            True if URL should be skipped
        """
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()

            # Irrelevant path segments
            irrelevant_segments = [
                "/games/",
                "/game/",
                "/puzzle/",
                "/crossword/",
                "/sudoku/",
                "/login/",
                "/signin/",
                "/signup/",
                "/register/",
                "/account/",
                "/shop/",
                "/store/",
                "/product/",
                "/cart/",
                "/checkout/",
                "/jobs/",
                "/careers/",
                "/apply/",
                # Note: '/about/' removed to allow scraping personal/about pages
                "/contact/",
                "/privacy/",
                "/terms/",
                "/help/",
                "/subscribe/",
                "/newsletter/",
                "/podcast/",
                "/video/",
                "/videos/",
                "/gallery/",
                "/photos/",
                "/events/",
                "/calendar/",
            ]

            # Check if any irrelevant segment is in the path
            for segment in irrelevant_segments:
                if segment in path:
                    return True

            return False
        except Exception:
            return False

    @staticmethod
    def _is_content_quality_acceptable(content: str) -> bool:
        """Check if scraped content has acceptable quality for research.

        Rejects content that is:
        - Too short (< 200 chars)
        - Access-blocked pages (CAPTCHA, paywall, login required)
        - Too repetitive (many duplicate lines)
        - Mostly navigation/boilerplate (high ratio of common web words)
        - Contains too many symbols/numbers (like Wikipedia citations: [1][2][3])

        Args:
            content: Scraped content to validate

        Returns:
            True if content quality is acceptable, False otherwise
        """
        if not content or len(content) < 200:
            return False

        # Check for common scraper-blocking / access-denied content
        block_phrases = [
            "request access",
            "access denied",
            "captcha",
            "bot test",
            "cloudflare",
            "please verify you are human",
            "verify you are not a robot",
            "automated scraping",
            "programmatic access",
            "complete the captcha",
            "subscription required",
            "subscribe to continue",
            "sign in to continue",
            "login to view",
            "paywall",
            "this content is premium",
            "members only",
            "404 not found",
            "page not found",
            "403 forbidden",
            "enable javascript",
            "javascript is required",
            "cookie consent",
        ]

        content_lower = content.lower()
        blocked_count = sum(
            1 for phrase in block_phrases if phrase in content_lower
        )

        if blocked_count >= 2:
            logger.debug(
                f"Content contains {blocked_count} access-blocking phrases - "
                "likely CAPTCHA/paywall/blocked"
            )
            return False

        # Check for excessive citation markers
        citation_count = len(re.findall(r"\[\d+\]", content))
        if citation_count > 20:
            logger.debug(
                f"Content has {citation_count} citation markers - likely a list/index page"
            )
            return False

        # Check for Wikipedia-style reference markers in sequence
        sequential_refs = len(re.findall(r"\[\d+\]\[\d+\]\[\d+\]", content))
        if sequential_refs > 5:
            logger.debug(
                f"Content has {sequential_refs} sequential reference markers - "
                "likely Wikipedia citations"
            )
            return False

        # Check for list-style content
        lines = content.split("\n")
        list_lines = [
            line
            for line in lines
            if re.match(r"^\s*[-•*]\s+", line.strip())
            or re.match(r"^\s*\d+\.\s+", line.strip())
        ]
        if len(lines) > 10 and len(list_lines) / len(lines) > 0.6:
            logger.debug(
                f"Content is {len(list_lines)/len(lines)*100:.0f}% list items - "
                "likely an index/list page"
            )
            return False

        # Check for repetitive content
        unique_lines = set(
            line.strip() for line in lines if len(line.strip()) > 10
        )
        if len(lines) > 10 and len(unique_lines) / len(lines) < 0.5:
            logger.debug("Content is too repetitive (< 50% unique lines)")
            return False

        # Check for navigation boilerplate
        nav_words = [
            "home",
            "about",
            "contact",
            "privacy",
            "terms",
            "login",
            "sign in",
            "subscribe",
        ]
        nav_count = sum(1 for word in nav_words if word in content.lower())
        if nav_count > 5:
            logger.debug(
                f"Content has {nav_count} navigation keywords - likely boilerplate"
            )
            return False

        # Check sentence structure
        sentences = re.split(r"[.!?]+", content)
        long_sentences = [s for s in sentences if len(s.strip().split()) > 5]
        if len(long_sentences) < 3:
            logger.debug("Content lacks proper sentence structure")
            return False

        return True
