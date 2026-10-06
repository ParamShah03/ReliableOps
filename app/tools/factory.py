from app.tools.actions import RestartServiceTool, RollbackDeploymentTool
from app.tools.dependencies import GetServiceDependenciesTool
from app.tools.deployments import GetRecentDeploymentsTool
from app.tools.logs import SearchLogsTool
from app.tools.metrics import QueryMetricsTool
from app.tools.registry import ToolRegistry
from app.tools.runbooks import SearchRunbooksTool
from app.tools.tickets import CreateTicketTool


def build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in [
        SearchRunbooksTool(),
        QueryMetricsTool(),
        SearchLogsTool(),
        GetRecentDeploymentsTool(),
        GetServiceDependenciesTool(),
        CreateTicketTool(),
        RollbackDeploymentTool(),
        RestartServiceTool(),
    ]:
        registry.register(tool)
    return registry
