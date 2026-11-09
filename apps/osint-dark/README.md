# OSINT DARK

The **control plane** for OSINT runs on this machine. The agent is the brain and
does the collection; this app is where the operator reads the result and directs
the next move.

Three surfaces:

- **PEOPLE** — roster of every subject with a published dossier
- **PROFILE** — the deep dossier: coverage matrix, identity, contact, employment,
  digital footprint, associates, timeline, evidence, pivot chains, the full
  ledger, negative findings, gaps, and next probes the operator can queue
- **LEDGER** — every artifact across every subject, filterable by subject, layer,
  confidence, and free text
- **RUN** — candidates-first workflow: the agent proposes coded candidates
  (`P01`…), the operator picks one and hands the code back in chat

Access: `https://ghost.taild6f361.ts.net/osint/` (or `onsint` from any shell).

## Architecture

```
browser (index.html)  ──►  server.py (127.0.0.1:18790)  ──►  state.json
        │                        │
        │                        └──► api.github.com   (token from env)
        │                        └──► crt.sh           (retry-bounded)
        └── localStorage: sessions, candidates, hints
```

`state.json` is the agent ↔ app bridge. The agent publishes dossiers into it; the
app reads them and writes picks, hints, and queued probes back. The agent reads
`GET /api/runs` to see what the operator asked for.

## Collection orchestrator

`collect.py` is the deep pipeline behind the app. It runs the layer-appropriate
collectors for a target and emits a ledger — the same shape the app renders.

```bash
export PATH="$HOME/.venvs/osint/bin:$PATH"
cd ~/SYMI-WS/osint-dark

./collect.py domain   example.com          # CT, DNS, RDAP, archive, urlscan, GitHub org
./collect.py email    someone@example.com  # gravatar, MX, GitHub commit search
./collect.py username torvalds             # GitHub profile (+ sherlock/maigret with --deep)
./collect.py name     "Linus Torvalds"     # GitHub users, Wikidata, Wikipedia
./collect.py ip       8.8.8.8              # ports, hostnames, geo, ASN, netblock
./collect.py phone    "+1 217 415 7211"    # E.164, region, carrier, line type
```

| Flag | Effect |
|---|---|
| `--deep` | add slow local tools (sherlock, maigret, holehe, socialscan) |
| `--json` | emit the ledger as JSON |
| `--publish "Subject"` | publish a dossier straight into the app |

Design rules: stdlib only, every collector isolated so one failure never kills the
run, every request timed out, duplicates dropped, and collector errors reported as
negative findings rather than hidden. A domain run typically yields 100–150
artifacts in ~35s.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness, version, whether a GitHub token is loaded |
| GET | `/api/state` | full state document |
| GET | `/api/dossiers` | `{dossiers: {subject: dossier}}` |
| GET | `/api/dossier` | legacy single dossier |
| GET | `/api/runs` | run/re-run requests |
| GET | `/api/gh?path=/users/x` | GitHub proxy (uses `GITHUB_TOKEN`) |
| GET | `/api/crt?domain=d` | crt.sh certificate-transparency proxy |
| POST | `/api/hints` | merge hint fields |
| POST | `/api/pick` | record a pick (`P01`… or `NONE`) |
| POST | `/api/dossiers` | upsert `{subject, dossier}` or `{subject, delete:true}` |
| POST | `/api/session` | store the current client session |
| POST | `/api/run` | append a run record |
| DELETE | `/api/dossiers?subject=KEY` | remove one dossier (no key = all) |

All paths are prefix-tolerant: a leading `/osint` is stripped, so the app works
both directly and behind the Tailscale `serve` path proxy.

### Publishing a dossier (agent side)

```sh
curl -s -X POST http://127.0.0.1:18790/api/dossiers \
  -H 'Content-Type: application/json' \
  -d '{"subject":"Jane Doe","dossier":{ …see schema below… }}'
```

The profile page renders a **structured schema**. Every field is optional — a
dossier with only `title`/`when`/`text`/`raw` still renders (legacy fallback),
it just shows fewer sections.

```jsonc
{
  "title": "Jane Doe — Role, Org",       // roster label
  "when": "2026-11-09",
  "confidence": "high",                   // high | medium | low
  "confidence_basis": "why this rating",
  "summary": "one-line verdict shown under the header",

  // Phase 0 — the app shows these in a block under the header
  "question": "the intelligence question, one sentence",
  "scope": "public/passive only | client-owned | credentialed",
  "product": "dossier | attack-surface map | timeline",

  "role": "Founder & CEO",
  "org": "ACME",
  "location": "Dallas, TX",

  "identity": {
    "full_name": "Jane Doe",
    "aliases": ["J. Doe"],
    "handles": [{"platform":"linkedin","handle":"janedoe","url":"https://…","confidence":"high"}],
    "dob": null, "nationality": null, "photo": null
  },

  "contact": {
    "emails":    [{"value":"jane@acme.com","type":"work","confidence":"high","source":"acme.com","note":""}],
    "phones":    [{"value":"+1 555 0100","type":"mobile","confidence":"low","source":"hint","note":""}],
    "addresses": [{"value":"Dallas, TX 75206","type":"HQ","confidence":"high","source":"terms"}]
  },

  "employment": [{"org":"ACME","role":"CEO","start":"","end":"present","confidence":"high","source":"…"}],

  "digital": {
    "accounts": [{"platform":"linkedin","handle":"janedoe","url":"https://…","confidence":"high"}],
    "domains":  [{"domain":"acme.com","mx":"Microsoft 365","hosting":"Azure","subdomains":65,"confidence":"high"}],
    "repos":    [{"name":"acme-api","url":"https://…","lang":"Go"}]
  },

  "associates": [{"name":"John Roe","role":"CTO","relation":"co-founder","confidence":"high","link":"https://…"}],

  "timeline": [{"date":"2026-11-09","event":"what happened","source":"where"}],
  "evidence": [{"claim":"…","source":"…","url":"…","confidence":"high","type":"primary"}],
  "gaps":     ["no date of birth", "no direct email"],

  // Phase 3 — the ledger. One row per artifact. This is the audit trail.
  "ledger": [
    {"layer":"email","artifact":"jane@acme.com","source":"https://acme.com","at":"2026-11-09","confidence":"confirmed"}
  ],

  // Phase 4 — pivot chains. Which artifact led where.
  "pivots": [
    {"from":"email","via":"gravatar","to":"profile","to_value":"janedoe","confidence":"confirmed"}
  ],

  // Phase 1 — layer coverage. status: done | partial | gap
  "layers": [
    {"name":"identity","status":"done","artifacts":6},
    {"name":"breach","status":"gap","artifacts":0}
  ],

  // Negative results are findings — report them.
  "negative_findings": ["no breach record", "no GitHub presence"],

  // Phase 5 — what one more hour or key would buy. Operator can queue these.
  "next_probes": ["Texas SOS entity lookup", "carrier lookup on +1 555…"],

  "text": "# OSINT DOSSIER\n\n## VERDICT\n…markdown narrative…",
  "raw":  "source trail / evidence blob"
}
```

Layer names the app expects: `identity`, `email`, `phone`, `domain`, `web`,
`corporate`, `social`, `geospatial`, `breach`, `code`. Confidence values:
`confirmed`, `probable`, `unverified`, `inference`.

Rendering rules:

| Field | Where it appears |
|---|---|
| `question`, `scope`, `product` | block under the profile header |
| `summary` | under the profile header |
| `layers` | LAYER COVERAGE matrix (10 chips, derived from `ledger` if absent) |
| `identity`, `contact`, `employment`, `digital`, `associates` | their own cards, one row per entry |
| `timeline` | vertical timeline with red event dots |
| `evidence` | EVIDENCE card, one row per claim |
| `pivots` | PIVOT CHAINS card, one block per hop |
| `ledger` | LEDGER card (per subject) and the global LEDGER tab |
| `negative_findings` | NEGATIVE FINDINGS card |
| `gaps` | OPEN GAPS card and the CONFIDENCE card |
| `next_probes` | NEXT PROBES card, each with a QUEUE button |
| `text` | AGENT DOSSIER card, rendered as markdown |
| `raw` | RAW LAYER card, verbatim |

**Clickable rows.** Any row carrying extra detail expands in place to show it —
handles, emails, phones, addresses, employment, domains, associates, and every
evidence row. Emails and phones get a COPY button; associates with a `link`
that matches another published subject get an OPEN DOSSIER button; evidence
rows with a `url` get an "open source" link. The confidence chip in the header
expands to show `confidence_basis`. RAW JSON is behind a toggle.

**Control plane.** Every `next_probes` entry has a QUEUE button. Pressing it
POSTs `{subject, mode:"probe", probe}` to `/api/run`, which the agent reads from
`GET /api/runs`. That is how the operator directs the investigation.

Any image URLs found in `text` or `raw` are rendered in an IMAGES card.

### Colour discipline

Red (`#e5484d`) is **structural only** — borders, accent bars, dots, the ghost
mark, the redline sweep, active states, and the code chips' borders. It is
never used for body text, headings, or links, because red-on-dark is hard to
read. Body text is `#c2c2c8`, headings `#e9e9ee`, links `#d4d4da` with a faint
underline that turns red on hover.

## Configuration

`~/.config/osint-dark/env` (mode 600), loaded by the systemd unit:

```
GITHUB_TOKEN=gho_…
```

Without a token GitHub allows 60 requests/hour, which is not enough for a
single deep dive. With one it is 5000/hour.

## Service

```sh
systemctl --user status osint-dark
systemctl --user restart osint-dark
journalctl --user -u osint-dark -f
```

Unit: `~/.config/systemd/user/osint-dark.service`, enabled at boot.

## Tests

Headless Chromium driver, no dependencies beyond `chromium` and node ≥ 22:

```sh
cd test
node cdp.mjs "https://ghost.taild6f361.ts.net/osint/" final.js   # 29 assertions
node net.mjs "https://ghost.taild6f361.ts.net/osint/"           # failed requests
```

`cdp.mjs` loads the page, runs a script in it, and reports console errors and
uncaught exceptions. `final.js` asserts every control: boot, roster, profile,
back, tabs, hints, new session, none-match, save, ghost visibility, md5,
markdown rendering, and the error strip.

## Rebuild notes (v3)

v2 was broken in ways that made the app look dead. Fixed in v3:

| Defect | Cause | Fix |
|---|---|---|
| Profile never opened | `#view-profile` had inline `display:none`; `show()` toggled a class with no CSS rule | `.view{display:none}` / `.view.on{display:block}`, no inline styles |
| RUN tab dead | same | same |
| `renderAll()` crashed | `dossierPaint()` wrote to `#dossier`, which did not exist | run-view dossier host is `#runDossier` |
| NEW SESSION bricked the app | it replaced `#main`, destroying all three views | views are static; only their contents are repainted |
| NONE MATCH dead | no handler bound | wired to `noneMatch()` |
| Ghost logo never appeared | `#ghost` existed only inside an unused template string | ghost is real DOM, shown when the roster is empty |
| Gravatar always threw | `crypto.subtle.digest("MD5")` is unsupported by WebCrypto | pure-JS MD5 (verified against known vectors) |
| Dossier rendered as one line | `.replace(/\\n/g,'<br>')` matched a literal backslash-n | real markdown renderer |
| Stale builds | no cache headers | `Cache-Control: no-store` on every response |
| Deep dive hung for minutes | crt.sh retried 3× at 45 s, serially | 2 attempts at 20 s, both domains in parallel |
| Deep dive burned the rate limit | commits fetched for all 30 repos | capped to the 8 most recently pushed |
| `since ?` on every candidate | GitHub's search endpoint omits `created_at` | read it from the per-user call |
