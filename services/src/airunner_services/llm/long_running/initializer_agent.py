"""Thin facade for the long-running initializer agent."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.llm.long_running.initializer_agent_analysis import (
    analyze_requirements,
)
from airunner_services.llm.long_running.initializer_agent_generation import (
    extract_json_from_response,
    generate_features,
)
from airunner_services.llm.long_running.initializer_agent_graph import (
    build_initializer_graph,
)
from airunner_services.llm.long_running.initializer_agent_project import (
    create_project,
)
from airunner_services.llm.long_running.initializer_agent_run import (
    finalize,
    get_feature_list_prompt,
    initialize_project,
)
from airunner_services.llm.long_running.initializer_agent_state import (
    INITIALIZER_SYSTEM_PROMPT,
    InitializerWorkflowState,
)
from airunner_services.llm.long_running.project_manager import ProjectManager
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class InitializerAgent:
    """Agent that initializes long-running projects.

    Takes user requirements and creates:
    1. Project database entry
    2. Comprehensive feature list
    3. Git repository
    4. Initial progress log

    Example:
        ```python
        agent = InitializerAgent(chat_model)
        result = agent.initialize_project(
            name="My Web App",
            description="Build a chat application with user auth and real-time messaging",
            working_directory="/home/user/projects/my-web-app"
        )
        print(f"Created project {result['project_id']} with {result['feature_count']} features")
        ```
    """

    def __init__(
        self,
        chat_model: Any,
        project_manager: Optional[ProjectManager] = None,
    ) -> None:
        """Initialize the initializer agent."""
        self._chat_model = chat_model
        self._project_manager = project_manager or ProjectManager()
        self._graph = build_initializer_graph(self)
        logger.info("InitializerAgent initialized")

    _analyze_requirements = analyze_requirements
    _generate_features = generate_features
    _extract_json_from_response = staticmethod(extract_json_from_response)
    _create_project = create_project
    _finalize = finalize
    initialize_project = initialize_project
    get_feature_list_prompt = staticmethod(get_feature_list_prompt)
