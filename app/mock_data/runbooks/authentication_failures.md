# Authentication Failures

## Symptoms
401 or 403 responses increase, token verification latency rises, or authentication requests time out.

## Diagnosis
Inspect auth-service latency, CPU, signing-key errors, token validation logs, and callers that depend on auth-service.

## Mitigation
Correct key/configuration issues or restore auth-service capacity. Restarting auth-service is a risky action requiring approval.
