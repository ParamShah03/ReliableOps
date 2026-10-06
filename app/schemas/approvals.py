from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class ApprovalResolution(BaseModel):
    resolved_by: str = "local-user"


class ApprovalRead(BaseModel):
    id: str
    run_id: str
    step_id: str
    action: str
    action_payload: dict[str, Any]
    status: str
    requested_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None
    executed_at: datetime | None
    model_config = ConfigDict(from_attributes=True)
