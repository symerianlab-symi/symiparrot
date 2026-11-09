#!/usr/bin/env python3
"""OSINT collection orchestrator — the deep pipeline behind the OSINT DARK app.

Runs the layer-appropriate collectors for a target, emits a ledger of artifacts,
and optionally publishes a dossier to the app.

    ./collect.py domain example.com
    ./collect.py email someone@example.com --deep
    ./collect.py username torvalds
    ./collect.py name "Linus Torvalds"
    ./collect.py ip 8.8.8.8
    ./collect.py phone "+1 217 415 7211"

Every artifact is a ledger row: layer | artifact | source | when | confidence.
Nothing is reported that is not in the ledger.

Design rules:
  - stdlib only (urllib) so it runs anywhere on this box
  - every collector isolated: one failure never kills the run
  - every request has a timeout
  - --deep adds the slow local tools (sherlock, maigret, holehe)
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

UA = "osint-dark/4 (research; +https://ghost.taild6f361.ts.net/osint/)"
APP = "http://127.0.0.1:18790"
LEDGER = []
ERRORS = []
T0 = time.time()


# ---------------------------------------------------------------- ledger
_SEEN = set()


def add(layer, artifact, source, confidence="confirmed", note=""):
    artifact = str(artifact).strip()
    if not artifact:
        return
    key = (layer, artifact)
    if key in _SEEN:
        return
    _SEEN.add(key)
    LEDGER.append({
        "layer": layer,
        "artifact": artifact,
        "source": source,
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "confidence": confidence,
        "note": note,
    })


def fail(collector, err):
    ERRORS.append({"collector": collector, "error": str(err)[:200]})


# ---------------------------------------------------------------- http
def http(url, headers=None, timeout=20, data=None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def http_json(url, headers=None, timeout=20, data=None):
    return json.loads(http(url, headers, timeout, data))


def gh(path, timeout=25):
    """GitHub API with the local gh token (5000 req/h instead of 60)."""
    try:
        tok = subprocess.run(["gh", "auth", "token"], capture_output=True,
                             text=True, timeout=10).stdout.strip()
    except Exception:
        tok = ""
    h = {"Accept": "application/vnd.github+json"}
    if tok:
        h["Authorization"] = "Bearer " + tok
    return http_json("https://api.github.com" + path, h, timeout)


def retry(fn, attempts=3, delay=1.5):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last = e
            time.sleep(delay * (i + 1))
    raise last


# ---------------------------------------------------------------- collectors: domain
def ct_certspotter(d):
    try:
        rows = http_json("https://api.certspotter.com/v1/issuances"
                         f"?domain={urllib.parse.quote(d)}&include_subdomains=true&expand=dns_names")
        names = set()
        for e in rows if isinstance(rows, list) else []:
            for n in e.get("dns_names", []):
                names.add(n.replace("*.", "").strip().lower())
        for n in sorted(names):
            add("domain", n, "https://api.certspotter.com (CT log)")
        return names
    except Exception as e:
        fail("certspotter", e)
        return set()


def ct_crtsh(d):
    try:
        rows = retry(lambda: http_json(
            f"https://crt.sh/?q=%25.{urllib.parse.quote(d)}&output=json", timeout=30))
        names = set()
        for e in rows if isinstance(rows, list) else []:
            for n in str(e.get("name_value", "")).split("\n"):
                n = n.replace("*.", "").strip().lower()
                if n:
                    names.add(n)
        for n in sorted(names):
            add("domain", n, "https://crt.sh (CT log)")
        return names
    except Exception as e:
        fail("crt.sh", e)
        return set()


def dns_records(d):
    out = {}
    for t in ("A", "AAAA", "MX", "TXT", "NS", "SOA", "CAA"):
        try:
            j = http_json(f"https://dns.google/resolve?name={urllib.parse.quote(d)}&type={t}", timeout=15)
            ans = j.get("Answer") or []
            vals = [a.get("data", "") for a in ans]
            if vals:
                out[t] = vals
                for v in vals:
                    add("domain", f"{t} {v}", "https://dns.google/resolve")
        except Exception as e:
            fail(f"dns:{t}", e)
    return out


def rdap_domain(d):
    try:
        j = http_json(f"https://rdap.org/domain/{urllib.parse.quote(d)}", timeout=20)
        for ev in j.get("events", []):
            add("domain", f"{ev.get('eventAction')}: {ev.get('eventDate')}",
                "https://rdap.org/domain/" + d)
        for ns in j.get("nameservers", []):
            add("domain", "NS " + str(ns.get("ldhName", "")), "https://rdap.org/domain/" + d)
        for ent in j.get("entities", []):
            roles = ",".join(ent.get("roles", []))
            handle = ent.get("handle", "")
            if handle:
                add("corporate", f"registrant {roles}: {handle}", "https://rdap.org/domain/" + d,
                    "probable")
        return j
    except Exception as e:
        fail("rdap", e)
        return {}


def wayback(d):
    try:
        rows = retry(lambda: http_json("http://web.archive.org/cdx/search/cdx"
                                       f"?url={urllib.parse.quote(d)}/*&output=json&collapse=urlkey&limit=300",
                                       timeout=60), attempts=2, delay=2)
        urls = [r[2] for r in rows[1:]] if isinstance(rows, list) and len(rows) > 1 else []
        for u in urls[:120]:
            add("web", u, "http://web.archive.org/cdx")
        return urls
    except Exception as e:
        fail("wayback", e)
        return []


def urlscan(d):
    try:
        j = http_json(f"https://urlscan.io/api/v1/search/?q=domain:{urllib.parse.quote(d)}&size=50",
                      timeout=25)
        for r in j.get("results", [])[:30]:
            page = (r.get("page") or {}).get("url", "")
            if page:
                add("web", page, "https://urlscan.io/api/v1/search")
        return j
    except Exception as e:
        fail("urlscan", e)
        return {}


def hackertarget(d):
    try:
        txt = http(f"https://api.hackertarget.com/hostsearch/?q={urllib.parse.quote(d)}", timeout=20)
        for line in txt.strip().splitlines():
            if "," in line and "error" not in line.lower():
                host, ip = line.split(",", 1)
                add("domain", f"{host} -> {ip}", "https://api.hackertarget.com/hostsearch")
    except Exception as e:
        fail("hackertarget", e)


def github_org(d):
    base = d.split(".")[0]
    for cand in (base, d):
        try:
            j = gh(f"/orgs/{urllib.parse.quote(cand)}")
            if j.get("login"):
                add("code", f"github org: {j['login']} ({j.get('public_repos')} repos)",
                    "https://api.github.com/orgs/" + cand)
                repos = gh(f"/orgs/{urllib.parse.quote(cand)}/repos?sort=pushed&per_page=30")
                for r in repos if isinstance(repos, list) else []:
                    add("code", f"repo {r['name']} [{r.get('language') or '-'}]",
                        "https://github.com/" + cand + "/" + r["name"])
                return
        except Exception:
            continue


def collect_domain(d):
    d = d.lower().strip()
    add("domain", d, "target")
    subs = ct_certspotter(d)
    if not subs:
        subs = ct_crtsh(d)
    dns_records(d)
    rdap_domain(d)
    wayback(d)
    urlscan(d)
    hackertarget(d)
    github_org(d)
    return {"subdomains": sorted(subs)}


# ---------------------------------------------------------------- collectors: email
def gravatar(email):
    import hashlib
    h = hashlib.md5(email.strip().lower().encode()).hexdigest()
    try:
        j = http_json(f"https://en.gravatar.com/{h}.json", timeout=15)
        e0 = (j.get("entry") or [{}])[0]
        if e0:
            add("identity", f"gravatar: {e0.get('preferredUsername') or e0.get('displayName')}",
                f"https://en.gravatar.com/{h}.json")
            if e0.get("profileUrl"):
                add("social", e0["profileUrl"], "gravatar profile")
            for a in (e0.get("accounts") or []):
                add("social", f"{a.get('domain')}: {a.get('username')} ({a.get('url')})",
                    "gravatar linked account")
            return e0
    except Exception as e:
        fail("gravatar", e)
    return None


def github_commits(email):
    try:
        j = gh(f"/search/commits?q=author-email:{urllib.parse.quote(email)}&per_page=50")
        for it in (j.get("items") or [])[:30]:
            c = it.get("commit", {}).get("author", {})
            repo = (it.get("repository") or {}).get("full_name", "")
            if c.get("name"):
                add("identity", f"commit author: {c.get('name')} <{c.get('email')}>",
                    "https://api.github.com/search/commits")
            if repo:
                add("code", f"repo {repo}", "https://github.com/" + repo)
        return j.get("total_count", 0)
    except Exception as e:
        fail("github_commits", e)
        return 0


def mx_for(email):
    dom = email.split("@")[-1]
    try:
        j = http_json(f"https://dns.google/resolve?name={urllib.parse.quote(dom)}&type=MX", timeout=15)
        for a in j.get("Answer") or []:
            add("email", f"MX {a.get('data')}", "https://dns.google/resolve")
    except Exception as e:
        fail("mx", e)


def holehe(email):
    try:
        r = subprocess.run(["holehe", "--only-used", email], capture_output=True,
                           text=True, timeout=180)
        for line in r.stdout.splitlines():
            m = re.match(r"\[\+\]\s+(\S+)", line.strip())
            if m:
                add("email", f"registered on {m.group(1)}", "holehe", "probable")
    except Exception as e:
        fail("holehe", e)


def socialscan_email(email):
    try:
        r = subprocess.run(["socialscan", email], capture_output=True, text=True, timeout=120)
        for line in r.stdout.splitlines():
            if "available" in line.lower() and "not" not in line.lower():
                add("email", line.strip(), "socialscan", "probable")
    except Exception as e:
        fail("socialscan", e)


def collect_email(email, deep=False):
    email = email.strip()
    add("email", email, "target")
    gravatar(email)
    mx_for(email)
    github_commits(email)
    if deep:
        holehe(email)
        socialscan_email(email)
    return {}


# ---------------------------------------------------------------- collectors: username
def sherlock(u):
    try:
        r = subprocess.run(["sherlock", "--timeout", "8", "--print-found", u],
                           capture_output=True, text=True, timeout=240)
        for line in r.stdout.splitlines():
            m = re.match(r"\[\+\]\s+([^:]+):\s+(\S+)", line.strip())
            if m:
                add("social", f"{m.group(1).strip()}: {m.group(2)}", "sherlock", "probable")
    except Exception as e:
        fail("sherlock", e)


def maigret(u):
    try:
        r = subprocess.run(["maigret", "--top", "50", "--timeout", "8", "--no-progressbar", u],
                           capture_output=True, text=True, timeout=300)
        for line in r.stdout.splitlines():
            m = re.match(r"\[\+\]\s+(\S+):\s+(\S+)", line.strip())
            if m:
                add("social", f"{m.group(1)}: {m.group(2)}", "maigret", "probable")
    except Exception as e:
        fail("maigret", e)


def collect_username(u, deep=False):
    u = u.strip().lstrip("@")
    add("identity", f"username: {u}", "target")
    try:
        j = gh(f"/users/{urllib.parse.quote(u)}")
        if j.get("login"):
            add("identity", f"github: {j.get('name') or j['login']}", "https://api.github.com/users/" + u)
            if j.get("location"):
                add("identity", "location: " + j["location"], "github profile")
            if j.get("company"):
                add("corporate", "company: " + j["company"], "github profile")
            if j.get("blog"):
                add("web", j["blog"], "github profile")
            if j.get("twitter_username"):
                add("social", "twitter: @" + j["twitter_username"], "github profile")
    except Exception as e:
        fail("github_user", e)
    if deep:
        sherlock(u)
        maigret(u)
    return {}


# ---------------------------------------------------------------- collectors: name
def github_users(name):
    try:
        j = gh(f"/search/users?q={urllib.parse.quote(name)}&per_page=20")
        for u in (j.get("items") or [])[:15]:
            add("identity", f"github candidate: {u['login']}",
                "https://api.github.com/search/users", "probable")
    except Exception as e:
        fail("github_users", e)


def wikidata(name):
    try:
        j = http_json("https://www.wikidata.org/w/api.php?action=wbsearchentities"
                      f"&search={urllib.parse.quote(name)}&language=en&format=json&limit=5", timeout=15)
        for s in j.get("search", []):
            add("identity", f"wikidata {s.get('id')}: {s.get('label')} — {s.get('description','')}",
                "https://www.wikidata.org", "probable")
    except Exception as e:
        fail("wikidata", e)


def wikipedia(name):
    try:
        j = http_json("https://en.wikipedia.org/api/rest_v1/page/summary/"
                      + urllib.parse.quote(name.replace(" ", "_")), timeout=15)
        if j.get("title") and j.get("extract"):
            add("identity", f"wikipedia: {j['title']} — {j['extract'][:160]}",
                j.get("content_urls", {}).get("desktop", {}).get("page", "https://en.wikipedia.org"),
                "probable")
    except Exception as e:
        fail("wikipedia", e)


def collect_name(name, deep=False):
    add("identity", name, "target")
    github_users(name)
    wikidata(name)
    wikipedia(name)
    return {}


# ---------------------------------------------------------------- collectors: ip
def collect_ip(ip):
    add("domain", ip, "target")
    try:
        j = http_json(f"https://internetdb.shodan.io/{urllib.parse.quote(ip)}", timeout=15)
        for p in j.get("ports", []):
            add("domain", f"open port {p}", "https://internetdb.shodan.io")
        for h in j.get("hostnames", []):
            add("domain", "hostname " + h, "https://internetdb.shodan.io")
        for v in j.get("vulns", []):
            add("domain", "vuln " + v, "https://internetdb.shodan.io", "probable")
    except Exception as e:
        fail("internetdb", e)
    try:
        j = http_json(f"http://ip-api.com/json/{urllib.parse.quote(ip)}", timeout=15)
        if j.get("status") == "success":
            add("domain", f"geo: {j.get('city')}, {j.get('country')} ({j.get('isp')})",
                "http://ip-api.com/json")
            if j.get("as"):
                add("domain", "AS " + j["as"], "http://ip-api.com/json")
    except Exception as e:
        fail("ip-api", e)
    try:
        j = http_json(f"https://rdap.org/ip/{urllib.parse.quote(ip)}", timeout=20)
        if j.get("handle"):
            add("domain", "netblock " + j["handle"], "https://rdap.org/ip/" + ip)
    except Exception as e:
        fail("rdap_ip", e)
    return {}


# ---------------------------------------------------------------- collectors: phone
def collect_phone(phone):
    add("phone", phone, "target")
    try:
        import phonenumbers
        from phonenumbers import carrier as pn_carrier
        from phonenumbers import geocoder as pn_geocoder
        p = phonenumbers.parse(phone, None)
        if phonenumbers.is_valid_number(p):
            add("phone", "E.164 " + phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.E164),
                "phonenumbers")
            add("phone", "region " + str(phonenumbers.region_code_for_number(p)), "phonenumbers")
            add("phone", "carrier " + str(pn_carrier.name_for_number(p, "en")),
                "phonenumbers", "probable")
            add("phone", "location " + str(pn_geocoder.description_for_number(p, "en")),
                "phonenumbers", "probable")
            add("phone", "line type " + str(phonenumbers.number_type(p)), "phonenumbers")
        else:
            add("phone", "number is not valid", "phonenumbers", "unverified")
    except Exception as e:
        fail("phonenumbers", e)
    return {}


# ---------------------------------------------------------------- output
def summary():
    layers = {}
    for r in LEDGER:
        layers[r["layer"]] = layers.get(r["layer"], 0) + 1
    return {
        "artifacts": len(LEDGER),
        "layers": layers,
        "errors": len(ERRORS),
        "seconds": round(time.time() - T0, 1),
    }


def publish(subject, target_type, target):
    dossier = {
        "title": f"{subject} — {target_type} collection",
        "when": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "confidence": "probable",
        "confidence_basis": "Automated collection; corroborate before relying on any single row.",
        "summary": f"Automated {target_type} collection for {target}: "
                   f"{len(LEDGER)} artifacts across {len(set(r['layer'] for r in LEDGER))} layers.",
        "question": f"What is publicly knowable about {target} ({target_type})?",
        "scope": "public / passive only",
        "product": "artifact ledger",
        "ledger": LEDGER,
        "layers": [{"name": k, "status": "done", "artifacts": v}
                   for k, v in sorted(summary()["layers"].items())],
        "negative_findings": [f"{e['collector']}: {e['error']}" for e in ERRORS],
        "next_probes": [
            "Corroborate each artifact against a second independent source",
            "Pivot on the highest-value artifact (email, handle, or host)",
            "Add breach data if HIBP_API_KEY is configured",
        ],
        "text": f"# Automated collection — {target}\n\n"
                f"{len(LEDGER)} artifacts across {len(set(r['layer'] for r in LEDGER))} layers.\n\n"
                + "\n".join(f"- **{r['layer']}** {r['artifact']}" for r in LEDGER[:60]),
        "raw": json.dumps({"errors": ERRORS, "summary": summary()}, indent=1),
    }
    body = json.dumps({"subject": subject, "dossier": dossier}).encode()
    req = urllib.request.Request(APP + "/api/dossiers", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode()


def main():
    ap = argparse.ArgumentParser(description="OSINT collection orchestrator")
    ap.add_argument("type", choices=["domain", "email", "username", "name", "ip", "phone"])
    ap.add_argument("target")
    ap.add_argument("--deep", action="store_true", help="also run slow local tools")
    ap.add_argument("--json", action="store_true", help="emit ledger JSON")
    ap.add_argument("--publish", metavar="SUBJECT", help="publish a dossier to the app")
    a = ap.parse_args()

    fn = {"domain": collect_domain, "email": collect_email, "username": collect_username,
          "name": collect_name, "ip": collect_ip, "phone": collect_phone}[a.type]
    try:
        if a.type in ("email", "username", "name"):
            fn(a.target, a.deep)
        else:
            fn(a.target)
    except Exception as e:
        fail("main", e)

    s = summary()
    if a.json:
        print(json.dumps({"target": a.target, "type": a.type, "ledger": LEDGER,
                          "errors": ERRORS, "summary": s}, indent=1))
    else:
        print(f"\n=== {a.type}: {a.target} ===")
        for r in LEDGER:
            print(f"  [{r['layer']:<10}] {r['artifact'][:100]}")
        print(f"\n{s['artifacts']} artifacts | {s['errors']} collector errors | {s['seconds']}s")
        for e in ERRORS:
            print(f"  ! {e['collector']}: {e['error'][:80]}")

    if a.publish:
        try:
            print("\npublished:", publish(a.publish, a.type, a.target))
        except Exception as e:
            print("\npublish failed:", e)


if __name__ == "__main__":
    main()
