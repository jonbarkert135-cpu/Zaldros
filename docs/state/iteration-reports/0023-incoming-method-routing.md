# Iteration 0023 — Retain incoming D-Bus methods during outgoing RPCs

Date: 2026-10-29. Base main: `ea60e7323101d6647c16f13528e7f15c066efdf3`.

**TASK** — Continue P04 after merged PR #10. Reproduce the server routing gap
observed during service activation, fix it through an actual PR and normal GitHub
merge, and retain the existing transport/Office engines. No environment or
dependency changes; no new environment Publish required.

**REPRODUCTION** — Eleven final tests against the frozen base backend on a private
real dbus-daemon: **10 failed / 1 passed**, zero skips. Incoming methods received
during an outgoing RPC are dropped by Connection._park; client dispatch drops them
too. ObjectServer bypasses the signal dispatcher and cannot drain deferred events.
Closing a connection inside a handler also exposes an unguarded socket.settimeout.
The frozen production backend matches the base byte-for-byte; only the new test
file is copied into its test directory. No activation-fixture override is needed.

**CHANGE** — Park both signals and method calls. The shared FIFO dispatcher can
deliver methods to ObjectServer, retains them during client-only dispatch, and
consumes messages parked by callback RPCs before newer socket messages. Deferred
methods precede the remaining tail if a callback raises. Synchronous call() never
executes arbitrary incoming service handlers. Preserve signal-delivery counts,
method counts, NO_REPLY_EXPECTED and dropping abandoned replies. Normalize errors
from socket.settimeout through the same DBusError path as recv. The activation
child now exports objects then uses ordinary synchronous ObjectServer.request_name,
removing the prior send_no_reply workaround without weakening activation assertions.

**DEVELOPMENT FAILURES** — A first FIFO implementation reversed two deferred calls
after a signal callback raised: **1 failed / 33 passed**. The retained ordering
assertion prompted separate FIFO deferral and restoration in finally. An interim
full run collected nine new cases: **655 passed / 63 warnings**, including one
unhandled-thread warning from the closed socket path. Add its regression and move
settimeout into the OS-error guard. A separate focused invocation used an incorrect
owner-recovery test filename and collected no tests; the corrected command is in
the receipt. These outcomes are not hidden or treated as final acceptance.

**VERIFICATION** — Final focused **36 PASS**, full shell/backend **657 PASS**
(62 existing forkpty warnings), tools **81 PASS**, all zero skips/failures.
Exact counts, log/source hashes and reproducible commands are recorded in
[local.json](../evidence/incoming-method-routing/local.json). The focused set
includes incoming RPCs, owner recovery, all seven service-file activation cases and
the bus tests. The full shell/backend and tools suites run separately. No performance
claim or replacement transport decision is made. Remote CI/ISO and final merge
results will be recorded on this iteration's PR after they complete.

**LIMITS / NEXT** — This closes the observed transport/server-routing defect, not
the entire P04 or P12 milestone. It is real private-bus protocol testing with test
services, not real PackageKit/systemd/polkit/hardware acceptance. Exported connections
still need their owner to schedule ObjectServer.process after synchronous RPCs;
parked user-space messages alone need not trigger another QSocketNotifier event.
Shell notification-server wiring, bus-daemon reconnect, initial synchronous Settings
reads, other GUI actions, and actual Unix-FD transfer remain open. Keep progressing
through measured bounded slices and normal PR delivery.
