# CI pipeline

`ci.yml` is the GitHub Actions workflow for this repository. It runs the `zaldros-sysprobe` unit
tests and then executes a live probe on the runner (a real systemd host), publishing the generated
service map as a build artefact.

It lives here rather than in `.github/workflows/` because the connected GitHub App is not granted the
`workflows` permission and pushes containing workflow files are rejected. To activate it, copy the
file to `.github/workflows/ci.yml` from a normal user account, or grant the app workflow permission.

## Pending change (not yet live)

`docs/ci/ci.yml` currently contains one change that is **not** in `.github/workflows/ci.yml`:
the two `podman build` steps of the `image` job retry up to 3 times (30s/60s backoff) because the
quay.io CDN periodically aborts the `fedora-bootc:42` pull with `unexpected EOF` (exit 125), which
reds out `main` for a purely network reason. Paste the file into `.github/workflows/ci.yml` from a
normal user account to activate it; everything else in the file is unchanged.
