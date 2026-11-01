"""Subprocess regression tests for the LLM settings dotenv development gate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[2]
_SETTINGS_MODULE = (
    _ROOT / "services/src/airunner_services/llm/llm_settings.py"
)
_IMPORTED_SETTINGS = (
    "AIRUNNER_LLM_AGENT_MAX_FUNCTION_CALLS",
    "AIRUNNER_LLM_AGENT_SUMMARIZE_AFTER_N_TURNS",
    "AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS",
    "AIRUNNER_LLM_OPENROUTER_MODEL",
    "AIRUNNER_LLM_PERFORM_ANALYSIS",
    "AIRUNNER_LLM_PERFORM_CONVERSATION_RAG",
    "AIRUNNER_LLM_PERFORM_CONVERSATION_SUMMARY",
    "AIRUNNER_LLM_PRINT_SYSTEM_PROMPT",
    "AIRUNNER_LLM_UPDATE_USER_DATA_ENABLED",
    "AIRUNNER_LLM_USE_CHATBOT_MOOD",
    "AIRUNNER_LLM_USE_WEATHER_PROMPT",
    "AIRUNNER_LLM_USE_YARN",
)
_IMPORT_SCRIPT = """
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.environ["FAKE_MODULE_ROOT"])
spec = importlib.util.spec_from_file_location(
    "llm_settings_under_test", os.environ["LLM_SETTINGS_MODULE"]
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(json.dumps({"dotenv_value": os.environ.get("DOTENV_FIXTURE_VALUE")}))
"""


def _run_import(tmp_path: Path, *, dev_env: str | None) -> tuple[dict, Path]:
    fake_root = tmp_path / "fake_modules"
    common = fake_root / "airunner_common"
    common.mkdir(parents=True)
    (common / "__init__.py").write_text("", encoding="utf-8")
    (common / "settings.py").write_text(
        "\n".join(f"{name} = False" for name in _IMPORTED_SETTINGS) + "\n",
        encoding="utf-8",
    )

    import_marker = tmp_path / "dotenv-import-marker"
    (fake_root / "dotenv.py").write_text(
        "from pathlib import Path\n"
        "import os\n"
        "marker = Path(os.environ['DOTENV_IMPORT_MARKER'])\n"
        "marker.write_text('imported\\n', encoding='utf-8')\n"
        "def load_dotenv():\n"
        "    with marker.open('a', encoding='utf-8') as stream:\n"
        "        stream.write('load_dotenv\\n')\n"
        "    for line in Path('.env').read_text(encoding='utf-8').splitlines():\n"
        "        key, value = line.split('=', 1)\n"
        "        os.environ[key] = value\n",
        encoding="utf-8",
    )

    (tmp_path / ".env").write_text(
        "DOTENV_FIXTURE_VALUE=controlled-test-value\n", encoding="utf-8"
    )
    env = {
        "HOME": str(tmp_path / "home"),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "FAKE_MODULE_ROOT": str(fake_root),
        "DOTENV_IMPORT_MARKER": str(import_marker),
        "LLM_SETTINGS_MODULE": str(_SETTINGS_MODULE),
    }
    if dev_env is not None:
        env["DEV_ENV"] = dev_env

    result = subprocess.run(
        [sys.executable, "-c", _IMPORT_SCRIPT],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        check=True,
        text=True,
        timeout=15,
    )
    return json.loads(result.stdout), import_marker


def test_unset_dev_env_does_not_import_dotenv_or_load_fixture_file(
    tmp_path: Path,
) -> None:
    result, import_marker = _run_import(tmp_path, dev_env=None)

    assert result == {"dotenv_value": None}
    assert not import_marker.exists()


def test_explicit_dev_env_loads_dotenv_once(tmp_path: Path) -> None:
    result, import_marker = _run_import(tmp_path, dev_env="1")

    assert result == {"dotenv_value": "controlled-test-value"}
    assert import_marker.read_text(encoding="utf-8").splitlines() == [
        "imported",
        "load_dotenv",
    ]
