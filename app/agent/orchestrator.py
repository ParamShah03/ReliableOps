from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.context_builder import build_context
from app.agent.decisions import FinalizeDecision, ToolDecision
from app.agent.planner import AgentPlanner
from app.core.config import get_settings
from app.core.enums import ApprovalStatus, IncidentStatus, RunStatus, StepStatus
from app.core.exceptions import ApprovalRequired, ReliableOpsError
from app.db.models.entities import AgentRun, AgentStep, Approval, Incident, LLMCall
from app.llm.factory import build_llm_client
from app.services.memory_service import upsert_memory
from app.tools.base import ToolContext
from app.tools.executor import ToolExecutor
from app.tools.factory import build_tool_registry

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self):
        self.settings = get_settings()
        self.registry = build_tool_registry()
        self.executor = ToolExecutor(self.registry)

    def run(self, db: Session, run_id: str) -> AgentRun:
        run = db.get(AgentRun, run_id)
        if not run:
            raise LookupError(f"Run not found: {run_id}")
        if run.status in {RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.MAX_STEPS_EXCEEDED.value}:
            return run

        if not run.started_at:
            run.started_at = datetime.now(timezone.utc)
        run.status = RunStatus.RUNNING.value
        db.commit()

        if self._resume_approved_action(db, run):
            db.refresh(run)

        while run.current_step < self.settings.max_agent_steps:
            if run.status == RunStatus.WAITING_FOR_APPROVAL.value:
                return run

            context = build_context(db, run, self.settings.max_agent_steps)
            llm = build_llm_client(run.model_name)
            planner = AgentPlanner(llm, self.registry)
            try:
                llm_result = planner.decide(context)
            except Exception as exc:
                return self._fail_run(db, run, f"LLM/planner failure: {exc}")

            self._record_llm_call(db, run, run.current_step + 1, llm_result)
            decision = llm_result.data
            if isinstance(decision, FinalizeDecision):
                return self._finalize(db, run, decision)
            if not isinstance(decision, ToolDecision):
                return self._fail_run(db, run, f"Unsupported planner decision: {type(decision).__name__}")

            if self._same_tool_signature_count(db, run.id, decision.tool_name, decision.tool_input) >= self.settings.max_same_tool_signature:
                self._record_failed_tool_step(db, run, decision, "Repeated identical tool call blocked by loop protection")
                db.refresh(run)
                continue

            step = AgentStep(
                run_id=run.id,
                step_number=run.current_step + 1,
                step_type="TOOL_CALL",
                reasoning_summary=decision.decision_summary,
                tool_name=decision.tool_name,
                tool_input=decision.tool_input,
                status=StepStatus.RUNNING.value,
            )
            db.add(step)
            run.current_step = step.step_number
            db.commit()
            db.refresh(step)

            try:
                result = self.executor.execute(
                    db,
                    decision.tool_name,
                    decision.tool_input,
                    ToolContext(run_id=run.id, step_number=step.step_number, approved=False),
                )
                step.tool_output = result.output
                step.latency_ms = result.latency_ms
                step.retry_count = result.retries
                step.status = StepStatus.COMPLETED.value
                upsert_memory(db, run.id, "working_evidence", f"step_{step.step_number}_{decision.tool_name}", result.output)
                db.commit()
            except ApprovalRequired as required:
                approval = Approval(
                    run_id=run.id,
                    step_id=step.id,
                    action=required.tool_name,
                    action_payload=required.payload,
                    status=ApprovalStatus.PENDING.value,
                )
                db.add(approval)
                step.status = StepStatus.WAITING_FOR_APPROVAL.value
                run.status = RunStatus.WAITING_FOR_APPROVAL.value
                db.commit()
                return run
            except Exception as exc:
                step.status = StepStatus.FAILED.value
                step.error_message = str(exc)
                upsert_memory(db, run.id, "tool_failure", f"step_{step.step_number}_{decision.tool_name}", {"error": str(exc)})
                db.commit()

            db.refresh(run)

        run.status = RunStatus.MAX_STEPS_EXCEEDED.value
        run.failure_reason = f"Exceeded maximum of {self.settings.max_agent_steps} agent steps"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        return run

    def _resume_approved_action(self, db: Session, run: AgentRun) -> bool:
        approval = db.scalar(
            select(Approval)
            .where(
                Approval.run_id == run.id,
                Approval.status == ApprovalStatus.APPROVED.value,
                Approval.executed_at.is_(None),
            )
            .order_by(Approval.requested_at)
        )
        if not approval:
            return False
        step = db.get(AgentStep, approval.step_id)
        if not step:
            return False

        result = self.executor.execute(
            db,
            approval.action,
            approval.action_payload,
            ToolContext(run_id=run.id, step_number=step.step_number, approved=True),
        )
        step.tool_output = result.output
        step.latency_ms = result.latency_ms
        step.retry_count = result.retries
        step.status = StepStatus.COMPLETED.value
        approval.executed_at = datetime.now(timezone.utc)
        run.status = RunStatus.RUNNING.value
        upsert_memory(db, run.id, "approved_action", f"step_{step.step_number}_{approval.action}", result.output)
        db.commit()
        return True

    def _finalize(self, db: Session, run: AgentRun, decision: FinalizeDecision) -> AgentRun:
        step = AgentStep(
            run_id=run.id,
            step_number=run.current_step + 1,
            step_type="FINAL_REPORT",
            reasoning_summary=decision.decision_summary,
            tool_output=decision.report.model_dump(mode="json"),
            status=StepStatus.COMPLETED.value,
        )
        db.add(step)
        run.current_step = step.step_number
        run.final_report = decision.report.model_dump(mode="json")
        run.status = RunStatus.COMPLETED.value
        run.completed_at = datetime.now(timezone.utc)
        incident = db.get(Incident, run.incident_id)
        if incident:
            incident.status = IncidentStatus.RESOLVED.value
        db.commit()
        db.refresh(run)
        return run

    def _fail_run(self, db: Session, run: AgentRun, reason: str) -> AgentRun:
        run.status = RunStatus.FAILED.value
        run.failure_reason = reason
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        return run

    def _record_llm_call(self, db: Session, run: AgentRun, step_number: int, result) -> None:
        db.add(
            LLMCall(
                run_id=run.id,
                step_number=step_number,
                model_name=run.model_name,
                latency_ms=result.latency_ms,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                retry_count=result.retry_count,
                validation_error=result.validation_error,
            )
        )
        db.commit()

    def _same_tool_signature_count(self, db: Session, run_id: str, tool_name: str, tool_input: dict) -> int:
        target = hashlib.sha256(json.dumps(tool_input, sort_keys=True, default=str).encode()).hexdigest()
        steps = db.scalars(select(AgentStep).where(AgentStep.run_id == run_id, AgentStep.tool_name == tool_name)).all()
        count = 0
        for step in steps:
            digest = hashlib.sha256(json.dumps(step.tool_input or {}, sort_keys=True, default=str).encode()).hexdigest()
            if digest == target:
                count += 1
        return count

    def _record_failed_tool_step(self, db: Session, run: AgentRun, decision: ToolDecision, error: str) -> None:
        step = AgentStep(
            run_id=run.id,
            step_number=run.current_step + 1,
            step_type="TOOL_CALL",
            reasoning_summary=decision.decision_summary,
            tool_name=decision.tool_name,
            tool_input=decision.tool_input,
            status=StepStatus.FAILED.value,
            error_message=error,
        )
        db.add(step)
        run.current_step = step.step_number
        db.commit()
