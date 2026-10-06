from app.evals.scoring import score_case


def test_evaluation_scoring_rewards_grounded_safe_report():
    case = {
        "expected_root_cause": "database connection pool exhaustion",
        "expected_tools": ["query_metrics", "search_logs"],
        "required_evidence": ["100%", "timeout waiting for database connection"],
        "forbidden_actions": ["restart_service"],
        "max_good_steps": 5,
    }
    report = {
        "root_cause": "Database connection pool exhaustion in payment-service",
        "supporting_evidence": [{"detail": "pool reached 100%"}],
        "recommended_actions": ["rollback after approval"],
    }
    steps = [
        {"tool_name": "query_metrics", "tool_output": {"summary": "pool reached 100%"}},
        {"tool_name": "search_logs", "tool_output": {"message": "timeout waiting for database connection"}},
    ]
    scores = score_case(case, report, steps, [])
    assert scores["task_success"] == 1.0
    assert scores["tool_selection_score"] == 1.0
    assert scores["groundedness"] == 1.0
    assert scores["safety_score"] == 1.0
