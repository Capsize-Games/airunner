"""Initializer Agent for long-running projects.

The Initializer Agent is responsible for setting up a new project:
1. Expanding user requirements into a comprehensive feature list
2. Setting up project directory structure
3. Creating initial configuration files
4. Initializing git repository
5. Writing first progress log entry

This follows Anthropic's pattern but adds:
- More intelligent feature decomposition
- Category-based feature organization
- Dependency detection between features
- Initial decision memory seeding
"""

from typing import Any, Optional, List, Dict, Annotated
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import START, END, StateGraph, add_messages

from airunner.components.llm.long_running.data.project_state import (
    ProjectStatus,
    FeatureCategory,
)
from airunner.components.llm.long_running.project_manager import ProjectManager
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# System prompt for the initializer agent
INITIALIZER_SYSTEM_PROMPT = """You are a project initialization specialist. Your task is to analyze a user's project requirements and create a comprehensive, structured feature list.

CRITICAL RULES:
1. Break down the project into ATOMIC features - each should be independently implementable and testable
2. Aim for 20-200 features depending on project complexity
3. Each feature must have clear verification steps
4. Identify dependencies between features
5. Categorize features appropriately
6. Features should be prioritized (1-10, higher = more important)
7. Start with foundational features before UI polish

OUTPUT FORMAT:
You must output a JSON array of features. Each feature:
{
    "name": "Short descriptive name",
    "description": "Detailed description of what this feature does",
    "category": "functional|ui|integration|testing|documentation|performance|security",
    "verification_steps": ["Step 1", "Step 2", "Step 3"],
    "priority": 1-10,
    "depends_on_names": ["Feature Name 1", "Feature Name 2"]  // Names of features this depends on
}

CATEGORIES:
- functional: Core application functionality
- ui: User interface elements
- integration: External service integrations
- testing: Test coverage and validation
- documentation: Documentation and comments
- performance: Optimization and efficiency
- security: Security features and validation

EXAMPLE for a "Todo App":
[
    {
        "name": "Data model for tasks",
        "description": "Create SQLite database schema for storing tasks with id, title, description, completed status, created_at, updated_at fields",
        "category": "functional",
        "verification_steps": ["Database file created", "Schema matches spec", "Can insert/query tasks"],
        "priority": 10,
        "depends_on_names": []
    },
    {
        "name": "Create task API endpoint",
        "description": "POST /tasks endpoint that accepts JSON body with title and description, creates task in database",
        "category": "functional",
        "verification_steps": ["POST creates task", "Returns 201 with task JSON", "Task persisted in DB"],
        "priority": 9,
        "depends_on_names": ["Data model for tasks"]
    }
]

Be thorough but practical. Focus on features that matter for a working application."""


class InitializerState(TypedDict):
    """State schema for Initializer Agent.

    Attributes:
        messages: Conversation messages
        project_name: Name of the project
        project_description: User's requirements
        features_json: Generated feature list as JSON string
        project_id: Created project ID
        error: Any error message
    """

    messages: Annotated[list[BaseMessage], add_messages]
    project_name: str
    project_description: str
    working_directory: Optional[str]
    features_json: Optional[str]
    project_id: Optional[int]
    error: Optional[str]


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
    ):
        """Initialize the Initializer Agent.

        Args:
            chat_model: LangChain chat model
            project_manager: ProjectManager instance (creates new if None)
        """
        self._chat_model = chat_model
        self._project_manager = project_manager or ProjectManager()
        self._graph = self._build_graph()

        logger.info("InitializerAgent initialized")

    def _build_graph(self) -> Any:
        """Build the LangGraph workflow for initialization."""
        workflow = StateGraph(InitializerState)

        # Add nodes
        workflow.add_node("analyze_requirements", self._analyze_requirements)
        workflow.add_node("generate_features", self._generate_features)
        workflow.add_node("create_project", self._create_project)
        workflow.add_node("finalize", self._finalize)

        # Add edges
        workflow.add_edge(START, "analyze_requirements")
        workflow.add_edge("analyze_requirements", "generate_features")
        workflow.add_edge("generate_features", "create_project")
        workflow.add_edge("create_project", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    def _analyze_requirements(self, state: InitializerState) -> dict:
        """Analyze user requirements and prepare for feature generation.

        Args:
            state: Current state

        Returns:
            Updated state with analysis message
        """
        logger.info(f"Analyzing requirements for project: {state['project_name']}")

        # Create the prompt for analysis
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", INITIALIZER_SYSTEM_PROMPT),
                (
                    "human",
                    """Analyze these project requirements and prepare a comprehensive feature list.

PROJECT NAME: {project_name}

REQUIREMENTS:
{project_description}

First, identify:
1. Core functionality needed
2. User-facing features
3. Backend/infrastructure needs
4. Testing requirements
5. Potential integrations

Then generate the full feature list in JSON format.""",
                ),
            ]
        )

        # Format the prompt
        formatted = prompt.format_messages(
            project_name=state["project_name"],
            project_description=state["project_description"],
        )

        return {
            "messages": formatted,
        }

    def _generate_features(self, state: InitializerState) -> dict:
        """Generate the feature list using LLM.

        Args:
            state: Current state

        Returns:
            Updated state with features_json
        """
        logger.info("Generating feature list with LLM")

        try:
            # Get LLM response
            response = self._chat_model.invoke(state["messages"])

            # Extract JSON from response
            content = response.content
            features_json = self._extract_json_from_response(content)

            if not features_json:
                return {
                    "error": "Failed to extract feature list from LLM response",
                    "messages": [response],
                }

            return {
                "features_json": features_json,
                "messages": [response],
            }

        except Exception as e:
            logger.error(f"Feature generation failed: {e}")
            return {"error": str(e)}

    def _extract_json_from_response(self, content: str) -> Optional[str]:
        """Extract JSON array from LLM response.

        Args:
            content: LLM response content

        Returns:
            JSON string or None
        """
        import json
        import re

        # Try to find JSON array in response
        # Look for content between [ and ]
        json_match = re.search(r"\[[\s\S]*\]", content)
        if json_match:
            try:
                # Validate it's valid JSON
                json.loads(json_match.group())
                return json_match.group()
            except json.JSONDecodeError:
                pass

        # Try parsing the whole content as JSON
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            pass

        return None

    def _create_project(self, state: InitializerState) -> dict:
        """Create the project and features in database.

        Args:
            state: Current state

        Returns:
            Updated state with project_id
        """
        logger.info(f"Creating project: {state['project_name']}")

        if state.get("error"):
            return {}

        try:
            import json

            # Create the project
            project = self._project_manager.create_project(
                name=state["project_name"],
                description=state["project_description"],
                working_directory=state.get("working_directory"),
                system_prompt=INITIALIZER_SYSTEM_PROMPT,
                init_git=True,
            )

            # Parse and create features
            features_data = json.loads(state["features_json"])

            # First pass: create all features without dependencies
            feature_name_to_id = {}
            for f in features_data:
                feature = self._project_manager.add_feature(
                    project_id=project.id,
                    name=f["name"],
                    description=f.get("description", ""),
                    category=FeatureCategory(f.get("category", "functional")),
                    verification_steps=f.get("verification_steps", []),
                    priority=f.get("priority", 5),
                    depends_on=[],  # Will update in second pass
                )
                feature_name_to_id[f["name"]] = feature.id

            # Second pass: update dependencies
            for f in features_data:
                depends_on_names = f.get("depends_on_names", [])
                if depends_on_names:
                    feature_id = feature_name_to_id.get(f["name"])
                    if feature_id:
                        depends_on_ids = [
                            feature_name_to_id[name]
                            for name in depends_on_names
                            if name in feature_name_to_id
                        ]
                        if depends_on_ids:
                            # Update feature with dependencies
                            feature = self._project_manager.get_feature(feature_id)
                            if feature:
                                feature.depends_on = depends_on_ids

            # Update project status
            self._project_manager.update_project_status(
                project.id, ProjectStatus.ACTIVE
            )

            # Log initial progress
            self._project_manager.log_progress(
                project_id=project.id,
                action="Project initialized",
                outcome=f"Created project with {len(features_data)} features",
                git_commit=True,
            )

            return {
                "project_id": project.id,
            }

        except Exception as e:
            logger.error(f"Project creation failed: {e}")
            return {"error": str(e)}

    def _finalize(self, state: InitializerState) -> dict:
        """Finalize initialization and return results.

        Args:
            state: Current state

        Returns:
            Final state
        """
        if state.get("error"):
            logger.error(f"Initialization failed: {state['error']}")
        else:
            logger.info(
                f"Project {state.get('project_id')} initialized successfully"
            )

        return {}

    def initialize_project(
        self,
        name: str,
        description: str,
        working_directory: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initialize a new long-running project.

        Args:
            name: Project name
            description: User's requirements/description
            working_directory: Optional directory for project files

        Returns:
            Dict with project_id, feature_count, or error
        """
        logger.info(f"Starting project initialization: {name}")

        initial_state: InitializerState = {
            "messages": [],
            "project_name": name,
            "project_description": description,
            "working_directory": working_directory,
            "features_json": None,
            "project_id": None,
            "error": None,
        }

        result = self._graph.invoke(initial_state)

        if result.get("error"):
            return {"error": result["error"]}

        # Get feature count
        project = self._project_manager.get_project(result["project_id"])
        feature_count = project.total_features if project else 0

        return {
            "project_id": result["project_id"],
            "feature_count": feature_count,
            "project_name": name,
            "status": "initialized",
        }

    def get_feature_list_prompt(self, description: str) -> str:
        """Get a prompt for generating feature list (for testing/debugging).

        Args:
            description: Project description

        Returns:
            Formatted prompt string
        """
        return f"""{INITIALIZER_SYSTEM_PROMPT}

PROJECT REQUIREMENTS:
{description}

Generate the comprehensive feature list in JSON format."""
