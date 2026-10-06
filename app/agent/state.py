from typing import Any
from pydantic import BaseModel


class InvestigationContext(BaseModel):
    run_id: str
    incident_id: str
    title: str
    description: str
    severity: str
    current_step: int
    prior_steps: list[dict[str, Any]]
    memories: list[dict[str, Any]]
    approvals: list[dict[str, Any]]
    max_steps: int
