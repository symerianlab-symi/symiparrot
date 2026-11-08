---
name: blackhat-ops
description: Ruthless offensive-research and tooling doctrine for finding, installing, configuring and running open-source software, and for pushing through blocked downloads and hostile networks. Use for any task that needs new tooling, deep internet research, or working around blockers.
---

# Black Hat Ops — the find/verify/run loop

Ruthless means the task is DONE and VERIFIED. Every loop below ends in evidence, not optimism.

## 1. Find (source triage, in order of trust)

1. Official releases/GitHub tags — pin the exact version; verify checksum/signature when published
2. Distro packages (`apt-cache policy`, `pacman -Si`) — note the version lag before choosing
3. Maintained forks when upstream is dead — check commit activity < 12 months
4. Build-from-source as the fallback, never the default

## 2. Install

- Prefer distro-native; containers (podman) for env isolation; venv/pipx for Python; npx --yes for one-shot node CLIs
- Record every install: `dpkg -S`, `pip freeze`, `cargo install --list` — the machine must stay auditable
- Disk before download (`df -h`), never guess

## 3. Blocked is a transition

The fall-back ladder, in order:
1. Alternate official mirror / CDN
2. Different protocol (https ↔ git:// ↔ ssh) or a release tarball instead of clone
3. Proxy via a reachable peer (`ssh -D`, tailscale node with egress)
4. Build dependency graph by hand from source
5. Write the minimal tool yourself — 20 lines of correct beats 2000 unavailable

## 4. Configure & run

- Config under version control or clearly dated backups (`file.orig-YYYYMMDD`)
- One change at a time; verify after each; roll back the moment behavior diverges from expectation
- Long builds: nohup + job id, poll — never a 10-minute foreground hang

## 5. Third-party systems (when the task calls for offense)

- Passive recon before active: certificates, DNS, public docs, shodan-style ranges
- Scope first: targets, owners, windows. Ruthless ≠ careless — leave systems working
- Test credentials only where authorization exists or is implied by the task
- Every probe logged: `tee` scan output; results must be re-readable
- Standard kit on this box: nmap, masscan, wireshark/tshark, hydra, hashcat-amd (remote on amdgpu1), sqlmap, burpsuite, aircrack-ng

## 6. Report like an operator

- What was done (commands that mattered, not every keystroke)
- What was VERIFIED (with the check that proved it)
- What remains / what was blocked and the next probe
