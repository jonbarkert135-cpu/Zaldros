# Security strategy

- **Read-only `/usr`** and image-based updates: no drift, no unnoticed system modification.
- **SELinux enforcing** by default; any policy exception is documented and reviewed.
- **Signed OS images**; update client verifies signatures; rollback to the previous known-good image.
- **Flatpak + portals** for user applications: filesystem, camera, microphone, screenshot and
  screen-share access mediated by portals, surfaced in Bedrock Settings as Windows-like permissions.
- **Disk encryption**: LUKS2 opt-in at install, TPM2-backed unlock where available (Windows-like
  "device encryption" workflow).
- **Secure Boot**: shim-based signed boot chain as a Phase 4 requirement.
- **Secrets/clipboard**: clipboard history stored in memory only, cleared on lock; password-manager
  clipboard entries honoured as sensitive (PART 2 §14).
- **No telemetry.** Diagnostics are local, opt-in, and user-readable.
- **No proprietary Microsoft binaries** in the image, ever (PART 1 §2, §11).
