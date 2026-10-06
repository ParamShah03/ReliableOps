from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.tools.base import BaseTool, ToolContext
from app.tools.mock_loader import load_json


class RecentDeploymentsInput(BaseModel):
    service: str
    limit: int = 5


class Deployment(BaseModel):
    service: str
    version: str
    deployed_at: datetime
    commit: str
    status: str


class RecentDeploymentsOutput(BaseModel):
    deployments: list[Deployment]


class GetRecentDeploymentsTool(BaseTool[RecentDeploymentsInput, RecentDeploymentsOutput]):
    name = "get_recent_deployments"
    description = "Return recent simulated deployments for a service."
    input_model = RecentDeploymentsInput
    output_model = RecentDeploymentsOutput

    def execute(self, db: Session, args: RecentDeploymentsInput, context: ToolContext) -> RecentDeploymentsOutput:
        data = load_json("deployments/deployments.json")
        rows = [Deployment.model_validate(x) for x in data if x["service"] == args.service]
        rows.sort(key=lambda x: x.deployed_at, reverse=True)
        return RecentDeploymentsOutput(deployments=rows[: args.limit])
