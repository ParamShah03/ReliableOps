from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.tools.base import BaseTool, ToolContext
from app.tools.mock_loader import load_json


class ServiceDependenciesInput(BaseModel):
    service: str


class ServiceDependenciesOutput(BaseModel):
    service: str
    depends_on: list[str]
    depended_on_by: list[str]


class GetServiceDependenciesTool(BaseTool[ServiceDependenciesInput, ServiceDependenciesOutput]):
    name = "get_service_dependencies"
    description = "Return dependency graph information for a simulated service."
    input_model = ServiceDependenciesInput
    output_model = ServiceDependenciesOutput

    def execute(self, db: Session, args: ServiceDependenciesInput, context: ToolContext) -> ServiceDependenciesOutput:
        graph: dict[str, list[str]] = load_json("dependencies.json")
        upstream = graph.get(args.service, [])
        downstream = [service for service, deps in graph.items() if args.service in deps]
        return ServiceDependenciesOutput(service=args.service, depends_on=upstream, depended_on_by=downstream)
