# CI workflows

The active workflows live in `.github/workflows/`. Files in this directory are
reference copies and must match the active definitions; they are not pending
installation instructions. Repository workflow changes can be pushed through
the authorized PR process.

`ci.yml` runs tools and live inventory probes, compatibility evidence checks,
the historical Fedora/bootc container builds, a runner benchmark baseline,
shell/backend/render tests, and the three required real-UNO Office jobs.
The container builds are not the selected Ubuntu ISO acceptance gate.

`iso.yml` builds the Ubuntu candidate and tests full/services/legacy against
low/mid/modern VM profiles. Its separate boot/UI acceptance contract is documented
in ADR-0026 and BUILD.md. A green Office job does not certify the installed OS.

Office setup, strict skip handling and version/JUnit artifacts are documented in
[Office development and CI](../office/BUILD.md). Ordinary CI uses read-only
repository contents permission. ISO publishing has its own scoped write permission
for diagnostic branches. P03 still includes development bootstrap, broader ISO
path coverage and other reproducibility work; these jobs do not close that stage.
