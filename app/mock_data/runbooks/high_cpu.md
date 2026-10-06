# High CPU

## Symptoms
CPU remains above 90%, latency increases, queues may grow, and request handlers become slow.

## Diagnosis
Check CPU, throughput, recent deployments, hot endpoints, and dependency behavior. High CPU with normal throughput often indicates inefficient work or a runaway loop.

## Mitigation
Scale out, reduce expensive work, or rollback a recent bad deployment after approval.
