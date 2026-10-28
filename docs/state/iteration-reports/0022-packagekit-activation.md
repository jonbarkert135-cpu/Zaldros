# Iteration 0022 — PackageKit activation and transaction creator identity

Date: 2026-10-28. Base main: `32512e27b136917bc8144d9490e90d155e7a29a5`.

**TASK** — Continue P04 from merged PR #9 through a feature branch, actual PR,
passing checks and normal GitHub merge. No environment configuration/dependency change.

**REPRODUCTION** — Seven new real-private-bus tests launch a PackageKit-shaped
Python child via a D-Bus service file. On pinned base production Bus/Updates code:
**5 failed / 2 passed**. GetNameOwner before the first method cannot start an
installed inactive service. Separately, replace the owner during CreateTransaction
but keep its old connection alive: the old code misses the owner-loss event before
its subscription and incorrectly reports successful refresh on that old owner.
The baseline uses the final activation fixture and only adds the optional private
service-directory harness to the frozen backend; its production source hashes
remain exactly those of the pinned base.

**CHANGE** — Send CreateTransaction to the well-known destination, allowing normal
D-Bus activation. Preserve method-return sender metadata through Result/Bus.call/
call_one and pin subsequent calls/signals to that creator's unique connection.
After installing the owner-loss subscription, verify that the same connection
still owns PackageKit. A replacement or missing identity fails before RefreshCache.
Preserve the existing absolute deadline/cancellation callback while activation is
pending. A later check can activate the service again after it exits.

**LOCAL** — Focused activation/update-check/bus suite **35 passed**, zero skips,
5.89s. Full shell/backend **646 passed**, zero skips, 62 existing forkpty warnings,
149.60s. Tools **81 passed**, zero skips, 6.43s. Activation tests cover initially
inactive service, missing service, child exit 23, deadline/cancel during delayed
startup and successful retry, a new process after termination, and owner replacement
before the create reply. No new latency/CPU/RAM claim; PR #9's benchmark is historical.
Exact commands, source hashes and baseline failures:
[local.json](../evidence/update-activation/local.json).

**HARNESS FAILURE / ROOT CAUSE** — The first child used MockSystem's synchronous
RequestName while an activating caller already had CreateTransaction queued.
Temporary tracing observed Connection._park receiving that METHOD_CALL (type 1),
which the client-only parking path drops. Initial fixed-production run: 2 failed /
33 passed. Export the test objects first and announce RequestName without waiting
for a reply, then let ObjectServer.process receive the queued request. All original
activation/readback assertions remain. Generic server-side incoming-method routing
during synchronous client calls is a separate observed transport/P12 gate; it is
not declared fixed by this helper bootstrap.

**LIMITS / NEXT** — P04 PARTIAL. This is real dbus-daemon activation and child
process restart with a test service, not real PackageKit/systemd/polkit/network
integration, installation/upgrades, bus-daemon recovery or hardware acceptance.
Existing finite authentication/match-rule setup and teardown timeouts still apply
on the private worker. Next: measured initial Settings reads/transport recovery;
verify real PackageKit integration and the observed server-routing gap separately.
Final CI/ISO results are recorded on this iteration's PR after verification.
