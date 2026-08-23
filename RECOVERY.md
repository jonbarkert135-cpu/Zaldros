# Recovery

Design contract for the update/rollback system (spec PART 4 §15–16, PART 5 §17). Not yet implemented
or tested — no image exists.

## Principles
- Updates are **atomic**: the running deployment is untouched until the switch. An interrupted update
  means no change at all, never a half-updated system.
- The previous deployment is always retained. A failed boot falls back to it.
- Rollback must be possible without a network connection and without a terminal.

## Intended mechanisms
| Situation | Mechanism |
| --- | --- |
| Bad update, system still boots | Update Center → "Restore previous version" (`bootc rollback`) |
| Bad update, system does not boot | Boot menu → previous deployment entry |
| Broken user configuration | Reset per-app config from Settings; user data untouched |
| Damaged filesystem | btrfs snapshot restore from the recovery environment |
| Unbootable disk | Recovery USB → reinstall image, keep `/home` |

Every one of these must be *tested by deliberately breaking a VM* before Phase 10 can close.
