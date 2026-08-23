# CI pipeline

`ci.yml` is the GitHub Actions workflow for this repository. It runs the `bedrock-sysprobe` unit
tests and then executes a live probe on the runner (a real systemd host), publishing the generated
service map as a build artefact.

It lives here rather than in `.github/workflows/` because the connected GitHub App is not granted the
`workflows` permission and pushes containing workflow files are rejected. To activate it, copy the
file to `.github/workflows/ci.yml` from a normal user account, or grant the app workflow permission.
