# Queue Backlog

## Symptoms
Queue depth and processing age rise while consumers cannot keep up.

## Diagnosis
Compare producer throughput, consumer throughput, CPU, downstream dependencies, and error rates. Determine whether consumers are slow or downstream calls are blocking them.

## Mitigation
Scale consumers, repair the downstream bottleneck, or temporarily shed non-critical work.
