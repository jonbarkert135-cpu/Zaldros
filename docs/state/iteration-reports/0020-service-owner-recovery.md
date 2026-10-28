# Iteration 0020 — P04 service-owner event recovery

Date: 2026-10-28. Base main: `05af5bc5b135897a0a156e2a9df4879d8899f956`.

**TASK** — Resume P04 through an actual GitHub PR after environment publication
restored API access. Owner authorization covers branch/push/PR/checks/normal merge;
direct-main fallback is prohibited and supersedes historical handoff instructions.

**PROBLEM / REPRODUCTION** — A named sender was resolved once at subscription time.
After service restart its new unique name failed the local filter. An unresolved
owner, and an explicitly unique sender, instead acted as wildcards when another
subscription routed the same signal onto the socket. Duplicate AddMatch calls left
a daemon rule behind after the last cancellation. Cached service presence stayed
stale after owner loss/start. Six initial private-bus regressions: five failed,
one passed (forged owner event control). The baseline uses the pinned base backend,
not a mock of the transport. Exact receipts are saved under evidence/service-owner-recovery/.

**CHANGE** — Install one daemon-authenticated NameOwnerChanged watch before resolving
well-known senders; update bindings in dispatch order. Strictly reject unresolved
or mismatched senders, including unique-name subscriptions. Invalidate presence cache
when the connection or dispatched owner generation changes. Reference-count daemon
match rules; remove the internal owner watch after the last relevant subscription,
including rollback of a failed AddMatch. Existing connection ownership stays single-threaded.
No new dependency, timer, nested event loop or global backend replacement.

**TESTS** — Eight real-private-bus regressions pass locally, including three
consecutive restarts, absent service start, unrelated sender isolation, forged owner
change, cached loss/start, balanced cancellation/resubscription, failed-subscription
cleanup, and BlueZ-shaped ObjectManager → facade → Qt bridge notification after
restart with stable subscription/notifier counts. Test services are not real BlueZ.

Local tools: **81 passed**, zero skips, 3.89s. Full shell/backend: **620 passed**,
zero skips, 62 existing forkpty warnings, 170.65s. That full run collected seven
recovery tests; the eighth failed-subscription-cleanup regression was added during
the run. The final focused suite passes all **8**, zero skips, on the same final
backend implementation. Earlier backend-only run: **160 passed** (six initial
recovery regressions). Exact commands, baseline failures and final code hashes:
[local.json](../evidence/service-owner-recovery/local.json). These overlapping
counts are not added together. Remote CI is pending.

**LIMITS / STATUS** — P04 PARTIAL. This fixes service-owner routing on a live bus,
not reconnect after dbus-daemon/transport loss. No automatic initial snapshot on
owner change; domains still refresh through their normal events/reads. Cache TTL
remains the fallback when no owner watch is active. Blocking GUI calls, deadlines,
operation lifecycle/cancellation and late-result handling remain open. This is a
correctness change; no CPU/RAM/latency improvement is claimed. No new installed-ISO,
physical-device, or Windows parity acceptance.

**NEXT** — Measure the synchronous timeout/GUI-heartbeat baseline on a pinned source,
compare a small async transport prototype with a maintained library (including FD
support/licensing), record the ADR, and implement one operation lifecycle vertically.
Continue through feature branches and actual PRs only.
