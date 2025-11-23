"""Content validation mixin for DeepResearchAgent.

This mixin provides URL and content quality validation methods.
"""

import re
import logging
from urllib.parse import urlparse
from datetime import datetime

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

    # Path segments we treat as irrelevant for scraping/story extraction
    IRRELEVANT_PATH_SEGMENTS = [
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

            # Check if any irrelevant segment is in the path
            for segment in ContentValidationMixin.IRRELEVANT_PATH_SEGMENTS:
                if segment in path:
                    return True

            return False
        except Exception:
            return False

    @staticmethod
    def _is_content_quality_acceptable(content: str) -> bool:
        """Check if scraped content has acceptable quality for research.

        Only rejects content that is:
        - Too short (< 200 chars)
        - Clearly access-blocked (CAPTCHA, 403/404 errors)
        - Completely unusable (no real sentences)

        Note: Fiction/creative writing is NOT rejected here - it will be
        labeled as FICTION by the LLM extraction and included in research
        as contextual information (e.g., author's creative works).

        Args:
            content: Scraped content to validate

        Returns:
            True if content quality is acceptable, False otherwise
        """
        if not content or len(content) < 200:
            return False

        content_lower = content.lower()

        # ONLY check for hard blockers (CAPTCHA, 403/404, etc.)
        # Don't reject just because of cookie notices or JavaScript warnings
        hard_block_phrases = [
            "request access",
            "access denied",
            "complete the captcha",
            "verify you are not a robot",
            "automated scraping",
            "404 not found",
            "page not found",
            "403 forbidden",
        ]

        # Need at least 3 hard blockers to reject (reduces false positives)
        blocked_count = sum(
            1 for phrase in hard_block_phrases if phrase in content_lower
        )

        if blocked_count >= 3:
            logger.debug(
                f"Content contains {blocked_count} hard access-blocking phrases"
            )
            return False

        # Check if content has at least SOME real sentences
        # (Not just navigation/boilerplate)
        sentences = re.split(r"[.!?]+", content)
        long_sentences = [s for s in sentences if len(s.strip().split()) > 8]

        if len(long_sentences) < 2:
            logger.debug(
                "Content lacks real sentence structure (< 2 sentences with 8+ words)"
            )
            return False

        return True

    @staticmethod
    def _extract_approximate_age_from_text(content: str) -> int | None:
        """Extract approximate age from a block of text if present.

        Looks for patterns like "60-year-old", "age 60", "born in 1964",
        and returns the computed age (approximate) or None.
        """
        try:
            from datetime import datetime

            text = content or ""
            # Normalize spacing
            t = " " + text.lower() + " "

            # Pattern: "60-year-old" or "60 year old" or "60-year old"
            m = re.search(r"(\d{1,3})\s*-?\s*years?\s*-?\s*old", t)
            if m:
                return int(m.group(1))

            # Pattern: "age 60"
            m = re.search(r"age\s*(\d{1,3})", t)
            if m:
                return int(m.group(1))

            # Pattern: "born in 1964" or "born 1964"
            m = re.search(r"born\s*(?:in\s*)?(\d{4})", t)
            if m:
                year = int(m.group(1))
                current_year = datetime.now().year
                approx_age = current_year - year
                # Sanity check: only return reasonable ages
                if 0 < approx_age < 150:
                    return approx_age

            # Pattern: "DOB: 1964" or similar
            m = re.search(r"\b(\d{4})\b", t)
            if m:
                year = int(m.group(1))
                current_year = datetime.now().year
                approx_age = current_year - year
                if 0 < approx_age < 150:
                    return approx_age

            return None
        except Exception:
            return None

    def _build_reference_profile(self, primary_subject: str) -> str:
        """Build a reference profile from already-validated sources.

        Args:
            primary_subject: The research subject

        Returns:
            Reference context string with known facts
        """
        if not hasattr(self, "state") or not self.state:
            return ""

        scraped_urls = self.state.get("scraped_urls", [])
        if not scraped_urls:
            return ""

        # Read the notes file to get validated facts
        notes_path = self.state.get("notes_path")
        if not notes_path:
            return ""

        try:
            from pathlib import Path

            notes_file = Path(notes_path)
            if not notes_file.exists():
                return ""

            content = notes_file.read_text()

            # Extract key facts from the first note section
            # Look for the first "### " section
            sections = content.split("\n### ")
            if len(sections) < 2:
                return ""

            first_section = sections[1]

            # Extract occupation/profession
            occupation = None
            if "software engineer" in first_section.lower():
                occupation = "software engineer"
            elif "game developer" in first_section.lower():
                occupation = "game developer"
            elif "farmer" in first_section.lower():
                occupation = "farmer"
            elif "musician" in first_section.lower():
                occupation = "musician"

            # Extract life status
            life_status = None
            if (
                "passed away" in first_section.lower()
                or "died" in first_section.lower()
                or "obituary" in first_section.lower()
            ):
                life_status = "deceased"
            elif (
                "active" in first_section.lower()
                or "currently" in first_section.lower()
            ):
                life_status = "active/alive"

            # Build reference context
            facts = []
            if occupation:
                facts.append(f"Occupation: {occupation}")
            if life_status:
                facts.append(f"Status: {life_status}")

            if facts:
                return f"""
VERIFIED FACTS about "{primary_subject}" from {len(scraped_urls)} validated source(s):
{chr(10).join(f'- {fact}' for fact in facts)}

CRITICAL: This new source MUST match these facts. If it contradicts → REJECT.
"""

        except Exception as e:
            logger.debug(f"Could not build reference profile: {e}")

        return ""

    def _check_cross_reference_llm(
        self,
        content: str,
        primary_subject: str,
        url: str,
        source_info=None,
    ) -> bool:
        """Use LLM to validate if content is about the research subject.

        This uses the LLM as a judge to determine relevance, which is more
        flexible than pattern matching for edge cases.

        Args:
            content: Page content to check
            primary_subject: The main research subject
            url: URL being checked

        Returns:
            True if content appears relevant to the primary subject
        """
        from langchain_core.messages import HumanMessage

        # Truncate content for faster LLM processing
        content_sample = content[:3000] if len(content) > 3000 else content

        # BALANCED validation - inclusive but not completely open
        # Accept likely matches, reject obvious mismatches, let synthesis handle edge cases
        prompt = f"""You are validating if a web page might be relevant to: "{primary_subject}"

URL: {url}

CONTENT SAMPLE (first 3000 chars):
{content_sample}

VALIDATION APPROACH - BALANCED FILTER:

1. **ACCEPT** if the page mentions:
   - The EXACT name/topic match
   - A username, alias, or nickname that could plausibly be the person (w4ffl35, Joe vs Joseph)
   - Related projects, companies, or direct affiliations mentioned BY NAME
   - Same first AND last name with compatible biographical details

2. **REJECT** if:
   - DIFFERENT first name (John ≠ Joe, unless it's clearly a nickname/alias)
   - Different last name (completely different person)
   - Obviously unrelated content (CAPTCHA, error pages, generic directories)
   - Different person entirely (e.g., John Smith the musician when searching for Joe Smith the engineer)

3. **BORDERLINE CASES** (be generous):
   - John vs Johnny vs Jon with SAME last name → ACCEPT (likely related, let synthesis distinguish)
   - Username/handle that might be the person → ACCEPT (f00bfff for John Smith)
   - Related companies/projects mentioned in other sources → ACCEPT
   - Same name, different age/location → ACCEPT (synthesis will note multiple people)

4. **KEY PRINCIPLE**:
   - If first name is CLEARLY different (John vs Joe, David vs Joe) → REJECT
   - If first name is a plausible variation (Joseph/Joey vs Joe) → ACCEPT
   - If it's a username/alias → use context to decide

Respond with ONLY:
PASS: <brief reasoning>
or
FAIL: <brief reasoning>

Your response:"""

        try:
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            decision = response.content.strip()

            # Parse response - looking for PASS or FAIL
            lines = decision.split("\n")
            verdict = lines[0].strip().upper()
            reasoning = (
                lines[1].strip() if len(lines) > 1 else "No reasoning provided"
            )

            is_relevant = "PASS" in verdict
            action = "PASS" if is_relevant else "FAIL"
            logger.info(
                f"Cross-reference LLM {action}: '{url}' for '{primary_subject}'"
            )
            logger.info(f"  Reasoning: {reasoning}")
            return is_relevant

        except Exception as e:
            logger.warning(
                f"LLM cross-reference check failed: {e}, defaulting to pattern matching"
            )
            # Fall back to simpler pattern matching
            return self._check_cross_reference_pattern(
                content, primary_subject, url
            )

    @staticmethod
    def _check_cross_reference_pattern(
        content: str, primary_subject: str, url: str
    ) -> bool:
        """Pattern-based cross-reference validation (fallback method).

        Args:
            content: Page content to check
            primary_subject: The main research subject
            url: URL being checked

        Returns:
            True if content appears relevant to the primary subject
        """
        # Normalize for comparison
        content_lower = content.lower()
        subject_lower = primary_subject.lower()
        url_lower = url.lower()

        # If the subject is a person name (2+ words), apply strict filtering
        subject_parts = subject_lower.split()
        if len(subject_parts) >= 2:  # Likely a person name
            full_name = " ".join(subject_parts)
            first_name = subject_parts[0]
            last_name = subject_parts[-1]

            # Check if URL path contains a name pattern with DIFFERENT first name
            # Pattern: look for common variations like /FirstLast, /first-last, etc.
            import string

            # Extract potential name patterns from URL path
            # e.g., /JohnSmith.htm, /john-smith/, ?user=johnsmith
            url_path = url_lower.split("://")[-1]  # Remove protocol

            # Check if full target name is in URL (good sign)
            if full_name.replace(" ", "") in url_path.replace("-", "").replace(
                "_", ""
            ):
                logger.debug(
                    f"Cross-reference PASS: Full name in URL: '{url}'"
                )
                return True

            # Check if URL has last name but DIFFERENT first name pattern
            if last_name in url_path:
                # Extract potential first names before the last name in URL
                words = re.findall(r"[a-z]{2,}", url_path)
                for word in words:
                    if word == last_name:
                        continue
                    if word != first_name and len(word) >= 3:
                        # Potential different first name - check if it precedes last name
                        pattern = f"{word}[^a-z]*{last_name}"
                        if re.search(pattern, url_path):
                            logger.info(
                                f"Cross-reference FAIL: URL appears to be about different person ('{word} {last_name}' not '{full_name}')"
                            )
                            return False

            # STRICT CHECK: Content must mention the FULL NAME
            if full_name in content_lower:
                logger.debug(f"Cross-reference PASS: Full name in content")
                return True

            # Check if it's a profile/portfolio site
            profile_domains = [
                "github.com",
                "gitlab.com",
                "dev.to",
                "linkedin.com",
                "twitter.com",
                "medium.com",
                "stackoverflow.com",
            ]
            is_profile_site = any(
                domain in url_lower for domain in profile_domains
            )

            # Personal sites with the person's name in domain
            is_personal_site = (
                first_name in url_lower and last_name in url_lower
            )

            if is_profile_site or is_personal_site:
                if last_name in url_lower:
                    logger.debug(
                        f"Cross-reference PASS: Profile/personal site"
                    )
                    return True

            # If we reach here, content does NOT mention the full name
            # Check if it mentions the last name (indicating it's about a different person)
            if last_name in content_lower:
                logger.info(
                    f"Cross-reference FAIL: Mentions last name but not full name - likely different person"
                )
                return False

            # Content doesn't mention the name at all - might still be relevant
            return True

        # For non-person topics, no strict filtering needed
        return True
