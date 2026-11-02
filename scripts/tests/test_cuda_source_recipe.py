"""Static checks for the reviewed, offline CUDA source-wheel recipe."""

from pathlib import Path


WORKFLOW = Path(".github/workflows/cuda-build-image-inventory.yml")


def test_cuda_source_recipe_uses_reviewed_python_and_backend_directly():
    text = WORKFLOW.read_text(encoding="utf-8")
    build_job = text.split("  build-llama-cpp-python:", 1)[1]

    assert "if: ${{ false }}" not in build_job
    assert (
        "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
        in build_job
    )
    assert build_job.index("fetch_wheel pip-26.2.2-py3-none-any.whl") < build_job.index(
        "Set up reviewed Python build host"
    )
    assert "python-version: '3.13.5'" in build_job
    assert "PIP_NO_INDEX: '1'" in build_job
    assert "PIP_FIND_LINKS: ${{ runner.temp }}/cuda-wheel/backend" in build_job
    assert "python -m pip --version" in build_job
    assert 'TMPDIR="$tmp" CI=1' in build_job
    assert 'timeout 30s "$CMAKE_EXECUTABLE" -E capabilities' in build_job
    assert "from scikit_build_core.build import build_wheel" in build_job
    assert "filename = build_wheel(" in build_job
    assert "python3 -m pip install" not in build_job
    assert "python -m pip install" not in build_job
    assert "no-build-isolation" not in build_job
    assert build_job.count('config core.hooksPath /dev/null') == 2


def test_cuda_source_recipe_binds_exact_sources_backend_and_offline_flags():
    text = WORKFLOW.read_text(encoding="utf-8")
    build_job = text.split("  build-llama-cpp-python:", 1)[1]

    assert "d2bcbac46605f11d382426dd88d67e8b5c124cd7" in build_job
    assert "f53577432541bb9edc1588c4ef45c66bf07e4468" in build_job
    assert "6f6d6cf600e2e9639fd258ecd11cfc19bd189354b968916a519c6793e7e26237" in build_job
    assert "a00ce642f577bf7f473932318056212bc4f8bfdf53128c78bbd5af0b9b20b189" in build_job
    assert "d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c" in build_job
    assert (
        "pip-26.2.2-py3-none-any.whl"
        in build_job
    )
    assert (
        "fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"
        in build_job
    )
    assert "PIP_FIND_LINKS: ${{ runner.temp }}/cuda-wheel/backend" in build_job
    assert "--network=none" in build_job
    assert "-DGGML_CUDA_CUB_3DOT2=OFF" in build_job
    assert "-DGGML_NATIVE=OFF" in build_job
    assert "-DCMAKE_CUDA_ARCHITECTURES=120a-real" in build_job
    assert "--allow-unsupported-compiler" not in build_job
