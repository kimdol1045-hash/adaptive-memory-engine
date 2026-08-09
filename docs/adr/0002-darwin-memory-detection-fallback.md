# ADR-0002: macOS memory detection uses a verified fallback

- Status: Accepted
- Date: 2026-08-09
- Owners: AME maintainers
- Supersedes: none
- Superseded by: none

## Context

The primary macOS RAM probe is `sysctl -n hw.memsize`. Some sandboxed agent environments deny that command even though `system_profiler` can still report the hardware. Returning the generic 16GB fallback in that case assigns capable machines to the wrong model tier.

## Options considered

1. Keep a fixed 16GB fallback: simple, but produces known false tier assignments.
2. Require users to pass RAM manually: explicit, but adds configuration and bootstrap friction.
3. Try `sysctl`, then parse the JSON output of `system_profiler`, and use 16GB only when both probes fail.

## Decision

On Darwin, AME first reads byte-accurate RAM from `sysctl`. If that probe fails or returns invalid data, it calls `system_profiler SPHardwareDataType -json`, parses `physical_memory`, and normalizes MB, GB, or TB to GiB-scale tier input. The conservative 16GB fallback remains only for a complete probe failure.

## Consequences

- Sandboxed macOS sessions can receive the correct hardware tier when `system_profiler` is available.
- Hardware profiling can take longer when the fallback command is needed.
- Parsing is limited to the documented human-readable memory field and must be covered by tests.

## Verification

- A unit test forces `sysctl` to fail and asserts that `48 GB` from the JSON fallback produces 48GB.
- `ame doctor` on the target M3 Max machine must report 48GB and Tier T3.
