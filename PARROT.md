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

## Operational notes
- client-access state is origin-pinned: boot web with
  `--public-origin https://ghost.taild6f361.ts.net` (matches copied state)
- one agent per home at a time (owner lock); headless bundle has its OWN persona
  and does not load agent presets — use web/cli sessions for preset proofs
- `symiparrot --profile headless "<task>"` = one-shot verification vehicle

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
