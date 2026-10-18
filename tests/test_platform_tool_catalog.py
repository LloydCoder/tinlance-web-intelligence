import json
from pathlib import Path

from tinlance_web_intelligence.integrations.agent_platform.tool_catalog import TWI_PLATFORM_TOOLS


def test_platform_tool_catalog_has_unique_names_and_operations() -> None:
    names = [tool.name for tool in TWI_PLATFORM_TOOLS]
    operations = [tool.operation for tool in TWI_PLATFORM_TOOLS]
    assert len(names) == len(set(names))
    assert len(operations) == len(set(operations))
    assert set(names) == {
        "twi_search",
        "twi_fetch",
        "twi_browser_navigate",
        "twi_job_read",
        "twi_job_cancel",
        "twi_research_verify",
        "twi_world_intelligence_export",
        "twi_world_intelligence_export_status",
    }


def test_json_tool_manifests_match_python_catalog() -> None:
    root = Path("schemas/mcp-tools")
    manifests = [
        json.loads(path.read_text(encoding="utf-8")) for path in root.glob("*.json")
    ]
    by_name = {tool.name: tool for tool in TWI_PLATFORM_TOOLS}
    assert {manifest["name"] for manifest in manifests} == set(by_name)
    for manifest in manifests:
        tool = by_name[manifest["name"]]
        assert manifest["operation"] == tool.operation
        assert manifest["authorization"]["required_scope"] == tool.required_scope
        assert manifest["input_schema"] == tool.input_schema
