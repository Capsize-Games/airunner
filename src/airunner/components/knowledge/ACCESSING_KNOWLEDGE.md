# Accessing Your Knowledge Base

## Quick Guide

Your knowledge base is stored in human-readable JSON at:

```
~/.local/share/airunner/knowledge/user_facts.json
```

## How to View and Edit

### Option 1: Using AI Runner's Document Editor
1. Open AI Runner
2. Navigate to the document editor
3. Open the file: `~/.local/share/airunner/knowledge/user_facts.json`
4. View/edit facts as needed (JSON format with syntax highlighting)
5. Save (or enable autosave)

### Option 2: Using Any Text Editor
```bash
# Open in default editor (Linux)
xdg-open ~/.local/share/airunner/knowledge/user_facts.json

# Or directly with your preferred editor
nano ~/.local/share/airunner/knowledge/user_facts.json
vim ~/.local/share/airunner/knowledge/user_facts.json
code ~/.local/share/airunner/knowledge/user_facts.json
```

### Option 3: File Explorer
1. Navigate to: `~/.local/share/airunner/knowledge/`
2. Double-click `user_facts.json` to open in your default editor

## File Structure

The knowledge base consists of a single JSON file with pretty formatting:

```json
[
  {
    "text": "User is a Python developer",
    "category": "work",
    "confidence": 0.95,
    "source": "conversation",
    "timestamp": "2025-10-18T13:36:53.879946",
    "metadata": {}
  },
  {
    "text": "User is experiencing back pain",
    "category": "health",
    "confidence": 1.0,
    "source": "conversation",
    "timestamp": "2025-10-18T13:56:53.697226",
    "metadata": {}
  }
]
```

**JSON is:**
- ✅ Human-readable (with `indent=2`)
- ✅ Machine-readable
- ✅ Preserves all metadata (confidence, timestamps, categories)
- ✅ Syntax highlighted in the document editor
- ✅ Single source of truth (no sync issues)

## How It Works

1. **Automatic Extraction**: As you chat, the LLM extracts facts about you
2. **Persistent Storage**: Facts are saved to `user_facts.json`
3. **Hybrid Injection**: Core facts (identity, location, preferences) are always loaded, while other facts are retrieved based on query relevance
4. **Token Efficient**: Only relevant facts are injected, saving ~33% tokens vs loading everything

## Knowledge Categories

Facts are organized into 11 categories:

- **Core** (always injected):
  - `identity` - Name, age, gender, etc.
  - `location` - Where you live, work
  - `preferences` - Likes, dislikes, habits

- **RAG** (retrieved on-demand):
  - `health` - Medical conditions, symptoms
  - `work` - Job, company, projects
  - `interests` - Hobbies, topics
  - `skills` - What you can do
  - `goals` - What you want to achieve
  - `history` - Past events, experiences
  - `relationships` - Family, friends
  - `other` - Miscellaneous

## Manual Editing

You can manually add, edit, or remove facts by editing the JSON file:

```json
[
  {
    "text": "User is experiencing back pain",
    "category": "health",
    "confidence": 1.0,
    "source": "conversation",
    "timestamp": "2025-10-18T13:56:53.697226",
    "metadata": {}
  },
  {
    "text": "User is a Python developer",
    "category": "work",
    "confidence": 0.95,
    "source": "manual",
    "timestamp": "2025-10-18T14:00:00.000000",
    "metadata": {}
  }
]
```

Each fact has:
- `text`: The fact statement
- `category`: One of: identity, location, preferences, relationships, work, interests, skills, goals, history, health, other
- `confidence`: 0.0-1.0 (how confident we are in this fact)
- `source`: Where this fact came from (conversation, manual, etc.)
- `timestamp`: When this fact was added/updated
- `metadata`: Optional additional data (empty object by default)

Changes are automatically picked up on the next conversation!

## Privacy Note

All knowledge is stored **locally** on your machine. Nothing is sent to external servers unless you explicitly use API-based LLMs (OpenRouter, OpenAI, etc.) - in which case, the relevant facts are included in the system prompt.

## Configuration

Hybrid mode is **enabled by default**. To adjust settings:

```python
# In llm_settings.py
core_facts_count = 10      # How many core facts to always inject
rag_facts_count = 5        # How many RAG facts to retrieve per query
use_rag_for_facts = True   # Enable hybrid mode (default)
```

See [HYBRID_APPROACH.md](./HYBRID_APPROACH.md) for detailed documentation.
