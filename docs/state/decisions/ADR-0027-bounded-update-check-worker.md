# ADR-0027 — One update-check worker with exclusive connection ownership

Date: 2026-10-28. Status: ACCEPTED for the PackageKit check slice only.
Base: `b86f4a95c49ae6676a2c41cf46a53d1199becb07`. P04 remains PARTIAL.

## Problem and measured alternatives

The Settings update action called synchronous Registry/PackageKit methods on the
GUI thread. A private real dbus-daemon with a deliberately slow test service
reproduces a **257.294 ms** maximum gap in a 5 ms Qt heartbeat with a 250 ms call
deadline. This is one isolated path, not whole Settings startup or VM frame pacing.
The baseline backend is exported from the pinned base and its loaded source hash
is recorded, rather than reconstructed from memory.

| Candidate | Observation | Ownership and maintenance |
| --- | --- | --- |
| Existing synchronous client on GUI | 257.294 ms heartbeat gap | Blocks GUI; rejected for this action |
| Existing client on one worker | 5.297 ms heartbeat gap; typed timeout; native Python property dictionaries | Worker creates/uses/closes its own connection. Existing facets retained; custom protocol maintenance remains ours |
| Bundled QtDBus native async | 6.252 ms heartbeat gap; async timeout works | In PySide6 6.12.0, GetAll arguments and asVariant conversion remain QDBusArgument, not the dict the facets accept. Requires a tested decoding/facet adapter; not a drop-in replacement |

The worker and QtDBus timings both show a responsive test loop; this single sample
does **not** establish that one is faster than the other. Exact probe source and
results: `../evidence/async-updates/`. The benchmark harness is
`tools/zaldros-bench/update_check_latency.py`; comparison uses zaldros-bench's
`ui_latency_ms` metric and applies only to this injected-fault case.

QtDBus/PySide6 is a mature bundled alternative, not rejected on the old assumption
that dependencies cannot be installed in CI. Installed PySide6-Essentials metadata
declares `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`; existing Qt redistribution
notices remain applicable. No new library is added in this slice.

Unix FD comparison: the existing transport uses recv/sendall, has no Unix-FD
negotiation/SCM_RIGHTS ownership implementation, and cannot safely be assumed to
support FD-bearing APIs just because wire type `h` parses. QtDBus exposes
QDBusUnixFileDescriptor; a local descriptor wrapper is valid in the probe, but
an actual FD bus round trip remains **UNRUN**. PackageKit check needs no FD. No
portal/inhibitor/FD support is accepted by this decision; that remains a prerequisite
before selecting a general async transport or extending this worker to FD APIs.

## Decision

Use one bounded worker for refresh metadata → GetUpdates → confirmed Finished →
snapshot. Connection construction, all calls/subscriptions, and close belong to
that worker exclusively. Never move the shared GUI backend/socket into it. Keep
the backend usable without Qt; the QObject operation lives in the shell.

Expose idle/running/succeeded/failed/cancelled/timed_out, an error code/detail and
busy state. One absolute budget spans refresh and readback. Cooperative cancellation
checks socket waits every 50 ms; it stops observation and closes this private bus,
and does not promise rollback of daemon work already accepted. Late results cannot
overwrite terminal/newer states. Retry is enabled after worker cleanup; repeated
clicks do not grow a queue. Application quit requests cancellation without joining
on the GUI thread.

Connection authentication and match-rule setup/teardown retain their existing
finite transport timeouts in the worker. They can delay cleanup and re-enabling
retry after the GUI has already shown its deadline/cancelled state. The 50 ms
check applies to cancellable method reply waits, not every transport phase.

Pin transactions to the unique service owner, verify Finished/ErrorCode, observe
owner loss, and reject foreign/replacement-owner signals. A successful method
return or missing service never becomes a zero-update count. Publish only the
confirmed snapshot through queued Qt delivery; repaint only cached update rows.
Do not rebuild/query unrelated Settings pages when an async result arrives.

## Remaining gates

Other Settings/GUI reads and actions remain synchronous, including initial tree
construction and unrelated service queries. Metadata checking does not install or
upgrade packages. Transport reconnection, broader operation infrastructure, real
PackageKit/polkit/network/hardware and FD round trips still require evidence. Review
a general transport choice before another domain or FD-dependent workflow, without
rewriting all facets based only on this single-action result.
