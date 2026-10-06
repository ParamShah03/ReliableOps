from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.orchestrator import AgentOrchestrator
from app.core.enums import ApprovalStatus, RunStatus
from app.db.models.entities import ActionExecution, AgentRun, AgentStep, Approval, Evaluation, Incident
from app.evals.scoring import score_case
from app.services.approval_service import resolve_approval


DATASET_DIR = Path(__file__).resolve().parent / "datasets"


class EvaluationRunner:
    def __init__(self):
        self.orchestrator = AgentOrchestrator()

    def load_cases(self, case_ids: list[str] | None = None) -> list[dict[str, Any]]:
        cases = []
        for path in sorted(DATASET_DIR.glob("incident_*.json")):
            case = json.loads(path.read_text(encoding="utf-8"))
            if not case_ids or case["id"] in case_ids:
                cases.append(case)
        return cases

    def run_cases(self, db: Session, case_ids: list[str] | None = None, agent_version: str = "v1") -> dict[str, Any]:
        results = []
        for case in self.load_cases(case_ids):
            started = time.perf_counter()
            incident = Incident(**case["incident"], status="OPEN")
            db.add(incident)
            db.flush()
            run = AgentRun(incident_id=incident.id, status=RunStatus.QUEUED.value, model_name="reliableops-mock-v1")
            db.add(run)
            db.commit()

            self.orchestrator.run(db, run.id)
            db.refresh(run)
            if run.status == RunStatus.WAITING_FOR_APPROVAL.value:
                pending = db.scalars(
                    select(Approval).where(Approval.run_id == run.id, Approval.status == ApprovalStatus.PENDING.value)
                ).all()
                for approval in pending:
                    resolve_approval(db, approval.id, approve=False, resolved_by="evaluation-safety-policy")
                self.orchestrator.run(db, run.id)
                db.refresh(run)

            steps_orm = db.scalars(select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.step_number)).all()
            steps = [
                {
                    "step_number": s.step_number,
                    "tool_name": s.tool_name,
                    "tool_input": s.tool_input,
                    "tool_output": s.tool_output,
                    "status": s.status,
                }
                for s in steps_orm
            ]
            risky = db.scalars(select(ActionExecution).where(ActionExecution.run_id == run.id)).all()
            risky_rows = [{"action": x.action, "approved": x.approved, "payload": x.payload} for x in risky]
            report = run.final_report or {}
            scores = score_case(case, report, steps, risky_rows)
            latency_ms = (time.perf_counter() - started) * 1000

            evaluation = Evaluation(
                run_id=run.id,
                case_id=case["id"],
                agent_version=agent_version,
                task_success=float(scores["task_success"]),
                groundedness=float(scores["groundedness"]),
                tool_selection_score=float(scores["tool_selection_score"]),
                safety_score=float(scores["safety_score"]),
                completeness_score=float(scores["completeness_score"]),
                efficiency_score=float(scores["efficiency_score"]),
                latency_ms=latency_ms,
                evaluator_notes=str(scores["notes"]),
            )
            db.add(evaluation)
            db.commit()
            results.append(
                {
                    "case_id": case["id"],
                    "run_id": run.id,
                    "status": run.status,
                    **{k: v for k, v in scores.items() if k != "notes"},
                    "latency_ms": round(latency_ms, 2),
                }
            )

        def avg(key: str) -> float:
            return round(sum(float(r[key]) for r in results) / max(1, len(results)), 3)

        return {
            "agent_version": agent_version,
            "cases": len(results),
            "task_success": avg("task_success"),
            "tool_selection": avg("tool_selection_score"),
            "groundedness": avg("groundedness"),
            "safety": avg("safety_score"),
            "completeness": avg("completeness_score"),
            "efficiency": avg("efficiency_score"),
            "average_steps": round(sum(self._step_count(db, r["run_id"]) for r in results) / max(1, len(results)), 2),
            "average_latency_ms": round(sum(float(r["latency_ms"]) for r in results) / max(1, len(results)), 2),
            "results": results,
        }

    @staticmethod
    def _step_count(db: Session, run_id: str) -> int:
        return len(db.scalars(select(AgentStep).where(AgentStep.run_id == run_id)).all())
