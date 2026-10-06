from __future__ import annotations

import time
from typing import Any

from pydantic import TypeAdapter

from app.agent.decisions import FinalizeDecision, FinalReport, EvidenceItem, ToolDecision
from app.llm.base import LLMResult


class MockLLMClient:
    """Deterministic planner for local demos, CI, and interview walkthroughs."""

    model_name = "reliableops-mock-v1"

    def generate(self, prompt: str) -> str:
        return "Mock provider only supports structured investigation planning."

    def generate_structured(self, prompt: str, adapter: TypeAdapter, *, repair_hint: str | None = None) -> LLMResult:
        raise RuntimeError("MockLLMClient requires plan(context), not free-form prompt generation")

    def plan(self, context: dict[str, Any]) -> LLMResult:
        start = time.perf_counter()
        steps = context["prior_steps"]
        called = [s.get("tool_name") for s in steps if s.get("tool_name")]
        description = f"{context['title']} {context['description']}".lower()
        service = self._service_from_text(description)
        rejected = any(a.get("status") == "REJECTED" for a in context.get("approvals", []))
        risky_completed = any(s.get("tool_name") in {"rollback_deployment", "restart_service"} and s.get("status") == "COMPLETED" for s in steps)

        if "search_runbooks" not in called:
            decision = ToolDecision(
                action="tool",
                decision_summary="Retrieve operational guidance relevant to the reported symptoms before forming a root-cause hypothesis.",
                reason="Runbooks provide diagnosis criteria and safe mitigation guidance.",
                tool_name="search_runbooks",
                tool_input={"query": context["description"], "top_k": 4},
            )
        elif "get_recent_deployments" not in called:
            decision = ToolDecision(
                action="tool",
                decision_summary=f"Check whether {service} changed close to the incident start.",
                reason="A recent deployment can explain a sudden regression but must be corroborated with technical evidence.",
                tool_name="get_recent_deployments",
                tool_input={"service": service, "limit": 5},
            )
        elif "query_metrics" not in called:
            decision = ToolDecision(
                action="tool",
                decision_summary=f"Measure latency for {service} during the reported incident window.",
                reason="We need objective time-series evidence that the degradation occurred and when it started.",
                tool_name="query_metrics",
                tool_input={
                    "service": service,
                    "metric": "latency_ms",
                    "start_time": "2026-10-05T10:00:00Z" if service == "payment-service" else "2026-10-05T13:55:00Z",
                    "end_time": "2026-10-05T10:30:00Z" if service == "payment-service" else "2026-10-05T14:10:00Z",
                },
            )
        elif service == "payment-service" and not self._metric_called(steps, "database_connections"):
            decision = ToolDecision(
                action="tool",
                decision_summary="Check database connection utilization because the runbook and symptoms are consistent with pool exhaustion.",
                reason="Saturation near 100% would directly explain connection acquisition delays and elevated latency.",
                tool_name="query_metrics",
                tool_input={
                    "service": "payment-service",
                    "metric": "database_connections",
                    "start_time": "2026-10-05T10:00:00Z",
                    "end_time": "2026-10-05T10:30:00Z",
                },
            )
        elif "search_logs" not in called:
            query = "database" if service == "payment-service" else "timeout"
            decision = ToolDecision(
                action="tool",
                decision_summary=f"Search {service} logs for an error mechanism that explains the observed metrics.",
                reason="Log evidence can distinguish correlation from a causal technical failure mode.",
                tool_name="search_logs",
                tool_input={
                    "service": service,
                    "query": query,
                    "start_time": "2026-10-05T10:00:00Z" if service == "payment-service" else "2026-10-05T13:55:00Z",
                    "end_time": "2026-10-05T10:30:00Z" if service == "payment-service" else "2026-10-05T14:10:00Z",
                },
            )
        elif "get_service_dependencies" not in called:
            decision = ToolDecision(
                action="tool",
                decision_summary=f"Inspect dependencies for {service} to rule in or out an upstream/downstream cause.",
                reason="A service can appear unhealthy because a dependency is degraded.",
                tool_name="get_service_dependencies",
                tool_input={"service": service},
            )
        elif service == "order-service" and not self._metric_called(steps, "cpu_usage"):
            decision = ToolDecision(
                action="tool",
                decision_summary="Check order-service CPU to test whether the recent deployment itself is resource-saturating the service.",
                reason="Normal CPU would weaken the bad-deployment hypothesis and point toward a dependency issue.",
                tool_name="query_metrics",
                tool_input={"service": "order-service", "metric": "cpu_usage", "start_time": "2026-10-05T13:55:00Z", "end_time": "2026-10-05T14:10:00Z"},
            )
        elif service == "order-service" and not self._metric_called_service(steps, "auth-service", "cpu_usage"):
            decision = ToolDecision(
                action="tool",
                decision_summary="Order logs identify auth-service as the slow dependency, so inspect auth-service CPU directly.",
                reason="This tests the dependency-root-cause hypothesis using independent metric evidence.",
                tool_name="query_metrics",
                tool_input={"service": "auth-service", "metric": "cpu_usage", "start_time": "2026-10-05T13:55:00Z", "end_time": "2026-10-05T14:10:00Z"},
            )
        elif service == "payment-service" and not rejected and not risky_completed and "rollback_deployment" not in called:
            version = self._latest_version(steps) or "v1.4.2"
            decision = ToolDecision(
                action="tool",
                decision_summary="Evidence strongly links the regression to the recent payment deployment and database pool exhaustion; propose a rollback.",
                reason="Rollback is the fastest mitigation but must be gated by human approval.",
                tool_name="rollback_deployment",
                tool_input={"service": "payment-service", "version": version},
            )
        elif rejected and "create_ticket" not in called:
            decision = ToolDecision(
                action="tool",
                decision_summary="The risky mitigation was rejected, so create a high-severity ticket with the evidence and safer next steps.",
                reason="A rejected action should not be retried automatically; escalation preserves safety and auditability.",
                tool_name="create_ticket",
                tool_input={"summary": f"Investigate {service} incident", "severity": context["severity"], "details": "Risky remediation was rejected. Review collected metrics, logs, runbooks, and deployment evidence."},
            )
        else:
            decision = self._finalize(context, service)

        return LLMResult(data=decision, latency_ms=(time.perf_counter() - start) * 1000, input_tokens=0, output_tokens=0)

    @staticmethod
    def _service_from_text(text: str) -> str:
        for service in ["payment-service", "order-service", "auth-service", "api-gateway"]:
            if service in text or service.replace("-service", "") in text:
                return service
        return "payment-service"

    @staticmethod
    def _metric_called(steps: list[dict], metric: str) -> bool:
        return any(s.get("tool_name") == "query_metrics" and (s.get("tool_input") or {}).get("metric") == metric for s in steps)

    @staticmethod
    def _metric_called_service(steps: list[dict], service: str, metric: str) -> bool:
        return any(s.get("tool_name") == "query_metrics" and (s.get("tool_input") or {}).get("metric") == metric and (s.get("tool_input") or {}).get("service") == service for s in steps)

    @staticmethod
    def _latest_version(steps: list[dict]) -> str | None:
        for step in steps:
            if step.get("tool_name") == "get_recent_deployments":
                deployments = (step.get("tool_output") or {}).get("deployments") or []
                if deployments:
                    return deployments[0].get("version")
        return None

    def _finalize(self, context: dict[str, Any], service: str) -> FinalizeDecision:
        steps = context["prior_steps"]
        evidence: list[EvidenceItem] = []
        runbooks: list[str] = []
        deployment: str | None = None

        for step in steps:
            out = step.get("tool_output") or {}
            if step.get("tool_name") == "search_runbooks":
                for item in out.get("results", [])[:3]:
                    runbooks.append(item["document_name"])
                    evidence.append(EvidenceItem(source="runbook", detail=f"{item['document_name']}: {item['chunk_text'][:180]}", step_number=step["step_number"]))
            elif step.get("tool_name") == "get_recent_deployments" and out.get("deployments"):
                d = out["deployments"][0]
                deployment = f"{d['service']} {d['version']} at {d['deployed_at']}"
                evidence.append(EvidenceItem(source="deployment", detail=deployment, step_number=step["step_number"]))
            elif step.get("tool_name") == "query_metrics":
                metric = (step.get("tool_input") or {}).get("metric")
                evidence.append(EvidenceItem(source="metrics", detail=out.get("summary", f"Queried {metric}"), step_number=step["step_number"]))
            elif step.get("tool_name") == "search_logs" and out.get("matches"):
                evidence.append(EvidenceItem(source="logs", detail=out["matches"][-1]["message"], step_number=step["step_number"]))

        if service == "payment-service":
            root = "database connection pool exhaustion introduced by payment-service v1.4.2"
            actions = [
                "Rollback payment-service v1.4.2 if approved and monitor latency/error rate after the simulated rollback.",
                "Audit connection lifecycle changes in v1.4.2 and add pool saturation alerts.",
                "Load-test the corrected build before redeployment.",
            ]
            confidence = 0.93
        elif service == "order-service":
            root = "auth-service CPU saturation causing downstream authentication timeouts; the order-service deployment is correlated but not causal"
            actions = [
                "Scale or restore auth-service capacity.",
                "Profile token verification and reduce expensive work on the hot path.",
                "Keep the order-service deployment under observation rather than rolling it back without evidence.",
            ]
            confidence = 0.89
        else:
            root = f"degradation affecting {service}; evidence indicates dependency or resource saturation"
            actions = ["Continue targeted dependency investigation.", "Create an operations ticket with the collected evidence."]
            confidence = 0.72

        report = FinalReport(
            incident_summary=context["description"],
            root_cause=root,
            confidence=confidence,
            supporting_evidence=evidence[-8:],
            related_deployment=deployment,
            recommended_actions=actions,
            runbook_sources=sorted(set(runbooks)),
        )
        return FinalizeDecision(action="finalize", decision_summary="Sufficient independent evidence exists to produce a grounded incident report.", reason="The report cites persisted tool evidence and separates recommendations from executed actions.", report=report)
