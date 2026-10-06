import pytest
from app.core.exceptions import UnknownToolError
from app.tools.factory import build_tool_registry


def test_registry_contains_only_known_tools():
    registry = build_tool_registry()
    assert set(registry.names()) == {
        "create_ticket",
        "get_recent_deployments",
        "get_service_dependencies",
        "query_metrics",
        "restart_service",
        "rollback_deployment",
        "search_logs",
        "search_runbooks",
    }


def test_unknown_tool_is_rejected():
    with pytest.raises(UnknownToolError):
        build_tool_registry().get("delete_production_database")
