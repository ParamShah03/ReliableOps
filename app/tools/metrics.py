from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.tools.base import BaseTool, ToolContext
from app.tools.mock_loader import load_json


class QueryMetricsInput(BaseModel):
    service: str
    metric: str
    start_time: datetime
    end_time: datetime


class MetricPoint(BaseModel):
    timestamp: datetime
    value: float


class QueryMetricsOutput(BaseModel):
    service: str
    metric: str
    unit: str
    points: list[MetricPoint]
    summary: str


class QueryMetricsTool(BaseTool[QueryMetricsInput, QueryMetricsOutput]):
    name = "query_metrics"
    description = "Query simulated infrastructure time-series metrics for a service and time window."
    input_model = QueryMetricsInput
    output_model = QueryMetricsOutput
    timeout_seconds = 2.0
    max_retries = 2

    def execute(self, db: Session, args: QueryMetricsInput, context: ToolContext) -> QueryMetricsOutput:
        data = load_json("metrics/metrics.json")
        series = data.get(args.service, {}).get(args.metric)
        if not series:
            return QueryMetricsOutput(service=args.service, metric=args.metric, unit="unknown", points=[], summary="No metric data found.")
        points = [MetricPoint.model_validate(p) for p in series["points"]]
        filtered = [p for p in points if args.start_time <= p.timestamp <= args.end_time]
        if not filtered:
            summary = "No points in the requested window."
        else:
            values = [p.value for p in filtered]
            summary = f"{args.metric} ranged from {min(values):.2f} to {max(values):.2f}; latest={values[-1]:.2f}."
        return QueryMetricsOutput(service=args.service, metric=args.metric, unit=series["unit"], points=filtered, summary=summary)
