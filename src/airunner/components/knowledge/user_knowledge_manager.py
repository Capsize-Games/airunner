"""
User knowledge manager for persistent fact storage.

Automatically extracts and stores facts about the user from conversations,
maintains them in a human-readable markdown file, and indexes them with RAG
for efficient retrieval.
"""

import re
import json
import logging
from typing import List, Dict, Optional, Set
from pathlib import Path
from datetime import datetime

from airunner.components.knowledge.fact_models import Fact, FactCategory
from airunner.settings import AIRUNNER_USER_DATA_PATH


class UserKnowledgeManager:
    """
    Manages persistent knowledge about the user.

    This system continuously grows by extracting facts from conversations
    and maintains them in both human-readable and machine-searchable formats.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.knowledge_dir = Path(AIRUNNER_USER_DATA_PATH) / "knowledge"
        self.facts_json = self.knowledge_dir / "user_facts.json"
        self.facts_cache: List[Fact] = []
        self._ensure_directories()
        self._load_facts()

    def _ensure_directories(self):
        """Create knowledge directory if it doesn't exist."""
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)

    def extract_facts_from_text(
        self, user_message: str, bot_response: str, llm_callable
    ) -> List[Fact]:
        """
        Extract user facts from conversation using LLM.

        Handles both new facts and corrections to existing facts.

        Args:
            user_message: What the user said
            bot_response: What the bot responded
            llm_callable: Function to call LLM for extraction

        Returns:
            List of extracted facts
        """
        # First check if this is a correction/deletion (fail gracefully if it errors)
        try:
            corrections = self._detect_corrections(user_message, llm_callable)
            if corrections:
                self._apply_corrections(corrections)
        except Exception as e:
            self.logger.warning(
                f"Correction detection failed (non-fatal): {e}"
            )
            # Continue with normal extraction even if correction detection fails

        manual_facts = self._extract_attempt_history_facts(user_message)

        # Then extract any new facts
        extraction_prompt = f"""Extract factual information about the user from this conversation.
Only extract explicit statements the user makes about themselves (symptoms, preferences, background, etc.).
Treat first-person descriptions of pain, health issues, treatments tried, or personal circumstances as facts.
Capture when the user confirms they already attempted a recommendation, rejected advice, or described something that did not help.

IMPORTANT: Return ONLY a JSON array. Do not include explanations, markdown, or any other text.
If there are no facts to extract, return an empty array: []

User: {user_message}
Assistant: {bot_response}

Example output:
[
    {{"text": "User's name is John", "category": "identity", "confidence": 0.95}},
    {{"text": "User lives in Seattle", "category": "location", "confidence": 0.90}}
]

Example for health complaints:
Conversation:
User: my neck and back are killing me. tons of pain
Assistant: I'm sorry to hear that. Have you tried any stretches?
Output:
[
    {{"text": "User is experiencing neck pain", "category": "health", "confidence": 0.9}},
    {{"text": "User is experiencing back pain", "category": "health", "confidence": 0.9}}
]

Example when the user already tried something:
Conversation:
User: yes I've already tried stretching but it didn't help
Assistant: Maybe try some gentle stretching routines.
Output:
[
    {{"text": "User has already tried stretching for pain relief", "category": "health", "confidence": 0.85}}
]

Categories: identity, location, preferences, relationships, work, interests, skills, goals, history, health, other

Before you return an empty array, double-check whether the user stated they already tried or refused something. Those statements must be returned as facts.
Your response MUST start with '[' and end with ']'. Do not include any text before or after the JSON array.

Output (JSON array only):"""

        response = llm_callable(
            extraction_prompt, max_tokens=500, temperature=0.1
        )
        llm_facts = self._parse_facts_from_response(response)

        if not manual_facts:
            return llm_facts

        # Merge manual heuristics with LLM output without duplicates
        existing = {fact.text for fact in manual_facts}
        merged = manual_facts.copy()
        for fact in llm_facts:
            if fact.text not in existing:
                merged.append(fact)
        return merged

    def _detect_corrections(
        self, user_message: str, llm_callable
    ) -> Optional[List[Dict]]:
        """
        Detect if user is correcting or deleting previous information.

        Returns list of corrections in format:
        [
          {"action": "delete", "fact": "User lives in Seattle"},
          {"action": "update", "old_fact": "User is 30 years old", "new_fact": "User is 31 years old"}
        ]
        """
        # Look for correction keywords
        correction_keywords = [
            "actually",
            "correction",
            "no ",
            "not ",
            "wrong",
            "incorrect",
            "that's not right",
            "i'm not",
            "i don't",
            "i didn't",
            "never said",
            "mistake",
            "change that",
        ]

        message_lower = user_message.lower()
        if not any(
            keyword in message_lower for keyword in correction_keywords
        ):
            return None

        # Get existing facts for context
        if not self.facts_cache:
            return None

        facts_context = "\n".join([f"- {f.text}" for f in self.facts_cache])

        correction_prompt = f"""The user is correcting or deleting information. 

Current facts about the user:
{facts_context}

User's message: {user_message}

Determine what corrections are needed. Return ONLY a JSON array:
[
  {{"action": "delete", "fact": "exact text of fact to delete"}},
  {{"action": "update", "old_fact": "old fact text", "new_fact": "new fact text", "category": "category", "confidence": 0.9}}
]

If no corrections needed, return: []

Output (JSON array only):"""

        response = llm_callable(
            correction_prompt, max_tokens=300, temperature=0.1
        )

        # Parse response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        if not response or response == "[]":
            return None

        try:
            import re

            json_match = re.search(r"\[[\s\S]*\]", response)
            if json_match:
                response = json_match.group(0)
            corrections = json.loads(response)
            return corrections if corrections else None
        except json.JSONDecodeError:
            self.logger.debug(
                f"Failed to parse correction response: {response[:100]}"
            )
            return None

    def _apply_corrections(self, corrections: List[Dict]):
        """Apply detected corrections to the knowledge base."""
        for correction in corrections:
            action = correction.get("action")

            if action == "delete":
                fact_text = correction.get("fact")
                if fact_text:
                    self.delete_fact(fact_text)

            elif action == "update":
                old_fact = correction.get("old_fact")
                new_fact_text = correction.get("new_fact")
                category = correction.get("category", "other")
                confidence = correction.get("confidence", 0.9)

                if old_fact and new_fact_text:
                    # Create new fact object
                    try:
                        category_enum = FactCategory(category)
                    except ValueError:
                        category_enum = FactCategory.OTHER

                    new_fact = Fact(
                        text=new_fact_text,
                        category=category_enum,
                        confidence=confidence,
                        source="correction",
                    )
                    self.update_fact(old_fact, new_fact)

    def _extract_attempt_history_facts(self, user_message: str) -> List[Fact]:
        """Heuristically detect remedies or actions the user already tried."""

        attempt_keywords = [
            "stretch",
            "exercise",
            "therapy",
            "medicat",
            "ibuprofen",
            "naproxen",
            "advil",
            "tylenol",
            "heat",
            "ice",
            "rest",
            "yoga",
            "chiropract",
            "massage",
            "physical therapy",
            "pt",
            "treatment",
            "doctor",
        ]

        failure_phrases = [
            "didn't help",
            "did not help",
            "doesn't help",
            "does not help",
            "didn't work",
            "did not work",
            "made it worse",
            "made things worse",
            "wasn't effective",
            "was not effective",
            "no relief",
        ]

        patterns = [
            (
                r"\b(?:i['’]?ve|i have|i)\s+(?:already\s+)?tried\s+"
                r"(?P<thing>[^.,;!?]+?)(?:\s+(?:but|and)\s+(?P<outcome>[^.,;!?]+))?"
                r"(?:[.,;!?]|$)"
            ),
        ]

        facts: List[Fact] = []
        seen: Set[str] = set()

        for pattern in patterns:
            for match in re.finditer(
                pattern, user_message, flags=re.IGNORECASE
            ):
                thing = match.group("thing") or ""
                thing_clean = thing.strip().strip("'\" ")
                if not thing_clean:
                    continue

                thing_lower = thing_clean.lower()
                if not any(
                    keyword in thing_lower for keyword in attempt_keywords
                ):
                    continue

                outcome_text = match.groupdict().get("outcome") or ""
                tail_context = user_message[match.end() : match.end() + 120]
                combined_outcome = f"{outcome_text} {tail_context}".lower()
                failed = any(
                    phrase in combined_outcome for phrase in failure_phrases
                )

                if failed:
                    fact_text = f"User has already tried {thing_clean} but it did not help"
                    confidence = 0.7
                else:
                    fact_text = f"User has already tried {thing_clean}"
                    confidence = 0.75

                normalized = fact_text.strip()
                if normalized.lower() in seen:
                    continue

                seen.add(normalized.lower())
                facts.append(
                    Fact(
                        text=normalized,
                        category=FactCategory.HEALTH,
                        confidence=confidence,
                        source="conversation",
                    )
                )
                self.logger.debug(
                    "Detected attempted remedy fact from message: %s",
                    normalized,
                )

        return facts

    def _parse_facts_from_response(self, response: str) -> List[Fact]:
        """Parse facts from LLM JSON response."""
        response = response.strip()

        # Remove markdown code blocks
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        if not response:
            return []

        decoder = json.JSONDecoder()
        arrays: List[List[Dict]] = []

        idx = 0
        while idx < len(response):
            start = response.find("[", idx)
            if start == -1:
                break
            try:
                candidate, offset = decoder.raw_decode(response[start:])
            except json.JSONDecodeError:
                idx = start + 1
                continue

            if isinstance(candidate, list):
                arrays.append(candidate)
            idx = start + offset

        if not arrays:
            self.logger.warning(
                "Failed to locate JSON array in extraction response"
            )
            self.logger.debug(f"Response was: {response[:200]}")
            return []

        parsed_array = next((arr for arr in arrays if arr), arrays[0])

        result = []
        for f in parsed_array:
            # Handle both string and list for "text" field
            text = f.get("text", "")
            if isinstance(text, list):
                text = " ".join(str(t) for t in text)  # Join list into string
            text = str(text).strip()

            if not text:
                continue  # Skip empty facts

            # Handle both string and list for "category" field
            category_raw = f.get("category", "other")
            if isinstance(category_raw, list):
                # Take first category if it's a list
                category_str = (
                    str(category_raw[0]).lower() if category_raw else "other"
                )
            else:
                category_str = str(category_raw).lower()

            try:
                # Try direct match first
                category = FactCategory(category_str)
            except ValueError:
                # Try to map common categories to valid ones
                category_mapping = {
                    "medical": FactCategory.HEALTH,
                    "personal": FactCategory.IDENTITY,
                    "hobby": FactCategory.INTERESTS,
                    "job": FactCategory.WORK,
                    "family": FactCategory.RELATIONSHIPS,
                    "friend": FactCategory.RELATIONSHIPS,
                    "like": FactCategory.PREFERENCES,
                    "dislike": FactCategory.PREFERENCES,
                }
                category = category_mapping.get(
                    category_str, FactCategory.OTHER
                )

            result.append(
                Fact(
                    text=text,
                    category=category,
                    confidence=f.get("confidence", 0.8),
                    source="conversation",
                )
            )
        return result

    def add_facts(self, new_facts: List[Fact]):
        """Add new facts, consolidating with existing ones."""
        if not new_facts:
            return

        consolidated = self._consolidate_facts(self.facts_cache, new_facts)
        self.facts_cache = consolidated
        self._save_facts()
        self.logger.info(
            f"Added {len(new_facts)} new facts. Total: {len(self.facts_cache)}"
        )

    def update_fact(self, old_text: str, new_fact: Fact) -> bool:
        """
        Update an existing fact.

        Args:
            old_text: Text of the fact to update
            new_fact: New fact data to replace it with

        Returns:
            True if fact was updated, False if not found
        """
        old_text_lower = old_text.lower()
        for i, fact in enumerate(self.facts_cache):
            if fact.text.lower() == old_text_lower:
                self.facts_cache[i] = new_fact
                self.facts_cache[i].timestamp = datetime.now()
                self._save_facts()
                self.logger.info(
                    f"Updated fact: '{old_text}' -> '{new_fact.text}'"
                )
                return True

        self.logger.warning(f"Fact not found for update: '{old_text}'")
        return False

    def delete_fact(self, fact_text: str) -> bool:
        """
        Delete a fact by its text.

        Args:
            fact_text: Text of the fact to delete

        Returns:
            True if fact was deleted, False if not found
        """
        fact_text_lower = fact_text.lower()
        original_count = len(self.facts_cache)
        self.facts_cache = [
            f for f in self.facts_cache if f.text.lower() != fact_text_lower
        ]

        if len(self.facts_cache) < original_count:
            self._save_facts()
            self.logger.info(f"Deleted fact: '{fact_text}'")
            return True

        self.logger.warning(f"Fact not found for deletion: '{fact_text}'")
        return False

    def replace_fact(
        self, old_text: str, new_text: str, new_confidence: float = None
    ) -> bool:
        """
        Replace fact text while preserving other attributes.

        Args:
            old_text: Text of the fact to replace
            new_text: New text
            new_confidence: Optional new confidence (keeps old if None)

        Returns:
            True if fact was replaced, False if not found
        """
        old_text_lower = old_text.lower()
        for fact in self.facts_cache:
            if fact.text.lower() == old_text_lower:
                fact.text = new_text
                if new_confidence is not None:
                    fact.confidence = new_confidence
                fact.timestamp = datetime.now()
                self._save_facts()
                self.logger.info(
                    f"Replaced fact text: '{old_text}' -> '{new_text}'"
                )
                return True

        self.logger.warning(f"Fact not found for replacement: '{old_text}'")
        return False

    def _consolidate_facts(
        self, existing: List[Fact], new_facts: List[Fact]
    ) -> List[Fact]:
        """
        Merge new facts with existing, handling duplicates.

        For now, simple text matching. Future: semantic similarity.
        """
        existing_texts = {f.text.lower() for f in existing}
        consolidated = existing.copy()

        for fact in new_facts:
            if fact.text.lower() not in existing_texts:
                consolidated.append(fact)
            else:
                # Update confidence if fact already exists
                for existing_fact in consolidated:
                    if existing_fact.text.lower() == fact.text.lower():
                        existing_fact.confidence = max(
                            existing_fact.confidence, fact.confidence
                        )
                        existing_fact.timestamp = datetime.now()

        return consolidated

    def _load_facts(self):
        """Load facts from JSON file."""
        if not self.facts_json.exists():
            self.facts_cache = []
            return

        with open(self.facts_json, "r") as f:
            content = f.read().strip()
            if not content:
                self.facts_cache = []
                return
            data = json.loads(content)
            self.facts_cache = [Fact.from_dict(f) for f in data]

        self.logger.info(
            f"Loaded {len(self.facts_cache)} facts from {self.facts_json}"
        )

    def _save_facts(self):
        """Save facts to JSON with pretty formatting."""
        with open(self.facts_json, "w") as f:
            json.dump(
                [f.to_dict() for f in self.facts_cache],
                f,
                indent=2,
                ensure_ascii=False,
            )
        self.logger.debug(
            f"Saved {len(self.facts_cache)} facts to {self.facts_json}"
        )

    def get_core_facts(self, max_facts: int = 10) -> List[Fact]:
        """
        Get essential facts that should always be in context.

        Core categories: identity, location, preferences

        Args:
            max_facts: Maximum number of core facts

        Returns:
            List of core facts sorted by confidence and recency
        """
        from airunner.components.knowledge.fact_models import FactCategory

        core_categories = [
            FactCategory.IDENTITY,
            FactCategory.LOCATION,
            FactCategory.PREFERENCES,
        ]

        # Filter core facts
        core_facts = [
            f for f in self.facts_cache if f.category in core_categories
        ]

        # Sort by confidence and recency
        sorted_facts = sorted(
            core_facts,
            key=lambda f: (f.confidence, f.timestamp),
            reverse=True,
        )[:max_facts]

        return sorted_facts

    def get_relevant_facts(self, query: str, max_facts: int = 5) -> List[Fact]:
        """
        Get facts relevant to the current query using keyword matching.

        Future: Use semantic search with embeddings.

        Args:
            query: User's query text
            max_facts: Maximum number of relevant facts

        Returns:
            List of relevant facts sorted by relevance
        """
        if not self.facts_cache:
            return []

        if not query:
            # No query provided, return top facts by confidence
            sorted_facts = sorted(
                self.facts_cache,
                key=lambda f: (f.confidence, f.timestamp),
                reverse=True,
            )
            return sorted_facts[:max_facts]

        query_lower = query.lower()

        # Score facts by keyword matching
        scored_facts = []
        for fact in self.facts_cache:
            score = 0
            fact_text_lower = fact.text.lower()

            # Direct text match
            if query_lower in fact_text_lower:
                score += 10

            # Category name match
            if fact.category.value in query_lower:
                score += 5

            # Keyword overlap
            query_words = set(query_lower.split())
            fact_words = set(fact_text_lower.split())
            overlap = len(query_words & fact_words)
            score += overlap

            # Boost by confidence
            score *= fact.confidence

            if score > 0:
                scored_facts.append((score, fact))

        # If no matches found (generic query), return all facts by confidence
        if not scored_facts:
            sorted_facts = sorted(
                self.facts_cache,
                key=lambda f: (f.confidence, f.timestamp),
                reverse=True,
            )
            return sorted_facts[:max_facts]

        # Sort by score (descending) and take top N
        scored_facts.sort(key=lambda x: x[0], reverse=True)
        return [fact for _, fact in scored_facts[:max_facts]]

    def get_context_for_conversation(
        self,
        max_facts: int = 20,
        query: str = None,
        core_facts_count: int = None,
        rag_facts_count: int = None,
        use_rag: bool = False,
        is_new_conversation: bool = False,
    ) -> str:
        """
        Get formatted knowledge to inject into conversation context.

        Supports hybrid approach:
        - Core facts: Always included (identity, location, preferences)
        - RAG facts: Retrieved based on query relevance

        Args:
            max_facts: Maximum total facts (legacy parameter)
            query: User query for RAG retrieval
            core_facts_count: Number of core facts to include
            rag_facts_count: Number of RAG facts to include
            use_rag: Enable RAG retrieval
            is_new_conversation: Deprecated, no longer used

        Returns:
            Formatted string for system prompt
        """
        if not self.facts_cache:
            return ""

        facts_to_include = []

        if use_rag and core_facts_count is not None:
            # Hybrid approach: core + RAG
            self.logger.info(
                f"Using hybrid approach: {core_facts_count} core + {rag_facts_count} RAG facts"
            )

            # Get core facts (always included)
            core_facts = self.get_core_facts(max_facts=core_facts_count)
            facts_to_include.extend(core_facts)

            # Get RAG facts if query provided and count > 0
            if query and rag_facts_count and rag_facts_count > 0:
                rag_facts = self.get_relevant_facts(
                    query=query, max_facts=rag_facts_count
                )
                # Avoid duplicates
                core_texts = {f.text for f in core_facts}
                rag_facts = [f for f in rag_facts if f.text not in core_texts]
                facts_to_include.extend(rag_facts)

                self.logger.info(
                    f"Retrieved {len(core_facts)} core + {len(rag_facts)} RAG facts"
                )
            else:
                self.logger.info(
                    f"Retrieved {len(core_facts)} core facts only (RAG skipped)"
                )
        else:
            # Legacy approach: top N facts by confidence
            sorted_facts = sorted(
                self.facts_cache,
                key=lambda f: (f.confidence, f.timestamp),
                reverse=True,
            )[:max_facts]
            facts_to_include = sorted_facts

        if not facts_to_include:
            return ""

        # Build fact context with intelligent usage instructions
        context = "------\n"
        context += "## What I Know About You\n\n"

        for fact in facts_to_include:
            context += f"- {fact.text}\n"

        context += (
            "\n**Usage rules:**\n"
            "- ONLY use facts relevant to the current conversation topic.\n"
            "- Don't ask questions already answered above.\n"
            "- Don't repeat suggestions the user already tried.\n"
            "- Let the user guide the conversation - don't force old topics.\n"
            "------\n"
        )

        return context

    def query_facts(self, query: str) -> List[Fact]:
        """
        Search facts by text matching.

        Future: Use semantic search with embeddings.
        """
        query_lower = query.lower()
        matching = [
            f for f in self.facts_cache if query_lower in f.text.lower()
        ]
        return sorted(matching, key=lambda f: f.confidence, reverse=True)

    def get_all_facts(self) -> List[Fact]:
        """Get all stored facts."""
        return self.facts_cache.copy()

    def clear_facts(self):
        """Clear all stored facts. Use with caution."""
        self.facts_cache = []
        self._save_facts()
        self.logger.warning("Cleared all user facts")
