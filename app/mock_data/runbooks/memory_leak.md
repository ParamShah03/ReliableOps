# Memory Leak

## Symptoms
Memory grows monotonically, garbage collection becomes frequent, and the service may restart or be OOM-killed.

## Diagnosis
Compare memory growth to request throughput and deployment timestamps. Look for OOM messages, GC pressure, and object retention patterns.

## Mitigation
Restarting can temporarily restore service but requires approval. The durable fix is to identify the leaking allocation path and deploy a correction.
