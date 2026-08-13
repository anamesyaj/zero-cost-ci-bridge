# Transient Validation Architecture R1

## Purpose

Provide a generic public CI execution surface for controlled validation jobs on ephemeral standard GitHub-hosted runners.

## Design principles

- Repository history contains reusable CI documentation and orchestration only.
- Validation inputs are supplied at runtime and are not committed here.
- Each certification targets an exact immutable revision.
- Detailed command output remains temporary during execution.
- Public output is limited to concise phase status and generic failure categories.
- Runtime inputs and temporary logs are not persisted through caches or artifacts.
- Cleanup runs on both success and failure.
- Cancelled, skipped, partial, timed-out, or cleanup-incomplete runs are not successful certifications.
- Standard zero-cost hosted runner capacity is required and there is no paid fallback.

## R1 flow

1. Controlled manual dispatch.
2. Confirm the permitted hosted-runner class.
3. Resolve the exact validation revision.
4. Prepare temporary runner-local input.
5. Install required dependencies.
6. Run the required validation phases.
7. Emit sanitized phase outcomes.
8. Remove temporary input, logs, and local runtime state.
9. Complete the job and allow runner disposal.

## Trigger model

R1 uses manual dispatch only. Automated triggering is outside R1 and requires a separate architecture review.

## Persistence model

R1 does not use caches or artifacts for runtime validation inputs or detailed runtime output. Public reports contain only sanitized status information.

## Success contract

Certification succeeds only when every required validation phase and the cleanup phase succeed.

## Implementation sequence

Architecture approval precedes executable workflow publication. Workflow implementation and runtime configuration require separate authorization.
