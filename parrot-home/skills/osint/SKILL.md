---
name: osint
description: Full-spectrum Open Source Intelligence - question-led investigations across identity, domain, corporate, breach, geospatial and social layers with pivot discipline, verifications and a decision-grade dossier. Use for ANY task involving researching a person, company, domain, or exposing the attack surface of a target.
---

# OSINT — the full discipline

OSINT is NOT searching. It is the cycle: **Question → Plan → Collect → Process → Analyze → Report**, iterated. Every run states the QUESTION first; every finding cites its source; every conclusion survives the question *“how do I know?”*

## Phase 0 — Question & scope (never skip)

1. Write the **intelligence question** in one sentence. (“Is X’s GitHub the same person as the LinkedIn?” is a question. “Find info on X” is not.)
2. Define **scope & authority**: public/passive only? client-owned targets? credentialed? Note it in the plan.
3. Define the **product**: dossier table? attack-surface map? timeline? The report format decides the collection.

## Phase 1 — Plan the layers

Run the layer checklist; each layer lists its primary sources IN ORDER. Collect across at least 3 layers for a person, 4 for a domain.

| Layer | Primary sources (order) |
|---|---|
| Identity | sherlock → maigret → gravatar hash → name variants on GitHub |
| Email/cred | holehe → breach indexes → commit authors in public repos → MX/SPF/DKIM DNS |
| Domain/IP | crt.sh JSON → dnsenum → PTR/SOA history → ASN via bgp.tools/iptoasn → shodan (keyed) |
| Web presence | site itself → robots/sitemap/.well-known → archive.org CDX → builtwith-style fingerprints (headers, generator meta) |
| Corporate | abr.gov.au / companies registries → LinkedIn public pages → news search RSS → tender/procurement portals |
| Social | LinkedIn → YouTube → conference decks (speaker archives) → YouTube transcript search |
| Geospatial | OSM → Google/Apple Maps → street view imagery → sun calc for photo timestamps |
| Government/legal | court lists, IP registers, land titles (state-dependent), election donations |

## Phase 2 — Collect (the arsenal)

**Local (installed — verify each run):**
- `sherlock <username>` — 400+ sites username enum; always `--timeout 8`
- `recon-ng` — modules marketplace; workspaces per target: `marketplace install all`, `db insert` everything
- `theHarvester -d domain -b crtsh,baidu,hackertarget -f out.html` — emails/hosts; **the JSON sidecar matters more than HTML**
- `dnsenum domain`, `dmitry -winse domain`, `exiftool` on any harvested docs/images (GPS + author + software = pivots)
- `maltego` (GUI transforms — for graph-shaped cases) ; `photon` for crawler deep-sites

**API/no-key services (curl-able, no account):**
- crt.sh: `curl 'https://crt.sh/?q=%25.DOMAIN&output=json'` — the CT log = the attack surface
- GitHub: users/repos/commits/orgs/events endpoints — **commit author blocks are identity gold**
- archive.org: `http://web.archive.org/cdx/search/cdx?url=DOMAIN/*&output=json&limit=...` — history, old endpoints, removed staff pages
- certificate transparency, security.txt, `.well-known/`, robots, sitemap

**Keyed (drop into `~/.symi-jai-parrot/env`, zero restart):**
- `EXA_API_KEY` (semantic search), `PERPLEXITY_API_KEY` (answered search), `JAI_API_KEY` (built-in web_search)
- shodan/censys for service banners; hunter.io for pattern verification; dehashed/haveibeenpwned for breaches

**Live channels already proven on this box:** gh CLI (GitHub search 5k/h), crt.sh, archive CDX, direct fetch stack.

## Phase 3 — Process

- Normalize: every artifact → one ledger (target, layer, artifact, source-URL, timestamp, confidence)
- Dedup by canonical key (domain lowercase, handle lowercase, email)
- **Enrich**: DNS for each host; whois for each domain; exif for each doc; gravatar hash for each email
- Flag secrets-in-public: `.env`, `wp-config`, backups, `.git` dirs, exposed indexes — verify from the cached/public copy

## Phase 4 — Analyze (where OSINT becomes intelligence)

- **Pivot chains** — the multiplier. email → gravatar → breach → password pattern → other accounts. domain → CT → hosts → cert org → ASN → netblock → sibling domains. name → GitHub commit email → company → LinkedIn → role.
- **Correlate** — two sources per conclusion minimum; note confidence per claim (confirmed / probable / unverified)
- **Timeline** — order everything; gaps are findings (dormant = attack window)
- **Attack-surface lens** (when scoped): live hosts vs parked, admin portals, version banners, staff roles for phishing realism
- **Verification** — re-derive one random claim per report from its source; if it fails, the collection phase was noisy — fix and rerun

## Phase 5 — Product

The dossier, always:
1. **Question restated** + scope/authority used
2. **Executive answer** — the 5 bullets that matter
3. **Findings tables by layer**, every row sourced
4. **Pivot map** — which artifact led where (the audit trail)
5. **Gaps & next probes** — what one more hour/key would buy
6. **Confidence legend** — no unsourced sentences, ever

## Local ops notes (this box)

- `parrot-exec --install <tool>` installs Parrot’s staged tools (theHarvester worked this way)
- web_search tool needs `JAI_API_KEY` in `~/.symi-jai-parrot/env` — else use the curl channels above
- ddg/bing HTML endpoints are JS-walled/blocked from this box — use lite endpoints, RSS, or API layers; don’t repeat that discovery each run
- Remote GPU (amdgpu1 via `ssh amdgpu1`, hashcat-amd) for any bulk cracking found in breaches
