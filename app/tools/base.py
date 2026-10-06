from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.enums import RiskLevel

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class ToolContext(BaseModel):
    run_id: str
    step_number: int
    approved: bool = False


class BaseTool(ABC, Generic[InputT, OutputT]):
    name: str
    description: str
    input_model: type[InputT]
    output_model: type[OutputT]
    timeout_seconds: float = 3.0
    max_retries: int = 2
    risk_level: RiskLevel = RiskLevel.READ_ONLY

    @abstractmethod
    def execute(self, db: Session, args: InputT, context: ToolContext) -> OutputT:
        raise NotImplementedError

    def validate_input(self, raw: dict[str, Any]) -> InputT:
        return self.input_model.model_validate(raw)
