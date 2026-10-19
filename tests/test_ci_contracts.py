from pathlib import Path


def test_ci_workflow_defines_supported_python_matrix_and_read_only_permissions() -> None:
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml").read_text(
        encoding="utf-8"
    )
    assert 'python-version: ["3.12", "3.13"]' in workflow
    assert "pull_request:" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "pytest -q" in workflow
