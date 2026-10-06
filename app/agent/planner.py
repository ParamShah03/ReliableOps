from __future__ import annotations

from app.agent.decisions import AgentDecisionAdapter
from app.agent.prompts import planner_prompt
from app.agent.state import InvestigationContext
from app.llm.mock import MockLLMClient
from app.tools.registry import ToolRegistry


class AgentPlanner:
    def __init__(self, llm_client, registry: ToolRegistry):
        self.llm = llm_client
        self.registry = registry

    def decide(self, context: InvestigationContext):
        if isinstance(self.llm, MockLLMClient):
            return self.llm.plan(context.model_dump(mode="json"))
        prompt = planner_prompt(context, self.registry.descriptions())
        return self.llm.generate_structured(prompt, AgentDecisionAdapter)
