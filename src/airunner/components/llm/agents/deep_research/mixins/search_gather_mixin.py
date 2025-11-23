"""Search and gather mixin for DeepResearchAgent.

Handles initial search, filtering, and source gathering for research.
"""

import logging
from pathlib import Path
from typing import TypedDict
import json
import re
import math
from datetime import datetime
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from airunner.components.llm.tools.research_document_tools import (
    create_research_document,
    append_research_notes,
)
from airunner.components.llm.tools.web_tools import (
    search_web,
    search_news,
    scrape_website,
)
from airunner.components.tools.search_tool import AggregatedSearchTool
from langchain_core.messages import HumanMessage
from airunner.components.tools.web_content_extractor import WebContentExtractor
from airunner.components.llm.agents.deep_research.mixins.content_extraction_mixin import (
    ContentExtractionMixin,
)
from airunner.components.llm.agents.deep_research.mixins.result_ranking_mixin import (
    ResultRankingMixin,
)
from airunner.components.llm.agents.deep_research.mixins.search_enhancement_mixin import (
    SearchEnhancementMixin,
)

logger = logging.getLogger(__name__)


class DeepResearchState(TypedDict):
    """Type definition for deep research state."""

    messages: list
    current_phase: str
    research_topic: str
    clean_topic: str
    search_queries: list
    document_path: str
    notes_path: str
    scraped_urls: list


class SearchGatherMixin(
    ContentExtractionMixin, ResultRankingMixin, SearchEnhancementMixin
):
    """Provides search and initial gathering methods."""

    def _is_structured_data(self, content: str) -> bool:
        """Detect if content is primarily structured data/tables rather than prose.

        Args:
            content: Raw web content

        Returns:
            True if content appears to be data tables/structured content
        """
        # Look for indicators of structured data
        structured_indicators = [
            "| - |",  # Markdown table separators
            "|||",  # Multiple consecutive pipes
        ]

        # Check if content has high density of table indicators
        indicator_count = sum(
            1 for indicator in structured_indicators if indicator in content
        )

        # Check for high pipe density (markdown tables)
        pipe_count = content.count("|")
        content_length = len(content)
        pipe_density = pipe_count / max(content_length, 1)

        # If more than 3 table indicators or high pipe density, it's structured data
        is_structured = indicator_count >= 3 or pipe_density > 0.02

        if is_structured:
            logger.info(
                f"[Content Filter] Detected structured data (indicators: {indicator_count}, pipe density: {pipe_density:.3f})"
            )

        return is_structured

    def _should_use_llm_filtering(self, topic: str) -> bool:
        """Determine if LLM filtering should be used for this topic.

        Use LLM filtering for:
        - Personal names (likely low-information topics)
        - Very specific/niche topics

        Skip LLM filtering for:
        - General topics with lots of information
        - Well-known events/policies

        Args:
            topic: Research topic

        Returns:
            True if LLM filtering should be used
        """
        topic_lower = topic.lower()

        # Check if topic looks like a person's name (2-3 capitalized words, short)
        words = topic.split()
        if len(words) <= 3 and all(w[0].isupper() for w in words if w):
            # Looks like a name
            logger.info(
                f"[Phase 1A] Enabling LLM filtering for personal name: {topic}"
            )
            return True

        # Check for very specific or niche indicators
        niche_indicators = ["specific", "particular", "individual", "personal"]
        if any(indicator in topic_lower for indicator in niche_indicators):
            logger.info(
                f"[Phase 1A] Enabling LLM filtering for niche topic: {topic}"
            )
            return True

        # General topics don't need LLM filtering
        return False

    def _create_research_files(self, topic: str, state: dict) -> dict:
        """Create research document and notes files."""
        try:

            # CRITICAL: Pass api parameter to avoid "Error: API not available"
            doc_path = create_research_document(topic=topic, api=self._api)

            # Validate the document path before proceeding
            if not doc_path or "Error" in doc_path:
                logger.error(f"Document creation failed: {doc_path}")
                raise ValueError(f"Invalid document path: {doc_path}")

            # Create notes file with proper header including current date/time
            notes_path = Path(doc_path).with_suffix(".notes.md")

            # Write proper header with structured format
            notes_header = f"""# {topic}
**Date: {datetime.now().strftime("%Y-%m-%d")}**

## Notes

"""
            with open(notes_path, "w", encoding="utf-8") as f:
                f.write(notes_header)

            logger.info(
                f"Created research files: {doc_path}, notes: {notes_path}"
            )
            return {
                "document_path": str(doc_path),
                "notes_path": str(notes_path),
            }
        except Exception as e:
            logger.error(
                f"Failed to create research files: {e}", exc_info=True
            )
            # Return state unchanged - this will cause later phases to fail gracefully
            return {}

    def _run_searches(self, query: str) -> list:
        """Run web and news searches, return combined results.

        Fetches top 50 results from each source to ensure comprehensive coverage.
        """
        collected = []

        try:
            # Fetch 50 web results for comprehensive coverage
            web_results = AggregatedSearchTool.aggregated_search_sync(
                query, category="web", num_results=50
            )
            if web_results and web_results.get("duckduckgo"):
                collected.extend(web_results["duckduckgo"])
                logger.info(
                    f"[Phase 1A] Found {len(web_results['duckduckgo'])} web results"
                )
        except Exception as e:
            logger.error(f"[Phase 1A] Web search failed: {e}")

        try:
            # Fetch 50 news results
            news_results = AggregatedSearchTool.aggregated_search_sync(
                query, category="news", num_results=50
            )
            if news_results and news_results.get("duckduckgo"):
                collected.extend(news_results["duckduckgo"])
                logger.info(
                    f"[Phase 1A] Found {len(news_results['duckduckgo'])} news results"
                )
        except Exception as e:
            logger.error(f"[Phase 1A] News search failed: {e}")

        return collected

    def _detect_subject_type(self, topic: str) -> str:
        """Detect whether the subject is a person, place, organization, event, concept or thing.

        First attempts a lightweight heuristic, then falls back to the LLM for ambiguous cases.
        """
        # First try a heuristic
        h = self._detect_subject_type_heuristic(topic)
        if h:
            return h

        # Fallback to LLM classification
        try:
            ans = self._detect_subject_type_llm(topic)
            if ans:
                return ans
        except Exception:
            pass

        # Default fallback
        return "unknown"

    def _detect_subject_type_heuristic(self, topic: str) -> str | None:
        """Lightweight heuristics for subject type detection.

        Returns 'person' or 'place' where applicable, otherwise None.
        """
        words = [w for w in topic.split() if w]
        if 1 < len(words) <= 3 and all(w[0].isupper() for w in words if w):
            logger.info(
                f"[Phase 1A] Detected probable person by heuristic: {topic}"
            )
            return "person"

        # Heuristic: contains location-like words
        location_indicators = [
            "city",
            "town",
            "village",
            "country",
            "state",
            "mountain",
        ]
        if any(ind in topic.lower() for ind in location_indicators):
            return "place"

        return None

    def _detect_subject_type_llm(self, topic: str) -> str | None:
        """LLM-based subject type classification. Returns a single word or None."""
        prompt = f"""Classify the following search subject in one word: person, place, organization, event, concept, or thing.

SUBJECT: {topic}

Return only one of these words (lowercase) and nothing else."""
        response = self._base_model.invoke([HumanMessage(content=prompt)])
        ans = response.content.strip().lower()
        if ans in {
            "person",
            "place",
            "organization",
            "event",
            "concept",
            "thing",
        }:
            logger.info(f"[Phase 1A] LLM detected subject type: {ans}")
            return ans
        return None

    def _build_person_profile(self, topic: str, notes_path: str) -> dict:
        """Build a simple profile object for a person using the top search results.

        The profile contains some common fields; missing fields are omitted.
        """
        try:
            search_results = self._run_searches(topic)
            top_items = search_results[:8]

            # Get snippets for LLM from top results
            snippets = self._fetch_person_snippets(top_items)
            if not snippets:
                return {}

            sample_text = "\n\n".join(s["text"][:4000] for s in snippets)
            profile = self._ask_llm_for_person_profile(topic, sample_text)
            return profile or {}
        except Exception as e:
            logger.warning(f"Failed to build person profile: {e}")
            return {}

    # moved helpers in SearchEnhancementMixin

    def _enhance_results_with_cross_links(
        self,
        results: list,
        topic: str,
        subject_type: str = "unknown",
        person_profile: dict | None = None,
        top_n: int = 15,
    ) -> list:
        """Fetch link lists for top results and compute cross-link and age relevance.

        This will adjust each result's _relevance score in-place.
        """
        candidate_items = results[:top_n]
        urls = [
            item.get("link") or item.get("url") for item in candidate_items
        ]
        url_set = set(u for u in urls if u)

        # Mapping from url to metadata
        meta_map = self._fetch_meta_map_for_urls(candidate_items)

        # Compute cross-link counts
        for item in candidate_items:
            url = item.get("link") or item.get("url")
            if url not in meta_map:
                continue
            orig = float(item.get("_relevance", 0))
            adjust = self._compute_adjustment_for_url(
                url, url_set, meta_map, subject_type, person_profile
            )

            new_score = min(1.0, orig + adjust)
            item["_relevance"] = new_score

        # Re-sort results
        results.sort(key=lambda x: x.get("_relevance", 0), reverse=True)
        return results

    # moved helpers in SearchEnhancementMixin

    # moved helpers in SearchEnhancementMixin

    # moved helpers in SearchEnhancementMixin

    def _filter_search_results(
        self, collected: list, topic: str, already_scraped: set
    ) -> list:
        """Deduplicate and filter search results for relevance."""
        seen = set()
        filtered = []
        topic_lower = topic.lower()

        for item in collected:
            url = item.get("link") or item.get("url")
            if not url or url in seen or url in already_scraped:
                continue

            if self._is_domain_blacklisted(url):
                logger.info(f"[Phase 1A] Skipping blacklisted domain: {url}")
                continue

            if self._is_url_irrelevant_path(url):
                logger.info(f"[Phase 1A] Skipping irrelevant URL path: {url}")
                continue

            seen.add(url)

            title = (item.get("title") or "").lower()
            snippet = (item.get("snippet") or "").lower()
            topic_words = topic_lower.split()

            # Determine relevance based on topic word presence
            topic_match_count = sum(
                1 for word in topic_words if word in title or word in snippet
            )
            relevance_score = topic_match_count / max(len(topic_words), 1)

            # Only include if at least 50% of topic words are present
            if relevance_score >= 0.5:
                item["_relevance"] = relevance_score
                filtered.append(item)

        # Sort by relevance score (highest first)
        filtered.sort(key=lambda x: x.get("_relevance", 0), reverse=True)
        logger.info(
            f"[Phase 1A] Filtered {len(collected)} results to {len(filtered)} relevant ones"
        )

        return filtered

    def _scrape_and_note_sources(
        self,
        filtered: list,
        notes_path: str,
        max_sources: int,
        already_scraped: set,
        topic: str,
    ) -> int:
        """Scrape filtered sources in parallel and append LLM-extracted facts to notes."""
        # Prepare URLs to scrape
        urls_to_scrape = []
        items_by_url = {}

        for item in filtered:
            if len(urls_to_scrape) >= max_sources:
                break
            url = item.get("link") or item.get("url")
            if url and url not in already_scraped:
                urls_to_scrape.append(url)
                items_by_url[url] = item

        if not urls_to_scrape:
            return 0

        logger.info(
            f"[Phase 1A] Scraping {len(urls_to_scrape)} URLs in parallel (max_workers=5)"
        )

        # PHASE 1: Parallel scraping - collect all raw content
        scraped_data = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all scraping tasks
            future_to_url = {
                executor.submit(
                    self._scrape_content_only,
                    url,
                    items_by_url[url],
                    topic,
                ): url
                for url in urls_to_scrape
            }

            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    scrape_result = future.result()
                    if scrape_result:
                        scraped_data.append(scrape_result)
                        self._emit_progress(
                            "Phase 1A",
                            f"Scraped {len(scraped_data)}/{len(urls_to_scrape)} sources",
                        )
                except Exception as e:
                    logger.warning(
                        f"[Phase 1A] Scraping future failed for {url}: {e}"
                    )

        if not scraped_data:
            logger.warning("[Phase 1A] No content scraped successfully")
            return 0

        # PHASE 2: Individual LLM extraction - process each source separately for better quality
        self._emit_progress(
            "Phase 1A", "Extracting facts from scraped content..."
        )

        extracted_notes = []
        for idx, item in enumerate(scraped_data, 1):
            logger.info(
                f"[Phase 1A] Extracting facts from source {idx}/{len(scraped_data)}: {item['title']}"
            )
            try:
                facts = self._extract_facts_with_llm(
                    item["content"],
                    topic,
                    item["url"],
                    item["title"],
                    item["metadata"],
                )
                if facts:
                    extracted_notes.append(
                        {
                            "url": item["url"],
                            "title": item["title"],
                            "facts": facts,
                            "metadata": item["metadata"],
                        }
                    )
                    self._emit_progress(
                        "Phase 1A",
                        f"Extracted facts from {len(extracted_notes)}/{len(scraped_data)} sources",
                    )
                else:
                    logger.info(
                        f"[Phase 1A] No relevant facts found in {item['url']}"
                    )
            except Exception as e:
                logger.error(
                    f"[Phase 1A] Extraction failed for {item['url']}: {e}"
                )

        if not extracted_notes:
            logger.warning(
                "[Phase 1A] No facts extracted from scraped content"
            )
            return 0

        # PHASE 3: Write all notes at once
        logger.info(
            f"[Phase 1A] Writing {len(extracted_notes)} notes to {notes_path}"
        )
        scraped_count = 0
        for note_data in extracted_notes:
            try:
                self._save_structured_note(
                    notes_path,
                    note_data["title"],
                    note_data["url"],
                    note_data["facts"],
                    note_data["metadata"],
                )
                already_scraped.add(note_data["url"])
                scraped_count += 1
            except Exception as e:
                logger.error(
                    f"[Phase 1A] Failed to save note for {note_data['url']}: {e}"
                )

        logger.info(
            f"[Phase 1A] Processing completed: {scraped_count} notes saved"
        )
        return scraped_count

    def _scrape_content_only(
        self, url: str, item: dict, topic: str
    ) -> dict | None:
        """Scrape a single URL and return raw content without LLM extraction.

        Args:
            url: URL to scrape
            item: Search result item with metadata
            topic: Research topic for validation

        Returns:
            Dict with scraped content and metadata, or None if scraping failed
        """
        try:
            result = WebContentExtractor.fetch_and_extract_with_metadata_raw(
                url, use_cache=True, summarize=False
            )

            if not self._validate_scrape_result(result, url):
                return None

            raw_content = result["content"]
            page_title = result.get("title") or item.get("title", "")
            metadata = self._extract_metadata(result)

            # Validate content
            if self._is_structured_data(raw_content):
                logger.info(f"[Phase 1A] Skipping structured data from {url}")
                return None

            if not self._is_content_quality_acceptable(raw_content):
                logger.warning(f"[Phase 1A] Content quality too low for {url}")
                WebContentExtractor._add_to_blocklist(url)
                return None

            # Check cross-reference (LLM validation)
            if not self._check_cross_reference_llm(raw_content, topic, url):
                logger.info(
                    f"[Phase 1A] No cross-reference to '{topic}' in {url}"
                )
                return None

            # Return raw data for batch processing
            return {
                "url": url,
                "title": page_title,
                "content": raw_content,
                "metadata": metadata,
            }

        except Exception as e:
            logger.warning(f"[Phase 1A] Scrape failed for {url}: {e}")
            return None

    def _batch_extract_facts(self, scraped_data: list, topic: str) -> list:
        """Extract facts from multiple sources using batched LLM calls.

        Args:
            scraped_data: List of dicts with url, title, content, metadata
            topic: Research topic

        Returns:
            List of dicts with url, title, facts, metadata
        """
        extracted_notes = []
        batch_size = 3  # Process 3 sources per LLM call

        for batch_idx in range(0, len(scraped_data), batch_size):
            batch = scraped_data[batch_idx : batch_idx + batch_size]
            logger.info(
                f"[Phase 1A] Batch extracting facts from sources {batch_idx+1}-{batch_idx+len(batch)}"
            )

            try:
                # Build batch prompt with multiple sources
                batch_results = self._extract_facts_batch(batch, topic)
                extracted_notes.extend(batch_results)

            except Exception as e:
                logger.error(f"[Phase 1A] Batch extraction failed: {e}")
                # Fall back to individual extraction for this batch
                for item in batch:
                    try:
                        facts = self._extract_facts_with_llm(
                            item["content"],
                            topic,
                            item["url"],
                            item["title"],
                            item["metadata"],
                        )
                        if facts:
                            extracted_notes.append(
                                {
                                    "url": item["url"],
                                    "title": item["title"],
                                    "facts": facts,
                                    "metadata": item["metadata"],
                                }
                            )
                    except Exception as e2:
                        logger.error(
                            f"[Phase 1A] Individual extraction failed for {item['url']}: {e2}"
                        )

        return extracted_notes

    def _extract_facts_batch(self, batch: list, topic: str) -> list:
        """Extract facts from multiple sources in a single LLM call.

        Args:
            batch: List of 2-3 dicts with url, title, content, metadata
            topic: Research topic

        Returns:
            List of dicts with extracted facts for each source
        """
        from langchain_core.messages import HumanMessage

        # Build combined prompt
        sources_text = ""
        for i, item in enumerate(batch, 1):
            content_sample = item["content"][
                :8000
            ]  # Increased from 4000 to capture more detail
            sources_text += f"""
### SOURCE {i}
Title: {item['title']}
URL: {item['url']}
Content:
{content_sample}

"""

        prompt = f"""Extract comprehensive, detailed facts from these {len(batch)} sources about: "{topic}"

{sources_text}

For EACH source, extract ALL relevant information including:
- Key facts, claims, and statements
- Statistics, data points, and numbers
- Quotes from officials or experts (with attribution)
- Policy details, plans, and proposals
- Dates, timelines, and context
- Opposing viewpoints and criticisms
- Background information and explanations

Be thorough and detailed. Format as bullet points:

SOURCE 1:
- [detailed fact 1]
- [detailed fact 2]
- [detailed fact 3]
[... continue with ALL relevant facts ...]

SOURCE 2:
- [detailed fact 1]
- [detailed fact 2]
[... continue with ALL relevant facts ...]

If a source has NO relevant facts, write "SOURCE N: No relevant facts."

Extract ALL relevant facts in detail now:"""

        try:
            response = self._base_model.invoke([HumanMessage(content=prompt)])
            result_text = response.content.strip()

            logger.info(
                f"[Phase 1A] Batch LLM response length: {len(result_text)} chars"
            )
            logger.debug(
                f"[Phase 1A] First 500 chars of response: {result_text[:500]}"
            )

            # Parse results by source
            results = []
            source_pattern = r"SOURCE (\d+):\s*\n(.*?)(?=\nSOURCE \d+:|$)"
            import re

            matches = re.findall(source_pattern, result_text, re.DOTALL)

            logger.info(
                f"[Phase 1A] Regex found {len(matches)} source matches in batch response"
            )

            for source_num_str, facts_text in matches:
                source_idx = int(source_num_str) - 1
                if 0 <= source_idx < len(batch):
                    facts = facts_text.strip()
                    if facts and "no relevant facts" not in facts.lower():
                        logger.info(
                            f"[Phase 1A] Extracted {len(facts)} chars from SOURCE {source_num_str}"
                        )
                        results.append(
                            {
                                "url": batch[source_idx]["url"],
                                "title": batch[source_idx]["title"],
                                "facts": facts,
                                "metadata": batch[source_idx]["metadata"],
                            }
                        )
                    else:
                        logger.info(
                            f"[Phase 1A] SOURCE {source_num_str} marked as no relevant facts"
                        )
                else:
                    logger.warning(
                        f"[Phase 1A] SOURCE {source_num_str} index out of range (batch size: {len(batch)})"
                    )

            logger.info(
                f"[Phase 1A] Batch extracted facts from {len(results)}/{len(batch)} sources"
            )
            return results

        except Exception as e:
            logger.error(f"[Phase 1A] Batch LLM extraction failed: {e}")
            raise

    def _validate_scrape_result(self, result: dict, url: str) -> bool:
        """Validate scraping result."""
        if not result or not result.get("content") or result.get("error"):
            error = result.get("error", "Unknown") if result else "No result"
            logger.warning(f"[Phase 1A] Scraper error for {url}: {error}")
            return False
        return True

    def _extract_metadata(self, result: dict) -> dict:
        """Extract metadata from scrape result."""
        return {
            "author": result.get("author"),
            "publish_date": result.get("publish_date"),
            "description": result.get("description"),
        }

    def _format_publish_date(self, publish_date: str) -> str:
        """Format publish date to YYYY-MM-DD."""
        if publish_date == "Unknown" or not isinstance(publish_date, str):
            return publish_date

        for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%B %d, %Y"]:
            try:
                dt = datetime.strptime(publish_date, fmt)
                return dt.strftime("%Y-%m-%d")
            except:
                continue
        return publish_date

    def _save_structured_note(
        self,
        notes_path: str,
        title: str,
        url: str,
        facts: str,
        metadata: dict,
    ):
        """Save structured note to file."""

        domain = urlparse(url).netloc
        publish_date = self._format_publish_date(
            metadata.get("publish_date") or "Unknown"
        )

        structured_note = f"""### {title} [{domain}]({url})
**Published: {publish_date}**

{facts}

---

"""
        with open(notes_path, "a", encoding="utf-8") as f:
            f.write(structured_note)

    def _phase1a_gather(self, state: DeepResearchState) -> dict:
        """Phase 1A: Gather initial sources by executing search queries."""
        queries = state.get("search_queries", [])
        topic = state.get("clean_topic") or state.get("research_topic", "")

        logger.info(
            f"[Phase 1A] Gathering sources with {len(queries)} queries"
        )

        # Prepare research environment
        state_updates, notes_path = self._prepare_gather_environment(
            topic, state
        )
        if not notes_path:
            return self._gather_error_state(state, state_updates)

        # Determine subject type and build profile if needed
        subject_type = self._detect_subject_type(topic)
        person_profile = {}
        if subject_type == "person":
            person_profile = self._build_person_profile(topic, notes_path)

        # Execute search and ranking
        already_scraped = set(state.get("scraped_urls", []))
        llm_ranked = self._execute_search_and_rank(
            queries, topic, already_scraped, subject_type, person_profile
        )

        # Scrape and note sources
        scraped_count = self._scrape_and_note_sources(
            llm_ranked, notes_path, 20, already_scraped, topic
        )

        logger.info(f"[Phase 1A] Gathered {scraped_count} sources")
        self._emit_progress(
            "Phase 1A", f"Gathered {scraped_count} initial sources"
        )

        # Note: research summary stage has been removed per configuration

        # Update state
        state_updates.update(
            {
                "sources_scraped": scraped_count,
                "scraped_urls": list(already_scraped),
            }
        )
        if person_profile:
            state_updates["person_profile"] = person_profile

        return {
            "messages": state.get("messages", []),
            "current_phase": "phase1a-curiosity",
            **state_updates,
        }

    def _prepare_gather_environment(
        self, topic: str, state: DeepResearchState
    ) -> tuple[dict, str]:
        """Prepare research files and paths for gathering phase."""
        state_updates = self._create_research_files(topic, state)
        notes_path = state_updates.get("notes_path") or state.get(
            "notes_path", ""
        )
        return state_updates, notes_path

    def _gather_error_state(
        self, state: DeepResearchState, state_updates: dict
    ) -> dict:
        """Return error state when notes path unavailable."""
        logger.error("[Phase 1A] No notes path available")
        return {
            "messages": state.get("messages", []),
            "current_phase": "phase1a-curiosity",
            **state_updates,
        }

    def _execute_search_and_rank(
        self,
        queries: list,
        topic: str,
        already_scraped: set,
        subject_type: str = "unknown",
        person_profile: dict | None = None,
    ) -> list:
        """Execute searches and rank results with LLM."""
        all_collected = []
        for query in queries:
            logger.info(f"[Phase 1A] Searching: {query}")
            self._emit_progress("Phase 1A", f"Searching: {query}")
            collected = self._run_searches(query)
            all_collected.extend(collected)

        # Filter and deduplicate
        filtered = self._filter_search_results(
            all_collected, topic, already_scraped
        )

        # Use LLM to rank ALL filtered results
        llm_ranked = self._rank_results_with_llm(
            filtered, topic, max_results=15
        )

        logger.info(
            f"[Phase 1A] LLM ranked {len(filtered)} results, selected top {len(llm_ranked)}"
        )

        # Enhance and adjust ranking using cross-links and age/profile heuristics
        enhanced = self._enhance_results_with_cross_links(
            llm_ranked, topic, subject_type, person_profile
        )
        return enhanced
