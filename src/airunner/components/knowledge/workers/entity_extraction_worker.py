"""
Entity extraction worker - extracts entities and relationships from facts.

This worker analyzes knowledge facts to identify named entities (people,
places, organizations) and creates relationship links in the database.
"""

import json
from typing import Dict, List, Optional

from airunner.components.application.workers.worker import Worker
from airunner.enums import SignalCode, QueueType
from airunner.components.knowledge.knowledge_memory_manager import (
    KnowledgeMemoryManager,
)
from airunner.components.knowledge.enums import (
    KnowledgeRelationshipType,
    EntityType,
)
from airunner.components.data.session_manager import session_scope
from airunner.components.knowledge.data.knowledge_relationship import (
    KnowledgeRelationship,
)


class EntityExtractionWorker(Worker):
    """
    Worker that extracts entities and relationships from knowledge facts.

    Processes knowledge facts to identify entities and create relationship
    links for graph queries and fact verification.
    """

    queue_type = QueueType.GET_LAST_ITEM  # Process most recent request

    # Default entity type for invalid/unknown entities
    DEFAULT_ENTITY_TYPE = EntityType.CONCEPT.value

    def __init__(self):
        super().__init__()
        self.knowledge_manager = None

        # Register signal handlers
        self.register(
            SignalCode.KNOWLEDGE_EXTRACT_ENTITIES, self.on_extract_entities
        )

    @property
    def km(self) -> KnowledgeMemoryManager:
        """Lazy-load knowledge manager."""
        if self.knowledge_manager is None:
            self.knowledge_manager = KnowledgeMemoryManager()
        return self.knowledge_manager

    def on_extract_entities(self, data: Dict):
        """
        Handle entity extraction request.

        Args:
            data: Dict with keys:
                - fact_id: int - ID of fact to analyze
                - fact_text: str - Text of the fact
        """
        try:
            fact_id = data.get("fact_id")
            fact_text = data.get("fact_text")

            if not fact_id or not fact_text:
                self.logger.warning("Missing fact_id or fact_text")
                return

            self.logger.info(f"Extracting entities from fact {fact_id}")

            # Extract entities and create relationships
            entities = self._extract_entities_from_fact(fact_id, fact_text)

            if entities:
                self.logger.info(
                    f"Extracted {len(entities)} entities from fact {fact_id}"
                )

                self.emit_signal(
                    SignalCode.KNOWLEDGE_ENTITY_EXTRACTION_COMPLETE,
                    {
                        "success": True,
                        "fact_id": fact_id,
                        "entities_count": len(entities),
                    },
                )
            else:
                self.logger.info(f"No entities extracted from fact {fact_id}")

        except Exception as e:
            self.logger.error(
                f"Error in entity extraction: {e}", exc_info=True
            )
            self.emit_signal(
                SignalCode.KNOWLEDGE_ENTITY_EXTRACTION_COMPLETE,
                {
                    "success": False,
                    "error": str(e),
                    "fact_id": data.get("fact_id"),
                },
            )

    def _extract_entities_from_fact(
        self, fact_id: int, fact_text: str
    ) -> List[Dict]:
        """
        Extract entities from a fact using LLM.

        Args:
            fact_id: ID of the fact
            fact_text: Text content of the fact

        Returns:
            List of extracted entities with metadata
        """
        entity_types_str = ", ".join([et.value for et in EntityType])

        extraction_prompt = f"""Extract named entities from this factual statement.

Fact: "{fact_text}"

Identify ALL named entities in the fact. For each entity, provide:
- "name": The entity name (person, place, organization, etc.)
- "type": One of [{entity_types_str}]
- "confidence": Float 0.0-1.0 indicating certainty

Entity Types:
- person: People's names (John, Dr. Smith, etc.)
- place: Locations (New York, Main Street, Building 5)
- organization: Companies, groups (Google, Red Cross, Team Alpha)
- product: Specific products or brands (iPhone, Excel)
- concept: Abstract concepts or topics (artificial intelligence, democracy)
- event: Named events (World War II, Olympics 2024)
- date: Specific dates or times (Monday, 2023, 3pm)

Examples:
- "John works at Google" → [{{"name": "John", "type": "person", "confidence": 0.95}}, {{"name": "Google", "type": "organization", "confidence": 0.95}}]
- "User lives in New York" → [{{"name": "New York", "type": "place", "confidence": 0.95}}]
- "Scheduled meeting for Monday" → [{{"name": "Monday", "type": "date", "confidence": 0.9}}]

Return ONLY valid JSON array, no other text. If no entities found, return []:
"""

        try:
            # Use the LLM to extract entities
            from airunner.components.llm.managers.llm_request import LLMRequest

            extraction_request = LLMRequest(
                temperature=0.1,  # Low for JSON generation
                max_new_tokens=300,
                do_sample=True,
                repetition_penalty=1.0,
                do_tts_reply=False,
            )

            result = self._call_llm_for_extraction(
                extraction_prompt, extraction_request
            )

            if not result:
                return []

            # Parse JSON response
            entities_data = self._parse_extraction_result(result)

            if not entities_data:
                return []

            # Create relationship records
            stored_entities = []
            with session_scope() as session:
                for entity_data in entities_data:
                    try:
                        entity_name = entity_data.get("name", "")
                        entity_type = entity_data.get("type", "concept")
                        confidence = entity_data.get("confidence", 0.8)

                        if not entity_name:
                            continue

                        # Validate entity type
                        try:
                            EntityType(entity_type)
                        except ValueError:
                            self.logger.warning(
                                f"Invalid entity type '{entity_type}', using '{self.DEFAULT_ENTITY_TYPE}'"
                            )
                            entity_type = self.DEFAULT_ENTITY_TYPE

                        # Check if relationship already exists
                        existing = (
                            session.query(KnowledgeRelationship)
                            .filter_by(
                                source_fact_id=fact_id,
                                entity_name=entity_name,
                                entity_type=entity_type,
                            )
                            .first()
                        )

                        if existing:
                            self.logger.debug(
                                f"Entity relationship already exists: {entity_name}"
                            )
                            continue

                        # Create new relationship
                        relationship = KnowledgeRelationship(
                            source_fact_id=fact_id,
                            relationship_type=KnowledgeRelationshipType.MENTIONS_ENTITY.value,
                            entity_name=entity_name,
                            entity_type=entity_type,
                            confidence=confidence,
                        )

                        session.add(relationship)
                        session.commit()

                        stored_entities.append(entity_data)
                        self.logger.info(
                            f"Created entity relationship: {entity_name} ({entity_type})"
                        )

                    except Exception as e:
                        self.logger.error(
                            f"Error storing entity: {e}", exc_info=True
                        )
                        session.rollback()
                        continue

            return stored_entities

        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}", exc_info=True)
            return []

    def _call_llm_for_extraction(
        self, prompt: str, request: "LLMRequest"
    ) -> Optional[str]:
        """
        Call LLM for entity extraction.

        Args:
            prompt: Extraction prompt
            request: LLM request configuration

        Returns:
            LLM response text or None
        """
        try:
            from airunner.components.llm.managers.llm_manager import LLMManager

            llm_manager = LLMManager()

            # Use the LLM API to generate
            response_parts = []

            def callback(response):
                response_parts.append(response.get("message", ""))

            request.messages = [{"role": "user", "content": prompt}]
            request.callback = callback

            llm_manager.generate_text(request)

            return "".join(response_parts)

        except Exception as e:
            self.logger.error(f"Error calling LLM: {e}", exc_info=True)
            return None

    def _parse_extraction_result(self, result: str) -> List[Dict]:
        """
        Parse LLM extraction result.

        Args:
            result: LLM response text

        Returns:
            List of entity dictionaries
        """
        try:
            # Clean up response - extract JSON array
            result = result.strip()

            # Try to find JSON array in response
            start_idx = result.find("[")
            end_idx = result.rfind("]")

            if start_idx == -1 or end_idx == -1:
                self.logger.warning("No JSON array found in response")
                return []

            json_str = result[start_idx : end_idx + 1]
            entities = json.loads(json_str)

            if not isinstance(entities, list):
                self.logger.warning("Parsed result is not a list")
                return []

            return entities

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            self.logger.debug(f"Raw response: {result}")
            return []
        except Exception as e:
            self.logger.error(
                f"Error parsing extraction result: {e}", exc_info=True
            )
            return []
