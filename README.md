# Zero-Cost CI Bridge

A minimal public CI execution surface for running controlled,
ephemeral validation workloads on standard GitHub-hosted runners.

## Security model

- No private application source is committed to this repository.
- No production credentials are stored in source control.
- Private workloads may exist only temporarily inside an ephemeral runner.
- Private source must never be uploaded as an artifact or cache.
- Workflow logs must expose only sanitized validation status.
- Workloads must use least-privilege credentials.
- Temporary source and runtime state must be deleted during cleanup.
- Standard public GitHub-hosted runners only.
- No paid runners or external paid CI services.

## Status

Architecture bootstrap only. No private-source integration is enabled.
