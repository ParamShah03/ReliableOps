# Bad Deployment

## Symptoms
Errors or latency begin within minutes of a deployment and were absent before it.

## Diagnosis
Correlate the deployment timestamp with metric and log changes. A deployment correlation is not sufficient alone: confirm a plausible technical mechanism using metrics or logs.

## Mitigation
If evidence is strong, prepare a rollback. Rollback execution requires explicit human approval.
