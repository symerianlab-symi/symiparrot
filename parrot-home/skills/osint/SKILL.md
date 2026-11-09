---
name: osint
description: Full-spectrum Open Source Intelligence — question-led investigations across identity, domain, corporate, breach, geospatial and social layers, with pivot discipline, corroboration and a decision-grade dossier. Use for ANY task researching a person, company, domain, email, phone, username, or exposing a target's attack surface.
---

# OSINT — the full discipline

## 0. What OSINT actually is

OSINT is not searching. Searching returns pages; OSINT returns **intelligence** — a
conclusion you can defend. The difference is the cycle:

**Question → Plan → Collect → Process → Analyze → Report**, iterated.

Three things make it powerful, in order:

1. **Pivot chains.** One artifact unlocks the next. An email unlocks a Gravatar
   profile, which unlocks a username, which unlocks a GitHub account, whose commit
   metadata unlocks a real name and a second email. Each hop is cheap; the chain is
   the product. A single search is worth nothing — a chain is worth everything.
2. **The public surface is far larger than people believe.** Every TLS certificate
   ever issued is logged forever. Every git commit carries an author email. Every
   corporate filing is public in most jurisdictions. Every deleted page is in an
   archive. Every breach is indexed. The target cannot delete any of it.
3. **Corroboration.** Two independent sources turn a claim into a finding. One
   source is a lead. This is what separates a dossier from a search dump.

The failure mode is collecting a lot and concluding nothing. The discipline is
concluding a little and proving all of it.

## 1. Phase 0 — Question and scope (never skip)

1. Write the **intelligence question** in one sentence. "Is X's GitHub the same
   person as the LinkedIn?" is a question. "Find info on X" is not.
2. Define **scope and authority**: public/passive only? client-owned target?
   credentialed? Write it down — it decides which techniques are legal and ethical.
3. Define the **product**: dossier? attack-surface map? timeline? The report format
   decides what you collect. Do not collect what the product does not need.
4. Note the **starting artifacts** you actually have: name, email, phone, username,
   domain, employer, photo, address. Each one is a different entry point.

## 2. Phase 1 — Plan the layers

Collect across **at least 3 layers for a person, 4 for a domain**. Each layer has an
entry point and a pivot out.

| Layer | Entry points | Pivots out to |
|---|---|---|
| Identity | name variants, username, photo | email, social, employer |
| Email | address, gravatar hash, breach index | username, phone, accounts |
| Phone | number, carrier, caller-ID apps | name, address, social |
| Domain/IP | domain, IP, ASN, cert | org, staff, infrastructure |
| Web presence | site, robots, sitemap, archive | tech stack, staff, old endpoints |
| Corporate | registry, filings, LEI | officers, addresses, subsidiaries |
| Social | platform search, archives | location, associates, behaviour |
| Geospatial | photo, map, sun position | address, time, travel |
| Breach | email, username | passwords, other accounts |
| Code | GitHub/GitLab org, commits | real names, emails, secrets |

## 3. Phase 2 — Collect: the arsenal

Everything below was **verified working on this box**. Re-verify with `command -v`
before relying on it; do not assume.

### 3.1 Local tools (installed)

```bash
export PATH="$HOME/.venvs/osint/bin:$PATH"   # holehe, maigret, socid_extractor, ipwhois

sherlock --timeout 8 <username>              # 400+ sites, fast, noisy
maigret --top 50 --timeout 8 <username>      # richer: extracts profile IDs/tags
holehe --only-used <email>                   # which sites have this email registered
theHarvester -d <domain> -b crtsh,duckduckgo -l 500
amass enum -passive -d <domain>              # passive subdomain enum
httpx -u <url> -title -tech-detect -status-code -silent
nmap -sV -Pn <host>                          # service/version banners
exiftool <file>                              # GPS, author, software, timestamps
trufflehog filesystem <path>                 # secrets in a local tree
trufflehog github --org=<org>                # secrets in an org's repos
photon -u <url>                              # crawler: URLs, emails, keys, socials
emailharvester -d <domain>                   # emails from search engines
dnsenum <domain>                             # DNS + zone-transfer attempt
dmitry -winse <domain>                       # whois, net, subdomains, email
spiderfoot -s <target> -t <type> -u passive -o json   # automation engine
recon-ng                                     # interactive; workspaces per target
maltego                                      # GUI graph transforms
```

`spiderfoot` is the best single-shot automation: `-u passive` keeps it non-intrusive,
`-o json` gives you a machine-readable ledger. Use it to seed, then pivot manually.

### 3.2 Keyless APIs (verified reachable, no account)

**Certificate Transparency — the single best domain pivot.** Every cert ever issued.

```bash
# certspotter: more reliable than crt.sh, use it first
curl -s "https://api.certspotter.com/v1/issuances?domain=$D&include_subdomains=true&expand=dns_names"

# crt.sh: richer but frequently 502 — always retry
curl -s "https://crt.sh/?q=%25.$D&output=json"
```

**Archives — deleted content, old endpoints, former staff.**

```bash
curl -s "http://web.archive.org/cdx/search/cdx?url=$D/*&output=json&collapse=urlkey&limit=500"
curl -s "https://archive.org/wayback/available?url=$U"

# Common Crawl: index names rotate every release and the service 504s often.
# Discover the current index, then retry — treat as best-effort, not a primary source.
IDX=$(curl -s "https://index.commoncrawl.org/collinfo.json" | jq -r '.[0].id')
curl -s "https://index.commoncrawl.org/$IDX-index?url=$D&output=json&limit=100"
```

**DNS / IP / routing.**

```bash
curl -s "https://dns.google/resolve?name=$D&type=MX"      # also TXT, A, NS, SOA, CAA
curl -sL "https://rdap.org/domain/$D"                     # modern whois, JSON
curl -s "http://ip-api.com/json/$IP"                      # geo, ISP, ASN
curl -s "https://ipinfo.io/$IP/json"
curl -s "https://internetdb.shodan.io/$IP"                # free: ports, hostnames, vulns, cpes
curl -s "https://api.hackertarget.com/hostsearch/?q=$D"   # subdomains
```

**Web / infrastructure.**

```bash
curl -s "https://urlscan.io/api/v1/search/?q=domain:$D&size=100"
curl -s "https://otx.alienvault.com/api/v1/indicators/domain/$D/general"
```

**Corporate / financial.**

```bash
curl -s "https://efts.sec.gov/LATEST/search-index?q=%22$NAME%22"          # US full-text filings
curl -s "https://api.gleif.org/api/v1/lei-records?filter[entity.legalName]=$NAME"
```

**Identity.**

```bash
# Gravatar: email -> profile -> linked accounts. The cheapest identity pivot there is.
H=$(printf '%s' "$EMAIL" | tr 'A-Z' 'a-z' | md5sum | cut -d' ' -f1)
curl -s "https://en.gravatar.com/$H.json"
```

### 3.3 GitHub — the highest-yield source on this box

A token is already available: `TOK=$(gh auth token)` → **5000 req/h** instead of 60.
Use it for everything GitHub.

```bash
TOK=$(gh auth token)
H="Authorization: Bearer $TOK"

# commit search by author email — real names, second emails, employer, timeline
curl -s -H "$H" "https://api.github.com/search/commits?q=author-email:$EMAIL&per_page=100"

# code search — leaked secrets, internal hostnames, config
curl -s -H "$H" "https://api.github.com/search/code?q=filename:.env+DB_PASSWORD&per_page=100"
curl -s -H "$H" "https://api.github.com/search/code?q=org:$ORG+password&per_page=100"

# identity surface
curl -s -H "$H" "https://api.github.com/users/$USER"
curl -s -H "$H" "https://api.github.com/users/$USER/orgs"
curl -s -H "$H" "https://api.github.com/users/$USER/repos?sort=pushed&per_page=100"
curl -s -H "$H" "https://api.github.com/repos/$OWNER/$REPO/commits?per_page=100"
```

Commit author blocks are identity gold: `commit.author.name`, `commit.author.email`,
`commit.author.date`. Harvest every distinct email — each is a new pivot.

### 3.4 Keyed services (NOT configured on this box)

These need keys and will return 401 today. Do not waste a run discovering that.

| Service | Buys you | Env var |
|---|---|---|
| Shodan (search) | internet-wide banners, ICS, exposed services | `SHODAN_API_KEY` |
| Censys | host/cert search | `CENSYS_API_ID/SECRET` |
| Have I Been Pwned | breach membership by email | `HIBP_API_KEY` |
| DeHashed / IntelX | breach records, passwords | paid |
| Hunter.io | email pattern verification | `HUNTER_API_KEY` |
| OpenCorporates | global company registry API | `OPENCORPORATES_API_KEY` |
| OpenSanctions | sanctions/PEP screening | `OPENSANCTIONS_API_KEY` |
| OCCRP Aleph | leaks + registries | `ALEPH_API_KEY` |
| VirusTotal | file/domain reputation | `VT_API_KEY` |
| Exa / Perplexity | semantic + answered search | `EXA_API_KEY` / `PERPLEXITY_API_KEY` |

`web_search` needs `JAI_API_KEY` in `~/.symi-jai-parrot/env`. Without it, use the
curl channels above — they cover most of what search would have given you.

## 4. Phase 3 — Process

- **One ledger.** Every artifact becomes a row: `target | layer | artifact | source
  URL | timestamp | confidence`. Nothing enters the report that is not in the ledger.
- **Canonicalise before dedup**: domains lowercase, handles lowercase, emails
  lowercase, phone numbers to E.164, IPs to dotted-quad.
- **Enrich every artifact once**: DNS for each host, RDAP for each domain, exiftool
  for each document/image, gravatar hash for each email, GitHub commit search for
  each email.
- **Flag secrets in public**: `.env`, `wp-config`, backups, `.git/`, exposed indexes,
  API keys in JS bundles. Verify from the public copy only — never authenticate with
  a found credential.

## 5. Phase 4 — Analyze: pivot chains

This is where OSINT becomes intelligence. Memorise these chains.

**Person (name only)**
```
name → name variants → GitHub user search → profile → repos → commit authors
     → distinct emails → gravatar → linked accounts → username → sherlock/maigret
     → social profiles → employer → corporate registry → officers → associates
```

**Email**
```
email → gravatar hash → profile + accounts
      → holehe → registered sites
      → GitHub commit search → real name, employer, other emails
      → breach index (keyed) → password pattern → other accounts
      → MX/SPF → mail provider → org
```

**Username**
```
username → sherlock + maigret → profiles → bio links → personal domain
         → archive of those profiles → deleted content
         → reuse on forums → posts → location/timezone/interest leaks
```

**Domain**
```
domain → certspotter/crt.sh → subdomains → httpx → live hosts + tech
       → RDAP → registrar, dates, nameservers → hosting provider
       → DNS MX/TXT → mail provider, SPF includes, verification tokens (org hints)
       → archive CDX → old endpoints, former staff pages
       → urlscan → screenshots, DOM, third-party requests
       → GitHub org/repos → staff, secrets
```

**Phone**
```
phone → E.164 → carrier/line type (keyed) → caller-ID apps → name
      → search engines → classifieds, business listings → address
```

**Company**
```
company → registry (Companies House / OpenCorporates / state SOS) → officers
        → officers → their other companies → associates
        → SEC EDGAR → filings, revenue, risk factors
        → GLEIF → LEI → parent/child entities
        → job posts → tech stack, headcount, internal tooling
        → cert transparency → infrastructure
```

**Photo**
```
photo → exiftool → GPS, camera, software, timestamp
      → reverse image search (Google/Yandex/Bing Lens, PimEyes, FaceCheck)
      → landmarks → geolocation → suncalc for time-of-day
      → archive → original higher-res version
```

### Corroboration rules

- **Two independent sources per conclusion.** Same fact from two sites that both
  scrape the same upstream is ONE source.
- **Grade every claim**: `confirmed` (2+ independent, primary) / `probable` (1 primary
  or 2 secondary) / `unverified` (single weak source) / `inference` (your reasoning).
- **Negative results are findings.** "No breach record" and "no GitHub presence" are
  reportable and often meaningful.
- **Re-derive one claim per report** from its cited source before publishing. If it
  fails, the collection was noisy — fix and rerun.

## 6. Phase 5 — Report

The dossier, always in this shape:

1. **Question restated** + scope/authority used
2. **Executive answer** — the 3–5 bullets that actually matter
3. **Findings by layer**, every row sourced, every claim graded
4. **Pivot map** — which artifact led where (the audit trail; this is what makes it
   reproducible)
5. **Gaps and next probes** — what one more hour or one more key would buy
6. **Confidence legend** — no unsourced sentence, ever

Publish to the OSINT DARK app so the operator can read it:

```bash
curl -s -X POST http://127.0.0.1:18790/api/dossiers \
  -H 'Content-Type: application/json' \
  -d '{"subject":"<key>","dossier":{ ...structured schema... }}'
```

The app renders `identity`, `contact`, `employment`, `digital`, `associates`,
`timeline`, `evidence`, `gaps`, plus `text` (markdown) and `raw`. See
`apps/osint-dark/README.md` for the full schema. Fill the structured fields — a
markdown blob alone wastes the layout.

## 7. Local ops notes (this box)

- `export PATH="$HOME/.venvs/osint/bin:$PATH"` before holehe/maigret/socid_extractor.
- `TOK=$(gh auth token)` — GitHub is authenticated as `jaysteelmind`; 5000 req/h.
- crt.sh 502s constantly. Retry 2–3×, or use certspotter first.
- Common Crawl 504s often and its index names rotate every release — discover via
  `collinfo.json`, retry, and treat it as best-effort. Wayback CDX is the reliable
  archive source.
- `ddg`/`bing` HTML endpoints are JS-walled from this box. Use the JSON APIs above,
  RSS, or `lite.duckduckgo.com`; do not rediscover this every run.
- `internetdb.shodan.io` is free and reliable; `api.shodan.io/shodan/host/{ip}` is
  rate-limited without a key — do not depend on it.
- Remote GPU for bulk cracking: `ssh amdgpu1` (ghostworker, no sudo), `hashcat-amd`,
  Radeon 8060S. SFTP to `~/workloads`.
- The OSINT DARK app is the output surface: `onsint` prints the laptop URL.

## 8. Honest gaps

Not installed, do not claim them: `subfinder`, `nuclei`, `gitleaks`, `h8mail`,
`socialscan`, `ghunt`, `toutatis`, `blackbird`, `ignorant`, `crepu`.
Substitutes that ARE installed: `amass` (subfinder), `trufflehog` (gitleaks),
`holehe` (h8mail/socialscan), `sherlock`+`maigret` (blackbird).

No breach API, no Shodan search, no Censys, no paid people-search. If a task truly
needs one, say so and name the key — do not silently produce a thinner dossier.
