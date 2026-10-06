# Dependency Timeout

## Symptoms
A healthy service reports downstream timeout errors while CPU and memory remain normal.

## Diagnosis
Inspect dependency topology. Query the dependency's latency and logs. Do not assume the most recently deployed caller is the root cause if its own resource metrics are normal.

## Mitigation
Restore the unhealthy dependency, use circuit breakers, and consider temporary traffic shedding.
