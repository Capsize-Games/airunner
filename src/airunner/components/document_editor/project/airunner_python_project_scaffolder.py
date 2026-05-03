"""Scaffold Python-first project templates into AIRunner workspaces."""

import re

from airunner.components.document_editor.project.airunner_project_service import (
    AirunnerProjectService,
)


class AirunnerPythonProjectScaffolder:
    """Write a minimal Python project layout for a coding workspace."""

    bootstrap_profile = "python-package"

    def __init__(self, project_service: AirunnerProjectService):
        self.project_service = project_service

    def scaffold(
        self,
        project_name: str,
        *,
        package_name: str | None = None,
    ) -> list[str]:
        """Create a src-layout Python package scaffold."""
        package = self._package_name(package_name or project_name)
        files = {
            ".gitignore": self._gitignore_content(),
            "README.md": self._readme_content(project_name),
            "pyproject.toml": self._pyproject_content(project_name, package),
            f"src/{package}/__init__.py": self._init_content(project_name),
            f"src/{package}/__main__.py": self._main_content(package),
            f"tests/test_{package}.py": self._test_content(package),
        }
        for rel_path, content in files.items():
            self.project_service.write_file(
                rel_path,
                content,
                backup=False,
            )
        return sorted(files.keys())

    def _package_name(self, value: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")
        return (normalized or "airunner_project").lower()

    def _gitignore_content(self) -> str:
        return "__pycache__/\n*.pyc\n.venv/\n.pytest_cache/\n"

    def _readme_content(self, project_name: str) -> str:
        return (
            f"# {project_name}\n\n"
            "Bootstrapped by AIRunner as a Python-first coding workspace.\n"
        )

    def _pyproject_content(
        self,
        project_name: str,
        package_name: str,
    ) -> str:
        project_slug = project_name.lower().replace(" ", "-")
        return (
            "[build-system]\n"
            'requires = ["setuptools>=69"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            "[project]\n"
            f'name = "{project_slug}"\n'
            'version = "0.1.0"\n'
            f'description = "{project_name}"\n'
            'readme = "README.md"\n'
            'requires-python = ">=3.11"\n'
            'dependencies = []\n\n'
            "[tool.setuptools.packages.find]\n"
            'where = ["src"]\n\n'
            "[tool.pytest.ini_options]\n"
            'testpaths = ["tests"]\n\n'
            "[tool.ruff]\n"
            'line-length = 80\n\n'
            "[tool.airunner]\n"
            f'package_name = "{package_name}"\n'
            f'bootstrap_profile = "{self.bootstrap_profile}"\n'
        )

    def _init_content(self, project_name: str) -> str:
        return (
            f'"""{project_name} package."""\n\n'
            '__all__ = ["main"]\n'
        )

    def _main_content(self, package_name: str) -> str:
        return (
            '"""Command-line entry point for the bootstrapped package."""\n\n'
            "def main() -> None:\n"
            f'    print("{package_name} is ready")\n\n'
            'if __name__ == "__main__":\n'
            '    main()\n'
        )

    def _test_content(self, package_name: str) -> str:
        return (
            f'"""Smoke tests for {package_name}."""\n\n'
            f'from {package_name} import __all__\n\n'
            'def test_package_exports_main() -> None:\n'
            '    assert "main" in __all__\n'
        )