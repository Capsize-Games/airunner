"""Search enhancement mixin for meta fetching and scoring helpers.

This mixin provides helper methods for fetching link metadata for results,
computing cross-link and age-based scoring adjustments, and building
person profiles using the LLM.
"""

import logging
from urllib.parse import urlparse
import json
import re

from airunner.components.tools.web_content_extractor import WebContentExtractor
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class SearchEnhancementMixin:
    """Helper methods for search result enhancement."""

    def _fetch_meta_map_for_urls(self, items: list) -> dict:
        """Fetch metadata including links and content for candidate URLs."""
        meta_map = {}
        for item in items:
            url = item.get("link") or item.get("url")
            if not url:
                continue
            try:
                extracted = WebContentExtractor.extract_with_links(url)
                if not extracted:
                    continue
                links = extracted.get("links", []) or []
                content = extracted.get("content", "") or ""
                meta_map[url] = {"links": links, "content": content}
            except Exception:
                continue
        return meta_map

    def _compute_page_age(self, content: str) -> int | None:
        if not content:
            return None
        if hasattr(self, "_extract_approximate_age_from_text"):
            try:
                return self._extract_approximate_age_from_text(content)
            except Exception:
                return None
        return None

    def _compute_adjustment_for_url(
        self,
        url: str,
        url_set: set,
        meta_map: dict,
        subject_type: str,
        person_profile: dict | None,
    ) -> float:
        """Compute adjustment to relevance based on cross-linking and age match."""
        if url not in meta_map:
            return 0.0

        cross_count = self._count_cross_links(url, url_set, meta_map)
        cross_score = cross_count / max(1, len(url_set) - 1)

        profile_age = self._get_profile_age(person_profile)
        page_age = self._compute_page_age(
            meta_map[url].get("content", "") or ""
        )
        age_score = 0.0
        if profile_age and page_age:
            age_score = 1.0 if abs(profile_age - page_age) <= 5 else 0.0

        return self._derive_adjustment_from_scores(
            cross_score, age_score, subject_type
        )

    def _get_profile_age(self, person_profile: dict | None) -> int | None:
        """Return integer profile approximate age if available, otherwise None."""
        if not person_profile:
            return None
        if person_profile.get("approximate_age") is None:
            return None
        return int(person_profile["approximate_age"])  # type: ignore[arg-type]

    def _count_cross_links(
        self, url: str, url_set: set, meta_map: dict
    ) -> int:
        """Count cross links from a url to other candidate urls."""
        if url not in meta_map:
            return 0
        links = meta_map[url]["links"]
        cross_count = 0
        for link in links:
            lurl = link.get("url")
            if not lurl:
                continue
            if lurl in url_set:
                cross_count += 1
            else:
                if self._link_points_to_candidates(lurl, url_set):
                    cross_count += 1
        return cross_count

    def _link_points_to_candidates(self, lurl: str, url_set: set) -> bool:
        """Check if lurl belongs to any of the candidate urls by domain match."""
        try:
            ld = urlparse(lurl).netloc
        except Exception:
            return False
        for u in url_set:
            try:
                if ld and ld in urlparse(u).netloc:
                    return True
            except Exception:
                continue
        return False

    def _build_person_profile_prompt(
        self, topic: str, sample_text: str
    ) -> str:
        return f"""You are a helpful agent that builds concise PERSON profiles using web excerpts.

SUBJECT: {topic}

WEB EXCERPTS (truncated):
{sample_text}

TASK: Create a JSON object with keys: name, aliases (list), occupations (list), locations (list), approximate_age (number or null), notable_projects (list), links (list of URLs). Fill with best-effort data from the excerpts. If unknown, use null or empty list. Return ONLY valid JSON."""

    def _parse_json_from_llm_response(self, content: str) -> dict:
        """Try parsing JSON from the LLM response text; returns dict or {}."""
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            m = re.search(r"\{[\s\S]*\}", content)
            if not m:
                return {}
            try:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {}
        return {}

    def _derive_adjustment_from_scores(
        self, cross_score: float, age_score: float, subject_type: str
    ) -> float:
        if subject_type == "person":
            return 0.25 * cross_score + 0.25 * age_score
        return 0.1 * cross_score

    def _ask_llm_for_person_profile(
        self, topic: str, sample_text: str
    ) -> dict:
        """Ask the LLM to build a JSON person profile and parse the response.

        Args:
            topic: original topic
            sample_text: concatenated web snippets

        Returns:
            parsed profile dict or {} on failure
        """
        try:
            prompt = self._build_person_profile_prompt(topic, sample_text)
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            profile = self._parse_json_from_llm_response(content)
            if not profile:
                return {}
            return profile
        except Exception as e:
            logger.debug(f"LLM person profile parse failure: {e}")
            return {}
