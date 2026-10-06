from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import RiskLevel
from app.db.models.entities import Ticket
from app.tools.base import BaseTool, ToolContext


class CreateTicketInput(BaseModel):
    summary: str
    severity: str
    details: str


class CreateTicketOutput(BaseModel):
    ticket_id: str
    created: bool


class CreateTicketTool(BaseTool[CreateTicketInput, CreateTicketOutput]):
    name = "create_ticket"
    description = "Create a simulated operations ticket. This is a safe side effect."
    input_model = CreateTicketInput
    output_model = CreateTicketOutput
    risk_level = RiskLevel.SAFE_WRITE

    def execute(self, db: Session, args: CreateTicketInput, context: ToolContext) -> CreateTicketOutput:
        execution_key = f"{context.run_id}:{context.step_number}:{self.name}"
        existing = db.scalar(select(Ticket).where(Ticket.execution_key == execution_key))
        if existing:
            return CreateTicketOutput(ticket_id=existing.id, created=False)
        ticket = Ticket(execution_key=execution_key, summary=args.summary, severity=args.severity, details=args.details)
        db.add(ticket)
        db.flush()
        return CreateTicketOutput(ticket_id=ticket.id, created=True)
