# Iteration 0008 — the base change is made explicit, and three real ISO build attempts

## CURRENT OBJECTIVE
Record the undeclared base change (Fedora bootc → Ubuntu 26.04) before running the ISO workflow
again, and get the pipeline past the build step so that real boot metrics become possible.

## RESEARCH
- Ubuntu package indices for `resolute` (2026-08-23): `plasma-workspace-wayland` **does not exist** —
  it is a Plasma 5 name. Plasma 6 ships the Wayland session inside `plasma-workspace`, with
  `kwin-wayland` as a separate package. The other 23 package names in the build script verify OK.
- Ubuntu publishes an official minimal rootfs for the release
  (`ubuntu-base-26.04-base-amd64.tar.gz`, 34.9 MB). Verified by download: it contains `usr/bin/apt`,
  `usr/share/keyrings/ubuntu-archive-keyring.gpg` and a deb822 `ubuntu.sources`.

## DECISION
- ADR-0009: base = Ubuntu 26.04 LTS, **status PROPOSED**, accepted only after a real build + boot.
  ADR-0001 (Fedora bootc) marked superseded, kept as the record of the option and its properties.
- Bootstrap from the official base tarball rather than debootstrap: it removes the dependency on the
  runner's debootstrap knowing a new suite. debootstrap stays as a fallback path.

## IMPLEMENTATION
- ADR-0009 written, including a cost table for the properties the move gives up.
- `ARCHITECTURE.md`, `SECURITY.md`, `SYSTEM_APPS.md`, `FEATURE_MATRIX.md`, `WINDOWS_ZALDROS_PARITY.md`,
  `PROJECT_STATE.md`, `RECOVERY.md`, `BUILD.md`, `TODO.md` corrected: SELinux → AppArmor, atomic
  updates and rollback demoted from "design" to "lost, replacement unbuilt", bootc build marked dead.
- `build/iso/build-iso.sh`: correct Plasma 6 package names, base-tarball bootstrap, build log kept.

## TEST
`iso` workflow runs #1–#5 on GitHub Actions. Tool tests: 66 passed, 2 skipped.

## RESULT
| run | commit | build full | build services | build legacy | boot job | failing step |
| --- | --- | --- | --- | --- | --- | --- |
| #1 | 41b0f29 | FAIL | FAIL | FAIL | skipped | Build ISO |
| #2 | 247ccc3 | FAIL | FAIL | FAIL | skipped | Build ISO |
| #3 | 27fcc87 | FAIL 15 s | FAIL 15 s | FAIL 87 s | skipped | Build ISO |
| #4 | 03b23bc | FAIL 111 s | FAIL 97 s | FAIL 78 s | skipped | Build ISO |
| #5 | cc1f22e | FAIL 102 s | FAIL 88 s | FAIL 79 s | skipped | Build ISO |

**No ISO has been produced, so there are no RAM, CPU, boot-time, UI or screenshot numbers.** The
`variant × profile` matrix stays empty rather than filled with estimates.

## PROBLEMS
1. Nonexistent package `plasma-workspace-wayland` (Plasma 5 name) — fixed.
2. Runner debootstrap has no script for `resolute` — fixed, then made irrelevant by the tarball path.
3. Job logs are not readable without repository admin rights, so failures were visible only as
   "step failed". Fixed by keeping the build log as an artifact and echoing its tail into the run
   summary.

## METRICS
Only build-step durations above are real measurements from this cycle. Everything else: unmeasured.

## NEXT
1. Read the failure text from run #5's summary/artifact and fix the next build error.
2. First green build → boot job runs → fill the stage-1 and stage-2 matrices with measured numbers.
3. Only then: ACCEPT / MODIFY / REJECT per variant, and one recommended architecture.
