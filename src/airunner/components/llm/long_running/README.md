# Long-Running Agent Harness

A sophisticated harness for managing AI agents across multiple sessions on complex, long-running tasks. Inspired by [Anthropic's research](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) on effective harnesses for long-running agents.

## Overview

The Long-Running Agent Harness solves a critical problem: AI agents forget everything between sessions, making them ineffective at complex tasks that span hours or days.

Our solution implements a two-phase architecture:
1. **Initializer Agent**: Sets up projects with comprehensive feature lists
2. **Session Agent**: Makes incremental progress, one feature at a time

### Key Improvements Over Anthropic's Approach

1. **Decision Memory**: Track past decisions and their outcomes to learn from experience
2. **Sub-Agent Delegation**: Route specialized tasks to expert sub-agents (code, research, testing)
3. **Sophisticated State Recovery**: Seamlessly resume interrupted sessions
4. **Resource-Aware Execution**: Optimized for local hardware (16GB VRAM, 32GB RAM)
5. **Integrated Tool System**: Full access to AI Runner's 40+ tools

## Quick Start

```python
from airunner.components.llm.long_running import LongRunningHarness

# Create the harness with your LLM
harness = LongRunningHarness(
    chat_model=your_llm,
    tools=your_tools,
)

# Create and initialize a project
project_id = harness.create_project(
    name="My Chat App",
    description="""
    Build a real-time chat application with:
    - User authentication
    - Public and private channels
    - Direct messaging
    - Message history and search
    - File sharing
    """,
    working_directory="/home/user/projects/chat-app"
)

# Run sessions until complete (or hit limit)
result = harness.run_until_complete(
    project_id,
    max_sessions=50
)

print(f"Status: {result['status']}")
print(f"Sessions run: {result['sessions_run']}")
print(f"Features passing: {result['features_passing']}/{result['total_features']}")
```

## Architecture

### Components

```
long_running/
├── __init__.py           # Package exports
├── data/
│   └── project_state.py  # SQLAlchemy models
├── project_manager.py    # CRUD operations for persistence
├── initializer_agent.py  # Sets up new projects
├── session_agent.py      # Makes incremental progress
├── harness.py           # Main orchestrator
├── sub_agents.py        # Specialized sub-agents
├── tools.py             # LangChain tools for LLM access
└── tests/               # Unit tests
```

### Data Models

- **ProjectState**: Project metadata, status, progress tracking
- **ProjectFeature**: Atomic features with verification steps
- **ProgressEntry**: Log of all work done (like `claude-progress.txt`)
- **SessionState**: Per-session context and working memory
- **DecisionMemory**: Past decisions and outcomes for learning

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    LongRunningHarness                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────────────┐         ┌──────────────────┐         │
│   │ InitializerAgent │──────▶ │  ProjectManager   │         │
│   └──────────────────┘         └──────────────────┘         │
│           │                            │                     │
│           │ Creates project            │ Persists state      │
│           │ with features              │                     │
│           ▼                            ▼                     │
│   ┌──────────────────┐         ┌──────────────────┐         │
│   │  SessionAgent    │──────▶ │   Sub-Agents      │         │
│   └──────────────────┘         │  ┌────────────┐  │         │
│           │                    │  │ CodeAgent  │  │         │
│           │ Incremental        │  │ Research   │  │         │
│           │ progress           │  │ Testing    │  │         │
│           ▼                    │  │ Docs       │  │         │
│   ┌──────────────────┐         │  └────────────┘  │         │
│   │ Progress Logging │         └──────────────────┘         │
│   │ Git Commits      │                                       │
│   │ Decision Memory  │                                       │
│   └──────────────────┘                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## API Reference

### LongRunningHarness

The main orchestrator for long-running projects.

```python
harness = LongRunningHarness(
    chat_model=llm,           # LangChain chat model
    tools=tools,              # List of tools for agents
    project_manager=manager,  # Optional custom ProjectManager
    sub_agents=sub_agents,    # Optional specialized agents
    on_progress=callback,     # Optional progress callback
)
```

#### Methods

**Project Lifecycle**
- `create_project(name, description, working_directory)` - Create and initialize a project
- `run_session(project_id)` - Run a single working session
- `run_until_complete(project_id, max_sessions)` - Run until complete or limit
- `resume_project(project_id)` - Resume a paused project
- `pause_project(project_id)` - Pause a project
- `abandon_project(project_id, reason)` - Abandon a project

**Status & Reporting**
- `get_project_status(project_id)` - Get current status and progress
- `get_decision_history(project_id)` - Get past decisions and outcomes
- `export_project_report(project_id)` - Export comprehensive report

**Recovery**
- `revert_to_checkpoint(project_id, commit_hash)` - Revert to git commit
- `add_decision_feedback(decision_id, outcome, score, lesson)` - Add feedback

### ProjectManager

Manages persistence for projects, features, sessions, and decisions.

```python
manager = ProjectManager()

# Create project
project = manager.create_project(
    name="My Project",
    description="Description",
    working_directory="/path/to/project",
    init_git=True
)

# Add features
feature = manager.add_feature(
    project_id=project.id,
    name="User Login",
    description="Users can log in with email and password",
    category=FeatureCategory.FUNCTIONAL,
    priority=9,
    verification_steps=["Open login page", "Enter credentials", "See dashboard"]
)

# Update feature status
manager.update_feature_status(feature.id, FeatureStatus.PASSING)

# Log progress
manager.log_progress(
    project_id=project.id,
    action="Implemented login",
    outcome="Login works, ready for testing",
    git_commit=True
)

# Record decisions
manager.record_decision(
    project_id=project.id,
    context="Needed authentication method",
    decision="Using JWT tokens",
    reasoning="Stateless, secure, industry standard"
)
```

### Sub-Agents

Specialized agents for different types of work:

```python
from airunner.components.llm.long_running.sub_agents import create_sub_agents

# Create all sub-agents
sub_agents = create_sub_agents(chat_model)

# Or create individually
from airunner.components.llm.long_running import (
    CodeSubAgent,
    ResearchSubAgent,
    TestingSubAgent,
    DocumentationSubAgent,
)

code_agent = CodeSubAgent(chat_model)
research_agent = ResearchSubAgent(chat_model)
```

## Feature Categories

Features are categorized to enable intelligent routing to sub-agents:

| Category | Description | Sub-Agent |
|----------|-------------|-----------|
| `functional` | Core functionality | CodeSubAgent |
| `ui` | User interface | CodeSubAgent |
| `integration` | External integrations | ResearchSubAgent |
| `testing` | Test coverage | TestingSubAgent |
| `documentation` | Docs and comments | DocumentationSubAgent |
| `performance` | Optimization | CodeSubAgent |
| `security` | Security features | CodeSubAgent |

## Feature Status Lifecycle

```
NOT_STARTED ─────▶ IN_PROGRESS ─────▶ PASSING
                        │
                        ▼
                    FAILING (retry)
                        │
                        ▼
                    BLOCKED (dependency issue)
```

## Decision Memory

The Decision Memory system tracks past decisions and their outcomes:

```python
# Record a decision
decision = manager.record_decision(
    project_id=project.id,
    context="Need to choose between REST and GraphQL",
    decision="Using REST API",
    reasoning="Simpler for this use case, team familiarity",
    tags=["architecture", "api"]
)

# Later, record the outcome
manager.update_decision_outcome(
    decision_id=decision.id,
    outcome=DecisionOutcome.SUCCESS,
    score=0.8,
    lesson="REST worked well, but GraphQL would help with complex queries"
)
```

Decisions are retrieved during planning phases to inform future choices.

## LangChain Tools

The module provides tools for LLM interaction:

```python
from airunner.components.llm.long_running import LONG_RUNNING_TOOLS

# Available tools:
# - create_long_running_project
# - get_project_status
# - list_project_features
# - get_project_progress_log
# - list_long_running_projects
# - add_project_feature
# - update_feature_status
# - log_project_progress
# - get_next_feature_to_work_on
```

## Best Practices

### 1. Feature Decomposition
- Break down into atomic, testable features
- 20-200 features per project is typical
- Each feature should be independently verifiable

### 2. Verification Steps
- Provide clear, concrete verification steps
- Steps should be executable (not just "it works")
- Include both happy path and edge cases

### 3. Progress Logging
- Log frequently to preserve context
- Commit to git after each feature
- Include files changed for traceability

### 4. Session Management
- Work on ONE feature per session
- Don't declare project complete prematurely
- Leave clean state for next session

### 5. Decision Memory
- Record significant decisions
- Update outcomes when known
- Learn from failures

## Testing

Run the test suite:

```bash
python src/airunner/bin/run_tests.py --unit --component llm
```

## Future Enhancements

- [ ] Parallel feature implementation (independent features)
- [ ] Automated test generation
- [ ] Browser automation integration (Puppeteer/Playwright)
- [ ] Multi-model support (different models for different tasks)
- [ ] Visual progress dashboard
- [ ] Collaborative editing (human + AI)

## References

- [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
