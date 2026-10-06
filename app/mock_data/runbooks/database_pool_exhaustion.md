# Database Connection Pool Exhaustion

## Symptoms
- Application latency increases sharply while CPU may remain normal.
- Database connection pool utilization approaches 100%.
- Logs contain messages such as `timeout waiting for database connection` or connection acquisition timeout.

## Diagnosis
Check database connection utilization and application latency over the same time window. Correlate the start of saturation with recent deployments or traffic changes. Confirm using application logs.

## Mitigation
Reduce concurrency, temporarily increase the pool only if the database can absorb the load, and rollback a deployment if it introduced a connection leak. A rollback is a risky production action and requires explicit human approval.
