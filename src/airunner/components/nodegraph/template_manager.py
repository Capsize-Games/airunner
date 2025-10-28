"""
Workflow template management system.

Manages loading, saving, categorizing, and discovering workflow templates.
"""

import json
import os
from typing import List, Optional, Dict, Any
from pathlib import Path

from airunner.utils.application.get_logger import get_logger
from airunner.settings import AIRUNNER_LOG_LEVEL


class WorkflowTemplate:
    """Represents a workflow template."""

    def __init__(self, data: Dict[str, Any], file_path: Optional[str] = None):
        """Initialize template from dictionary.

        Args:
            data: Template data dictionary
            file_path: Optional path to template file
        """
        self.name = data.get("name", "Untitled Template")
        self.description = data.get("description", "")
        self.category = data.get("category", "general")
        self.tags = data.get("tags", [])
        self.author = data.get("author", "Unknown")
        self.version = data.get("version", "1.0")
        self.variables = data.get("variables", {})
        self.nodes = data.get("nodes", [])
        self.connections = data.get("connections", [])
        self.file_path = file_path

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary.

        Returns:
            Template data as dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "author": self.author,
            "version": self.version,
            "variables": self.variables,
            "nodes": self.nodes,
            "connections": self.connections,
        }

    def __repr__(self):
        return f"<WorkflowTemplate(name='{self.name}', category='{self.category}')>"


class TemplateManager:
    """Manages workflow templates."""

    def __init__(self, template_dir: Optional[str] = None):
        """Initialize template manager.

        Args:
            template_dir: Directory containing template files.
                         Defaults to package templates directory.
        """
        self.logger = get_logger("TemplateManager", AIRUNNER_LOG_LEVEL)

        if template_dir is None:
            # Use package templates directory
            package_dir = Path(__file__).parent
            template_dir = package_dir / "templates"

        self.template_dir = Path(template_dir)
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.categories: Dict[str, List[WorkflowTemplate]] = {}

        # Create template directory if it doesn't exist
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Load templates
        self.reload()

    def reload(self):
        """Reload all templates from disk."""
        self.templates = {}
        self.categories = {}

        if not self.template_dir.exists():
            self.logger.warning(
                f"Template directory does not exist: {self.template_dir}"
            )
            return

        # Load all JSON files in template directory
        for file_path in self.template_dir.glob("*.json"):
            try:
                template = self.load_template_file(file_path)
                if template:
                    self.templates[template.name] = template

                    # Add to category index
                    category = template.category
                    if category not in self.categories:
                        self.categories[category] = []
                    self.categories[category].append(template)

                    self.logger.debug(f"Loaded template: {template.name}")

            except Exception as e:
                self.logger.error(f"Error loading template {file_path}: {e}")

        self.logger.info(
            f"Loaded {len(self.templates)} templates from {self.template_dir}"
        )

    def load_template_file(
        self, file_path: Path
    ) -> Optional[WorkflowTemplate]:
        """Load a single template file.

        Args:
            file_path: Path to template JSON file

        Returns:
            WorkflowTemplate instance or None on error
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return WorkflowTemplate(data, str(file_path))

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in template {file_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading template {file_path}: {e}")
            return None

    def save_template(
        self, template: WorkflowTemplate, file_name: Optional[str] = None
    ) -> bool:
        """Save template to disk.

        Args:
            template: Template to save
            file_name: Optional file name (defaults to sanitized template name)

        Returns:
            True if saved successfully
        """
        try:
            if file_name is None:
                # Sanitize template name for file name
                file_name = (
                    template.name.lower().replace(" ", "_").replace("/", "_")
                    + ".json"
                )

            file_path = self.template_dir / file_name

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(template.to_dict(), f, indent=2)

            template.file_path = str(file_path)
            self.templates[template.name] = template

            # Update category index
            category = template.category
            if category not in self.categories:
                self.categories[category] = []
            if template not in self.categories[category]:
                self.categories[category].append(template)

            self.logger.info(f"Saved template: {template.name}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving template: {e}")
            return False

    def get_template(self, name: str) -> Optional[WorkflowTemplate]:
        """Get template by name.

        Args:
            name: Template name

        Returns:
            WorkflowTemplate instance or None if not found
        """
        return self.templates.get(name)

    def list_templates(self) -> List[WorkflowTemplate]:
        """List all templates.

        Returns:
            List of all templates
        """
        return list(self.templates.values())

    def list_by_category(self, category: str) -> List[WorkflowTemplate]:
        """List templates in a specific category.

        Args:
            category: Category name

        Returns:
            List of templates in category
        """
        return self.categories.get(category, [])

    def list_categories(self) -> List[str]:
        """List all categories.

        Returns:
            List of category names
        """
        return list(self.categories.keys())

    def search_templates(
        self, query: str, category: Optional[str] = None
    ) -> List[WorkflowTemplate]:
        """Search templates by name, description, or tags.

        Args:
            query: Search query string
            category: Optional category filter

        Returns:
            List of matching templates
        """
        query_lower = query.lower()
        results = []

        templates = (
            self.list_by_category(category)
            if category
            else self.list_templates()
        )

        for template in templates:
            # Search in name
            if query_lower in template.name.lower():
                results.append(template)
                continue

            # Search in description
            if query_lower in template.description.lower():
                results.append(template)
                continue

            # Search in tags
            if any(query_lower in tag.lower() for tag in template.tags):
                results.append(template)
                continue

        return results

    def delete_template(self, name: str) -> bool:
        """Delete a template.

        Args:
            name: Template name

        Returns:
            True if deleted successfully
        """
        template = self.templates.get(name)
        if not template:
            self.logger.warning(f"Template not found: {name}")
            return False

        try:
            # Delete file if it exists
            if template.file_path and os.path.exists(template.file_path):
                os.remove(template.file_path)

            # Remove from memory
            del self.templates[name]

            # Remove from category index
            category = template.category
            if category in self.categories:
                self.categories[category].remove(template)

            self.logger.info(f"Deleted template: {name}")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting template {name}: {e}")
            return False

    def create_from_template(
        self,
        template_name: str,
        workflow_name: str,
        variables: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """Create a workflow from a template.

        Args:
            template_name: Name of template to use
            workflow_name: Name for new workflow
            variables: Optional variable overrides

        Returns:
            Workflow data dictionary ready for create_workflow tool
        """
        template = self.get_template(template_name)
        if not template:
            self.logger.error(f"Template not found: {template_name}")
            return None

        # Merge variables (template defaults + overrides)
        merged_vars = {**template.variables, **(variables or {})}

        # Substitute variables in nodes and connections
        nodes = self._substitute_variables(template.nodes, merged_vars)
        connections = self._substitute_variables(
            template.connections, merged_vars
        )

        return {
            "name": workflow_name,
            "description": f"Created from template: {template.name}",
            "nodes": nodes,
            "connections": connections,
            "variables": merged_vars,
        }

    def _substitute_variables(self, data: Any, variables: Dict) -> Any:
        """Recursively substitute {{variable}} placeholders.

        Args:
            data: Data structure (dict, list, str, etc.)
            variables: Variable substitutions

        Returns:
            Data with variables substituted
        """
        if isinstance(data, dict):
            return {
                k: self._substitute_variables(v, variables)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [
                self._substitute_variables(item, variables) for item in data
            ]
        elif isinstance(data, str):
            # Replace {{var_name}} with variable value
            result = data
            for var_name, var_value in variables.items():
                placeholder = f"{{{{{var_name}}}}}"
                if placeholder in result:
                    result = result.replace(placeholder, str(var_value))
            return result
        else:
            return data


# Global template manager instance
_template_manager = None


def get_template_manager() -> TemplateManager:
    """Get global template manager instance.

    Returns:
        TemplateManager singleton
    """
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager
