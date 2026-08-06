---
name: failure-mode-designer
description: Systematically design failure modes for critical system flows and components, including triggers, blast radius, detection signals, mitigation, degraded mode, recovery, data impact, retry safety, and test or chaos scenarios. Use whenever a system design needs resilience, outage analysis, dependency failure, overload, timeout, retry, recovery, RPO/RTO, or operational failure planning.
---

# Failure Mode Designer

Start from critical user flows and architecture components. Read `references/contract-v1.md` and `references/handoff-v1.md`, then return `FM-*` records in a state patch.

## Procedure

1. List critical flows and their dependency chain. Cover applicable classes: timeout, retry storm, duplicate delivery, partial failure, dependency outage, overload, corruption, region failure, and human/operational error.
2. For each meaningful failure, record trigger, blast radius, detection signal and threshold, mitigation, degraded mode, recovery steps, data impact, owner, and test/chaos scenario.
3. Treat retries as a coupled policy: bounded retry budget, exponential backoff, jitter, idempotency key, and classification of retryable errors. Do not recommend blind retries.
4. Link every critical flow to at least one `FM-*`. Tie recovery targets to `NFR-*`, RPO, or RTO evidence. A failure without detection is incomplete.
5. Record residual risks and safe next handoff. Never mark design complete; validation owns that gate.

## Acceptance checks

Run bundled `scripts/validate_failure_modes.py <failure-model.json>`, contract validation, repository validation, and skill-creator quick validation. Accept only when every critical flow has an FM record and every record has detection, recovery, data impact, and an executable test scenario.
