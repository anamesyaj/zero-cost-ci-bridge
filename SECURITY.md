# Security Policy

This public repository must remain free of private application material.

## Public boundary

Only generic CI documentation and generic workflow code may be committed here. Private source, private identifiers, private diagnostics, non-public data, and confidential configuration must remain outside this repository and its Git history.

## Ephemeral execution

Private validation workloads may exist only temporarily inside an ephemeral standard GitHub-hosted runner during an explicitly authorized job.

The implementation must use an exact immutable source revision, least-privilege read-only source access, sanitized public status output, unconditional cleanup, and final runner disposal.

## Public logs

Actions logs are public. Validation commands must not publish detailed private output. Public output must be limited to generic phase status and generic failure classes.

## No persistence

Private workload material must not be stored in Actions caches, workflow artifacts, releases, job summaries, public issues, public pull requests, or external logging services.

## Controlled triggers

The initial private-validation path must be manually dispatched. Untrusted public pull-request code must not receive private-source access. `pull_request_target` must not be used for private-source execution.

## Zero-cost requirement

Only standard GitHub-hosted runner capacity that is zero-cost for this public repository may be used. The system must fail closed rather than fall back to paid runner or external CI capacity.

## Cleanup

Cleanup is mandatory even when validation fails. Temporary source, temporary logs, containers, volumes, and transient runtime state must be removed before completion. A required cleanup failure means certification is not successful.

## Reporting concerns

Do not place sensitive evidence in public issues. Establish a private communication channel with the repository owner before sharing sensitive details.
