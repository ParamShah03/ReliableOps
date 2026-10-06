from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import RiskLevel
from app.db.models.entities import ActionExecution
from app.tools.base import BaseTool, ToolContext


class RollbackDeploymentInput(BaseModel):
    service: str
    version: str


class RestartServiceInput(BaseModel):
    service: str


class RiskyActionOutput(BaseModel):
    action: str
    status: str
    simulated: bool = True
    details: str


class _RiskyActionBase(BaseTool):
    risk_level = RiskLevel.REQUIRES_APPROVAL
    max_retries = 0

    def _record(self, db: Session, context: ToolContext, action: str, payload: dict, details: str) -> RiskyActionOutput:
        execution_key = f"{context.run_id}:{context.step_number}:{action}"
        existing = db.scalar(select(ActionExecution).where(ActionExecution.execution_key == execution_key))
        if existing:
            return RiskyActionOutput.model_validate(existing.result)
        result = RiskyActionOutput(action=action, status="SIMULATED_SUCCESS", details=details)
        db.add(
            ActionExecution(
                execution_key=execution_key,
                run_id=context.run_id,
                action=action,
                payload=payload,
                approved=context.approved,
                result=result.model_dump(mode="json"),
            )
        )
        db.flush()
        return result


class RollbackDeploymentTool(_RiskyActionBase, BaseTool[RollbackDeploymentInput, RiskyActionOutput]):
    name = "rollback_deployment"
    description = "Simulate rolling back a service deployment. Requires explicit human approval."
    input_model = RollbackDeploymentInput
    output_model = RiskyActionOutput

    def execute(self, db: Session, args: RollbackDeploymentInput, context: ToolContext) -> RiskyActionOutput:
        return self._record(db, context, self.name, args.model_dump(), f"Rolled back {args.service} from {args.version} in simulation.")


class RestartServiceTool(_RiskyActionBase, BaseTool[RestartServiceInput, RiskyActionOutput]):
    name = "restart_service"
    description = "Simulate restarting a service. Requires explicit human approval."
    input_model = RestartServiceInput
    output_model = RiskyActionOutput

    def execute(self, db: Session, args: RestartServiceInput, context: ToolContext) -> RiskyActionOutput:
        return self._record(db, context, self.name, args.model_dump(), f"Restarted {args.service} in simulation.")
