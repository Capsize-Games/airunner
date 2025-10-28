"""
Knowledge extraction worker - extracts facts from conversations.

This worker listens for conversation turns and automatically extracts
factual information when auto_extract_knowledge is enabled.
"""

import json
import logging
from typing import Dict, List, Optional, Any

from airunner.components.application.workers.worker import Worker
from airunner.enums import SignalCode, QueueType
from airunner.components.knowledge.knowledge_memory_manager import (
    KnowledgeMemoryManager,
)
from airunner.components.knowledge.enums import (
    KnowledgeFactCategory,
    KnowledgeSource,
)


class KnowledgeExtractionWorker(Worker):
    """
    Worker that extracts knowledge from conversations.

    Listens for KNOWLEDGE_EXTRACT_FROM_CONVERSATION signal and uses
    an LLM to extract factual information, then stores it in the database.
    """

    queue_type = QueueType.NONE  # Process immediately, don't queue

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.knowledge_manager = None

        # Register signal handlers
        self.register(
            SignalCode.KNOWLEDGE_EXTRACT_FROM_CONVERSATION,
            self.on_extract_knowledge,
        )

    @property
    def km(self) -> KnowledgeMemoryManager:
        """Lazy-load knowledge manager."""
        if self.knowledge_manager is None:
            self.knowledge_manager = KnowledgeMemoryManager()
        return self.knowledge_manager

    def on_extract_knowledge(self, data: Dict):
        """
        Handle knowledge extraction request.

        Args:
            data: Dict with keys:
                - user_message: str - The user's message
                - bot_response: str - The bot's response
                - conversation_id: int - The conversation ID
        """
        try:
            user_message = data.get("user_message", "")
            bot_response = data.get("bot_response", "")
            conversation_id = data.get("conversation_id")

            if not user_message or not bot_response:
                self.logger.warning(
                    "Empty user message or bot response - skipping extraction"
                )
                return

            self.logger.info(
                f"Extracting knowledge from conversation {conversation_id}"
            )

            # Extract facts
            facts = self._extract_facts(
                user_message, bot_response, conversation_id
            )

            if facts:
                self.logger.info(f"Extracted {len(facts)} facts")

                # Emit completion signal
                self.emit_signal(
                    SignalCode.KNOWLEDGE_EXTRACTION_COMPLETE,
                    {
                        "success": True,
                        "facts_count": len(facts),
                        "conversation_id": conversation_id,
                    },
                )
            else:
                self.logger.info("No facts extracted from conversation")
                self.emit_signal(
                    SignalCode.KNOWLEDGE_EXTRACTION_COMPLETE,
                    {
                        "success": True,
                        "facts_count": 0,
                        "conversation_id": conversation_id,
                    },
                )

        except Exception as e:
            self.logger.error(
                f"Error extracting knowledge: {e}", exc_info=True
            )
            self.emit_signal(
                SignalCode.KNOWLEDGE_EXTRACTION_COMPLETE,
                {
                    "success": False,
                    "error": str(e),
                    "conversation_id": conversation_id,
                },
            )

    def _extract_facts(
        self,
        user_message: str,
        bot_response: str,
        conversation_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract facts from a conversation turn using LLM.

        Args:
            user_message: The user's message
            bot_response: The bot's response
            conversation_id: Optional conversation ID

        Returns:
            List of extracted facts with format:
            [{"text": "...", "category": "...", "confidence": 0.9}, ...]
        """
        # Build extraction prompt with user-focused categories
        # Focus on user categories since we're extracting from user conversations
        user_categories = [
            cat.value for cat in KnowledgeFactCategory if cat.is_user_category
        ]
        categories_str = ", ".join(user_categories)

        extraction_prompt = f"""Extract factual information about the user from this conversation turn.
Only extract clear, verifiable facts. Do not extract opinions, questions, or uncertain information.

User: {user_message}
Assistant: {bot_response}

Return a JSON array of facts. Each fact should have:
- "text": The factual statement (e.g., "User has back pain")
- "category": One of [{categories_str}]
- "confidence": Float 0.0-1.0 indicating certainty

Category Guide:
- user_identity: Name, age, gender, pronouns
- user_location: Where user lives, works, travels
- user_preferences: Likes, dislikes, habits, routines
- user_relationships: Family, friends, colleagues
- user_work: Job title, company, projects, responsibilities
- user_interests: Hobbies, topics of interest, entertainment
- user_skills: Technical skills, abilities, talents
- user_goals: Aspirations, plans, objectives
- user_history: Past events, experiences, background
- user_health: Medical conditions, symptoms, treatments, wellness

Examples:
- "I have back pain" → {{"text": "User experiences back pain", "category": "user_health", "confidence": 0.95}}
- "I work as a software engineer" → {{"text": "User works as a software engineer", "category": "user_work", "confidence": 0.95}}
- "I love hiking" → {{"text": "User enjoys hiking", "category": "user_interests", "confidence": 0.95}}
- "I might try yoga" → DO NOT EXTRACT (uncertain/future intention)

Return ONLY valid JSON array, no other text:
"""

        try:
            # Use the LLM to extract facts
            # We'll use a simple synchronous call with low temperature for deterministic output
            from airunner.components.llm.managers.llm_request import LLMRequest

            # Create extraction request with low temperature for structured output
            extraction_request = LLMRequest(
                temperature=0.1,  # Low for JSON generation
                max_new_tokens=500,
                do_sample=True,
                repetition_penalty=1.0,
                do_tts_reply=False,
            )

            # Call LLM via API
            # Note: This is a simplified approach - in production you might want
            # to use the full workflow manager for better integration
            result = self._call_llm_for_extraction(
                extraction_prompt, extraction_request
            )

            if not result:
                return []

            # Parse JSON response
            facts_data = self._parse_extraction_result(result)

            if not facts_data:
                return []

            # Store facts in database
            stored_facts = []
            for fact_data in facts_data:
                try:
                    fact_text = fact_data.get("text", "")
                    category = fact_data.get("category", "other")
                    confidence = fact_data.get("confidence", 0.8)

                    if not fact_text:
                        continue

                    # Validate category - convert legacy categories if needed
                    valid_categories = [
                        cat.value for cat in KnowledgeFactCategory
                    ]
                    if category not in valid_categories:
                        # Try legacy category mapping
                        try:
                            mapped_cat = (
                                KnowledgeFactCategory.from_legacy_category(
                                    category
                                )
                            )
                            category = mapped_cat.value
                            self.logger.info(
                                f"Mapped legacy category '{fact_data.get('category')}' to '{category}'"
                            )
                        except (ValueError, KeyError):
                            self.logger.warning(
                                f"Invalid category '{category}', using 'other'"
                            )
                            category = KnowledgeFactCategory.OTHER.value

                    # Add fact to database
                    fact = self.km.add_fact(
                        text=fact_text,
                        category=category,
                        confidence=confidence,
                        source=KnowledgeSource.CONVERSATION.value,
                        conversation_id=conversation_id,
                    )

                    if fact:
                        stored_facts.append(fact_data)
                        self.logger.info(
                            f"Stored fact: {fact_text} (category: {category})"
                        )

                        # Emit signal for each fact
                        self.emit_signal(
                            SignalCode.KNOWLEDGE_FACT_ADDED,
                            {
                                "fact": fact_text,
                                "category": category,
                                "confidence": confidence,
                                "source": "auto_extracted",
                            },
                        )

                except Exception as e:
                    self.logger.error(
                        f"Error storing fact: {e}", exc_info=True
                    )
                    continue

            return stored_facts

        except Exception as e:
            self.logger.error(f"Error in fact extraction: {e}", exc_info=True)
            return []

    def _call_llm_for_extraction(
        self, prompt: str, llm_request: "LLMRequest"
    ) -> Optional[str]:
        """
        Call LLM to extract facts from the prompt.

        Args:
            prompt: The extraction prompt
            llm_request: LLM generation parameters

        Returns:
            The LLM's response text or None
        """
        try:
            # Import here to avoid circular dependencies
            from airunner.components.llm.managers.llm_model_manager import (
                LLMModelManager,
            )

            # Get or create model manager
            model_manager = LLMModelManager()

            # Ensure model is loaded
            if not model_manager.agent:
                self.logger.warning(
                    "LLM not loaded - loading now for extraction"
                )
                model_manager.load()

            if not model_manager.agent:
                self.logger.error("Failed to load LLM for extraction")
                return None

            # Create request data
            from airunner.enums import LLMActionType

            request_data = {
                "request_data": {
                    "prompt": prompt,
                    "action": LLMActionType.CHAT,
                    "llm_request": llm_request,
                }
            }

            # Call the model manager's handle_request
            result = model_manager.handle_request(
                request_data, extra_context=None
            )

            # Extract response text
            response_text = result.get("response", "")

            return response_text

        except Exception as e:
            self.logger.error(
                f"Error calling LLM for extraction: {e}", exc_info=True
            )
            return None

    def _parse_extraction_result(self, result: str) -> List[Dict[str, Any]]:
        """
        Parse the LLM's JSON response into fact dictionaries.

        Args:
            result: The LLM's response (should be JSON array)

        Returns:
            List of fact dictionaries or empty list if parsing fails
        """
        try:
            # Try to find JSON array in the response
            # Sometimes LLM wraps it in ```json ... ``` or adds extra text

            # Remove code fences if present
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()

            # Remove any leading/trailing whitespace
            result = result.strip()

            # Try to parse JSON
            facts = json.loads(result)

            # Ensure it's a list
            if not isinstance(facts, list):
                self.logger.warning(f"Expected JSON array, got {type(facts)}")
                return []

            return facts

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            self.logger.debug(f"Response was: {result[:200]}")

            # Try to extract any JSON-like structure
            try:
                # Look for [ ... ] pattern
                import re

                match = re.search(r"\[.*\]", result, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    facts = json.loads(json_str)
                    if isinstance(facts, list):
                        return facts
            except:
                pass

            return []

        except Exception as e:
            self.logger.error(
                f"Error parsing extraction result: {e}", exc_info=True
            )
            return []
