# Task: Chronos-Recurse Repository Audit & Refactor

## Status
- [ ] Bootstrap Chronos Control Plane
- [ ] Cycle 1: Snapshot & Initial Audit
- [ ] Cycle 2: WebSIFT Remediation (if warnings found)
- [ ] Cycle 3: Elimination of Brittle Constants
- [ ] Cycle 4: Deployment & Verification

## Context
The user requires a full audit of the `dayz_discord_ops_repo` using the **CHRONOS-RECURSE** protocol. This involves:
1.  **Repo-Scoped Mutation**: Changes are limited to this repository.
2.  **Proof-Gated Changes**: Every change must be verified.
3.  **Warning-Triggered WebSIFT**: Warnings trigger external research.
4.  **Mixture of Experts (MoE)**: Simulating multiple roles (Exhumer, Cartographer, etc.) to decide on changes.

## Goals
1.  **Audit**: Identify all hardcoded Discord IDs, paths, and potential syntax/lint errors.
2.  **Refactor**: Move hardcoded values to the Registry or Configuration.
3.  **Deploy**: Ensure the bot and services can launch without "Endless" loops, using smoke tests instead.
4.  **Verify**: Idempotence and correctness of all operations.

## Constraints
- **Single Mutation Cluster per Cycle**: Only one set of related changes at a time.
- **Freshness Gate**: Verify file state before writing.
- **No Blockers**: If creds are missing, mock/stub and proceed.
- **Artifacts**: All outputs must be structured events/files in `.chronos`.
