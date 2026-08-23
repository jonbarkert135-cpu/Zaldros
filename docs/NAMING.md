# Naming — AUTHORITATIVE

**Official OS name: Bedrock OS** (repo: github.com/jonbarkert135-cpu/bedrock_os).

Decided by Linussi Fril, 2026-08-23. The name "RAVEN OS" appearing in the master-spec prompt parts was invented by the AI that wrote the prompt and is **wrong** — it does NOT override the owner's decision.

Mapping when reading spec parts 1–5:
- "Raven OS" / "RAVEN OS" → **Bedrock OS**
- "Raven Desktop Shell" → Bedrock Desktop Shell
- "Raven Taskbar" → Bedrock Taskbar
- "Raven Start" → Bedrock Start
- "Raven System Applications" → Bedrock System Applications
- Performance profiles: Bedrock Desktop / Bedrock Performance / Bedrock Legacy

Note: an unrelated existing project also called "Bedrock OS" (bedrocklinux.org, meta-distribution) exists — flagged to the owner for a possible naming/branding conflict; awaiting his decision. Use "Bedrock OS" until told otherwise.

## Update 2026-08-23 — suffix fixed to "OS"

Product name is **Bedrock OS**, not "Bedrock Linux": *Bedrock Linux* is an existing unrelated project
(bedrocklinux.org) and the clash would confuse users and search results. Short identifier stays
`bedrock` (`ID=bedrock` in `/etc/os-release`, package prefix, CLI prefix). See ADR-0005.
