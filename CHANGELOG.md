# Changelog

All notable changes to AI Runner will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Knowledge system migration CLI command (`airunner-migrate-knowledge`) for migrating from JSON to database storage
- Automatic one-time knowledge migration on application startup
- Database-backed knowledge system with `KnowledgeMemoryManager` for improved performance and reliability
- Service settings panel for configuring background service and HTTP server
- Provider/model selection UI with VSCode-style searchable dropdowns
- Model management dialog for downloading and managing LLM models
- Workflow template system with predefined templates for common LangGraph patterns
- Nodegraph LLM tools for workflow management (create, update, delete, list, export, import)

### Changed
- HTTP server configuration moved to database settings (host, port, LNA/CORS toggle)
- Knowledge facts now stored in SQLite database instead of JSON files

### Deprecated
- **UserKnowledgeManager**: JSON-based knowledge system is deprecated and will be removed in version 3.0.0
  - **Migration Path**: Run `airunner-migrate-knowledge` to migrate your existing knowledge data
  - **Replacement**: Use `KnowledgeMemoryManager` for new code
  - **Timeline**: Deprecation warnings added in 2.0.0, removal planned for 3.0.0 (approximately 3 months)
  - **Why**: Database-backed system provides better performance, reliability, and scalability
  - **Impact**: Existing JSON files will continue to work but will show deprecation warnings

### Removed
- None

### Fixed
- None

### Security
- None

## Migration Guide: UserKnowledgeManager → KnowledgeMemoryManager

If you are using `UserKnowledgeManager` in your code, please migrate to `KnowledgeMemoryManager`:

**Old Code:**
```python
from airunner.components.knowledge.user_knowledge_manager import UserKnowledgeManager

knowledge = UserKnowledgeManager()
facts = knowledge.get_all_facts()
```

**New Code:**
```python
from airunner.components.knowledge.knowledge_memory_manager import KnowledgeMemoryManager

knowledge = KnowledgeMemoryManager(embeddings=your_embeddings)  # Optional embeddings
facts = knowledge.get_all_facts(enabled_only=True)
```

**Migrating Your Data:**
1. Run the migration command: `airunner-migrate-knowledge`
2. Or let it run automatically on next app launch
3. Verify your facts in the new system
4. Update your code to use `KnowledgeMemoryManager`

For more details, see the [Knowledge System Documentation](https://github.com/Capsize-Games/airunner/wiki/Knowledge-System).
