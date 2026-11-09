# symiparrot — divergent fork of the Symi runtime

Branch `symi-parrot`. Fork of stock `@symerian/symi` 2026.12.87
(content `bee397…409` → `content-symiparrot`), home `~/.symi-jai-parrot`.

## Identity
- package `@symerian/symi-parrot` `2026.12.87-parrot.1` (native/package.json)
- carrier product block rewritten to match; launch.mjs asserts updated
- launcher `/home/ghost/bin/symiparrot` pins `SYMI_HOME`+`JAI_HOME` to the parrot home

## The five changes
1. **HTTP fetch provider** — preset rows `web-fetch-http` + `tool-web.fetch: true`.
   Full-page web reads for recon/CVEs/docs; auto-selected (single provider).
2. **30-min shell ceiling** — parrot-home `settings.yaml` `shell.timeoutMs 600000 / maxTimeoutMs 1800000`.
   Hot-reloaded; long installs/builds complete.
3. **Ruthless black-hat-engineer persona** — preset `persona` row rewritten:
   enumerate first, verify by execution, blocked-is-a-transition, third-party offense
   allowed but leave things working, operator-grade reporting.
4. **`blackhat-ops` skill** — `parrot-home/skills/blackhat-ops/SKILL.md`
   (deployed to `~/.symi-jai-parrot/skills/...`): source-triage ladder, install
   hygiene, 5-rung blocked-fallback, scoped offense, operator reporting.
5. **Search redundancy** — preset rows `web-search-exa` / `web-search-perplexity`,
   keyed from `EXA_API_KEY` / `PERPLEXITY_API_KEY`; absent keys degrade gracefully.

## Runtime patches (cordis-host-runner/lib/index.js)
- **#2 owner-trusted client packages**: `ownerTrusted = plugin.sessionId === agent.id`
   skips the panel approval for session-owned plugins (backup: `index.js.pre-parrot2`)
- **#3 durable grant registry**: snapshot `~/.symi-jai-parrot/.symi-parrot-dynamic-grants.json`,
   atomic write, validated restore in constructor, save-hooks on define/confirm/panel
   (markers `symiparrot#3`; backup: `index.js.pre-parrot3`)

## OSINT capability
- **`osint` skill** — `parrot-home/skills/osint/SKILL.md` (deployed to
  `~/.symi-jai-parrot/skills/osint/`). Rewritten against verified reality: the
  intelligence cycle, layer checklist, pivot-chain playbooks, corroboration and
  confidence grading, and an arsenal split into *installed tools*, *keyless APIs
  proven reachable*, *GitHub token exploitation*, and *keyed services not configured*.
  Every command in it was executed on this box before being written down.
- **OSINT DARK app** — `apps/osint-dark/` (deployed to `~/SYMI-WS/osint-dark/`).
  Readable output surface: structured dossier schema, per-person profile pages,
  candidates-first `P##` workflow, hints, telemetry. Served at
  `https://ghost.taild6f361.ts.net/osint/` via `onsint`.
- **Collection orchestrator** — `apps/osint-dark/collect.py`. Runs the
  layer-appropriate collectors for a target (domain / email / username / name /
  ip / phone) and emits a ledger in the app's schema. Stdlib only, every collector
  isolated, every request timed out, duplicates dropped, collector errors reported
  as negative findings. `--deep` adds the slow local tools; `--publish` writes a
  dossier straight into the app. A domain run yields 100–150 artifacts in ~35s.
- **GitHub token** — `gh auth token` gives 5000 req/h plus commit and code search;
  the skill treats this as the highest-yield source on the box.

## Operational notes
- client-access state is origin-pinned: boot web with
  `--public-origin https://ghost.taild6f361.ts.net` (matches copied state)
- one agent per home at a time (owner lock); headless bundle has its OWN persona
  and does not load agent presets — use web/cli sessions for preset proofs
- `symiparrot --profile headless "<task>"` = one-shot verification vehicle

### tmux wheel scrolling (required for the CLI)
The CLI runs in the alternate screen and enables DECSET 1007, but it does **not**
enable mouse tracking — it scrolls on Up/Down/PageUp/PageDown. tmux 3.7's default
`WheelUpPane` forwards the wheel to the app as a mouse event whenever
`alternate_on` is set, and `WheelDownPane` is not bound at all. So wheel-up was
swallowed and wheel-down did nothing.

Fix lives in `~/.config/tmux/tmux.conf` (see `ops/tmux-scroll.conf`). Route by
capability instead of by screen mode:

```
bind -n WheelUpPane   if -F -t = "#{mouse_any_flag}" "send-keys -M" "if -F -t = '#{alternate_on}' 'send-keys -t = Up' 'copy-mode -e'"
bind -n WheelDownPane if -F -t = "#{mouse_any_flag}" "send-keys -M" "if -F -t = '#{alternate_on}' 'send-keys -t = Down' 'copy-mode -e'"
bind -n S-WheelUpPane   copy-mode -e
bind -n S-WheelDownPane copy-mode -e
bind -n C-WheelUpPane   if -F -t = "#{mouse_any_flag}" "send-keys -M" "if -F -t = '#{alternate_on}' 'send-keys -t = PageUp' 'copy-mode -e'"
bind -n C-WheelDownPane if -F -t = "#{mouse_any_flag}" "send-keys -M" "if -F -t = '#{alternate_on}' 'send-keys -t = PageDown' 'copy-mode -e'"
```

1. app requested mouse tracking → forward the event (vim, less, htop)
2. app is in alternate screen → send arrow keys (Symi, pagers)
3. otherwise → tmux copy-mode (normal shell scrollback)

**One arrow key = one display line.** Sending three per notch made a single notch
jump three lines, and a fast scroll queued keys that kept processing after the
wheel stopped — the view appeared to run past where you wanted to stop. One per
notch is the finest step the app supports. Ctrl+wheel gives viewport jumps for
long transcripts.

Shift+wheel always reaches tmux scrollback, even inside a full-screen app.
Verified: Symi pane resolves to SEND-ARROWS and scrolls; a plain shell resolves
to copy-mode; a mouse-tracking app resolves to FORWARD-MOUSE.

## Credentials & keys (C1–C3 closure)
- `parrot-home/.credentials.yaml` — layer-2 store, schema-valid (parser-proven),
  hot-reloaded; currently zero entries = search providers degrade with teaching errors
- `parrot-home/env` — layer-1 env file, sourced by the launcher; drop keys here
  (`EXA_API_KEY` / `PERPLEXITY_API_KEY` / `JAI_API_KEY`) to light search
- Live recon channel NOW: `gh` CLI authenticated (5k req/h GitHub search/API)
- Empty-string values are rejected by the parser — comment out, never leave `""`

## Runtime grant state (C4)
Live grants: `~/.symi-jai-parrot/.symi-parrot-dynamic-grants.json` — runtime-mutable,
NOT tracked verbatim. Capture point-in-time: `tools/capture-grants.sh` → `state/`.
Rebuild-from-nothing: define any client plugin once; the runner recreates and
resaves the snapshot on every mutation (parrot#3). Restore a capture:
`cp state/dynamic-grants.snapshot.json ~/.symi-jai-parrot/.symi-parrot-dynamic-grants.json`
then restart the host (restore runs at constructor, validated).

## OSINT toolchain (part 2)
- System: sherlock recon-ng theHarvester dnsenum dmitry exiftool fierce photon whatweb wafw00f amass maltego - all verified running
- `~/.venvs/osint/` (py3.13 venv): holehe maigret exifread phonenumbers lxml6 + spiderfoot deps
- `/home/ghost/tools/spiderfoot` (git clone) + `/usr/local/bin/spiderfoot` wrapper; 200+ modules (`spiderfoot -M`)
- lxml note: py3.13 needs >=5 wheels; spiderfoot req pinned <5 (source-build ABI break) - relaxed in-place
- Live-fire validated: sherlock 400+ sites, holehe provider hits, maigret alt-IDs, amass passive 156 subds (vs crtsh 70), GDELT news API keyless

## OSINT DARK (app)
- `apps/osint-dark/index.html` — dark-mode agent-profile sheet; live source: `~/SYMI-WS/osint-dark/`
  (`python3 -m http.server 18790` in that dir; http://127.0.0.1:18790)
- Dark grey bg / light grey text; OSINT DARK + date header; subject avatar+identity card,
  findings table w/ source column, telemetry panel (requests/hits/wall-time)
- SAVE / DELETE (localStorage `osint-dark-saves-v1`) / RE-RUN: wrong-person | deeper | darkweb
- Engine: browser-side passive keyless chain — GitHub users→repos→commit-emails, crt.sh CT,
  gravatar hash+avatar, archive.org CDX; seeded cache renders on first load

## Access & ops (C4b)
- Laptop URL: https://ghost.taild6f361.ts.net/osint/  (tailscale serve path -> 127.0.0.1:18790)
- Persistent: ~/.config/systemd/user/osint-dark.service (enabled, Restart=on-failure)
- `onsint` (/usr/local/bin): idempotent starter+health-check, prints the laptop URL
- SSH from laptop: ssh ghost; run `onsint` any time - service and tailnet path self-heal
