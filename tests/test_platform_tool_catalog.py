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
        "twi_evidence_export",
        "twi_research_verify",
        "twi_world_intelligence_export",
        "twi_world_intelligence_export_status",
        "twi_monitor_create",
        "twi_monitor_read",
        "twi_monitor_run",
        "twi_monitor_pause",
        "twi_monitor_resume",
        "twi_monitor_delete",
        "twi_usage_read",
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



def test_usage_read_tool_is_tenant_scoped_and_read_only() -> None:
    tool = next(item for item in TWI_PLATFORM_TOOLS if item.name == "twi_usage_read")
    assert tool.operation == "twi.usage.read"
    assert tool.required_scope == "twi:usage:read"
    assert tool.capability == "web.usage.read"
    assert tool.resource_pattern == "twi://usage/*"
    assert tool.read_only is True
    assert tool.consequential is False
    assert tool.destructive is False
    assert tool.open_world is False
    assert tool.input_schema["properties"]["period_start"]["maxLength"] == 40
