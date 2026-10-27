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
in ADR-0026 and BUILD.md. Its repository-push filter includes backend, apps, assets,
system configuration, provenance and the shipped log helper alongside the recipe
and shell. Tools regressions check the filter against consumed inputs. A green
Office job does not certify the installed OS or install Office frontends in it.

Office setup, strict skip handling and version/JUnit artifacts are documented in
[Office development and CI](../office/BUILD.md). Ordinary CI uses read-only
repository contents permission. ISO publishing has its own scoped write permission
for diagnostic branches on the existing repository-push/manual workflow. P03
still includes development bootstrap and other reproducibility work; these jobs
do not close that stage.
