# Knowledge Management System

## Overview

The knowledge management system provides persistent, continuously-growing memory beyond conversation history. It separates **style** (learned via LoRA) from **facts** (stored in RAG-indexed knowledge bases).

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Tier 1: Working Memory (RAM)            │
│  - Current conversation context                 │
│  - Recently accessed facts (LRU cache)          │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│      Tier 2: Short-Term Memory (Database)       │
│  - Recent conversations (7-30 days)             │
│  - User session data                            │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│       Tier 3: Long-Term Memory (RAG+Files)      │
│  - User knowledge base (facts about user)       │
│  - Document library (books, articles)           │
│  - Web knowledge cache                          │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│     Tier 4: Foundational Memory (LoRA)          │
│  - Writing styles                               │
│  - Response patterns                            │
│  - Domain vocabularies                          │
└─────────────────────────────────────────────────┘
```

## Components

### UserKnowledgeManager
**Purpose:** Continuously extract and store facts about the user from conversations.

**Features:**
- Automatic fact extraction from conversations
- **Automatic correction detection** (user says "actually", "no", "wrong", etc.)
- **CRUD operations** (Create, Read, Update, Delete facts)
- Human-readable JSON storage (`~/.local/share/airunner/knowledge/user_facts.json`)
- Fact consolidation (merges duplicates, updates confidence)
- Category-based organization (identity, preferences, work, etc.)
- Manual editing support (edit JSON directly)

**Usage:**
```python
from airunner.components.knowledge.user_knowledge_manager import UserKnowledgeManager

km = UserKnowledgeManager()

# Extract facts from conversation (handles corrections automatically)
facts = km.extract_facts_from_text(
    user_message="My name is John and I live in Seattle",
    bot_response="Nice to meet you, John!",
    llm_callable=lambda prompt, **kwargs: llm.generate(prompt)
)

# Add to knowledge base
km.add_facts(facts)

# Update a fact
km.replace_fact("User is 30 years old", "User is 31 years old")

# Delete a fact
km.delete_fact("User lives in Seattle")

# Get context for next conversation
context = km.get_context_for_conversation(max_facts=20)
```

**See also:**
- [CORRECTION_SYSTEM.md](./CORRECTION_SYSTEM.md) - Complete CRUD operations guide
- [HYBRID_APPROACH.md](./HYBRID_APPROACH.md) - Token-efficient fact injection
- [ACCESSING_KNOWLEDGE.md](./ACCESSING_KNOWLEDGE.md) - Manual editing guide

### Data Models

**Fact:** Individual piece of knowledge with confidence scoring
```python
@dataclass
class Fact:
    text: str
    category: FactCategory  
    confidence: float  # 0.0-1.0
    source: str  # "conversation", "web", "document"
    timestamp: datetime
    metadata: dict
```

**FactCategory:** Categorization for organization
- IDENTITY: Name, age, gender
- LOCATION: Where user lives/works
- PREFERENCES: Likes, dislikes, habits
- RELATIONSHIPS: Family, friends
- WORK: Job, company, projects
- INTERESTS: Hobbies, topics
- SKILLS: Capabilities
- GOALS: Aspirations
- HISTORY: Past events
- OTHER: Miscellaneous

## Integration with BaseAgent

The knowledge manager integrates with the conversation system to automatically extract and utilize user knowledge:

```python
# In BaseAgent.chat()
def chat(self, message: str, **kwargs):
    # 1. Load user knowledge into context
    user_context = self.knowledge_manager.get_context_for_conversation()
    kwargs['extra_context'] = user_context
    
    # 2. Perform normal chat
    response = self._perform_tool_call(self.action, **kwargs)
    
    # 3. Extract new facts (async, non-blocking)
    if self.auto_extract_knowledge:
        self._extract_and_store_knowledge(message, response.response)
    
    return response
```

## LoRA vs RAG: When to Use What

### Use LoRA For:
✅ Writing style (mimicking authors)
✅ Response tone/personality
✅ Domain vocabulary
✅ Linguistic patterns
✅ Response format preferences

### Use RAG For:
✅ User facts and preferences
✅ Document content
✅ Web knowledge
✅ Conversation history
✅ Any factual information

### Why Not LoRA for Facts?
❌ Low-rank adapters can't memorize content
❌ Requires 100+ epochs for any memorization
❌ Unreliable (may hallucinate variations)
❌ Catastrophic forgetting with multiple topics
❌ Extremely compute-intensive

### Why RAG is Better for Facts
✅ 100% accurate retrieval
✅ Instant updates (no retraining)
✅ Human-readable storage
✅ Efficient search with embeddings
✅ Transparent and debuggable

## File Locations

```
~/.local/share/airunner/
├── knowledge/
│   ├── user_facts.json         # User knowledge (human-readable JSON)
│   └── document_summaries/     # Document summaries (future)
└── text/
    └── models/
        └── llm/
            └── adapters/       # LoRA style adapters
```

## Viewing and Editing Knowledge

The knowledge system stores facts in a human-readable JSON file at `~/.local/share/airunner/knowledge/user_facts.json`.

**To view or edit your knowledge:**
1. Navigate to the knowledge directory in your file explorer
2. Open `user_facts.json` in the AI Runner document editor (or any text editor)
3. Edit facts manually as needed (JSON format with `indent=2` for readability)
4. Changes are automatically picked up on next conversation

**Quick access:**
```bash
# Open knowledge directory
xdg-open ~/.local/share/airunner/knowledge/

# View current facts
cat ~/.local/share/airunner/knowledge/user_facts.json
```

The document editor widget supports JSON syntax highlighting, line numbers, and autosave - perfect for managing your knowledge base!

## Future Enhancements

1. **Semantic Fact Matching:** Use embeddings to detect similar facts
2. **Knowledge Graph:** Connect related facts with relationships
3. **Document Summarization:** Multi-level summaries for documents
4. **Auto-Learning Worker:** Background task for knowledge consolidation
5. **Web Knowledge Cache:** Store and index web-scraped content
6. **Fact Verification:** Cross-reference facts for consistency
7. **Export/Import:** Share knowledge bases between instances

## Development Guidelines

- Keep knowledge managers focused and single-purpose
- Use dataclasses for clean data models
- Maintain human-readable formats (markdown)
- Log all knowledge operations for transparency
- Never block conversation with knowledge extraction
- Prefer async operations for heavy processing
