#!/usr/bin/env python3
"""OSINT DARK server — static app + state API (agent <-> app bridge).

Endpoints (all prefix-tolerant: a leading /osint is stripped):
  GET  /                     index.html (no-store)
  GET  /api/health           liveness + version
  GET  /api/state            full state document
  GET  /api/dossiers         {dossiers: {subject: dossier}}
  GET  /api/dossier          {dossier: <legacy single>}
  GET  /api/runs             {runs: [...]}
  GET  /api/gh?path=/users/x GitHub proxy (uses GITHUB_TOKEN when present)
  GET  /api/crt?domain=d     crt.sh certificate-transparency proxy
  POST /api/hints            merge hint fields
  POST /api/pick             record a candidate pick (code P01.. / NONE)
  POST /api/dossiers         upsert {subject, dossier} or {subject, delete:true}
  POST /api/dossier          set legacy single dossier
  POST /api/session          store the current client session
  POST /api/run              append a run record
  DELETE /api/dossiers?subject=KEY   remove one dossier (no key = all)
"""
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state.json"
LOCK = threading.RLock()
VERSION = "3.0"
PORT = int(os.environ.get("OSINT_DARK_PORT", "18790"))
GH_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""

DEFAULT = {
    "picks": [],
    "hints": {},
    "dossier": None,
    "dossiers": {},
    "runs": [],
    "session": None,
}


def read_state():
    with LOCK:
        try:
            d = json.loads(STATE.read_text())
            if not isinstance(d, dict):
                raise ValueError("state is not an object")
        except Exception:
            d = {}
        for k, v in DEFAULT.items():
            if k not in d:
                d[k] = json.loads(json.dumps(v))
        return d


def write_state(d):
    with LOCK:
        tmp = STATE.with_name(STATE.name + ".tmp")
        tmp.write_text(json.dumps(d, indent=1))
        os.replace(tmp, STATE)


def http_json(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


class Handler(SimpleHTTPRequestHandler):
    server_version = "osint-dark/" + VERSION

    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def log_message(self, *a):
        pass

    # ---- helpers -------------------------------------------------------
    def _path(self):
        p = urllib.parse.urlparse(self.path).path
        if p.startswith("/osint"):
            p = p[len("/osint"):] or "/"
        return p

    def _query(self):
        return urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

    def end_headers(self):
        # never let a browser serve a stale build of the app
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            v = json.loads(self.rfile.read(n) or b"{}")
            return v if isinstance(v, dict) else {}
        except Exception:
            return {}

    def _static(self, p):
        self.path = p
        return super().do_GET()

    def _favicon(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" fill="#0a0a0c"/>'
            '<path d="M32 8C21 8 14 16 14 27v20c0 2 2 3 3.5 1.6L21 45l3.5 3.8c1.2 1.3 3.2 1.3 4.4 0'
            'L32 45l3.1 3.8c1.2 1.3 3.2 1.3 4.4 0L43 45l3.5 3.6C48 50 50 49 50 47V27C50 16 43 8 32 8z"'
            ' fill="none" stroke="#e5484d" stroke-width="2.5"/>'
            '<circle cx="25" cy="28" r="2.5" fill="#e5484d"/>'
            '<circle cx="39" cy="28" r="2.5" fill="#e5484d"/></svg>'
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Content-Length", str(len(svg)))
        self.end_headers()
        self.wfile.write(svg)

    # ---- GET -----------------------------------------------------------
    def do_GET(self):
        p = self._path()
        q = self._query()

        if p == "/api/health":
            return self._json({
                "ok": True,
                "version": VERSION,
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "github_token": bool(GH_TOKEN),
            })
        if p == "/api/state":
            return self._json(read_state())
        if p == "/api/dossiers":
            return self._json({"dossiers": read_state().get("dossiers", {})})
        if p == "/api/dossier":
            return self._json({"dossier": read_state().get("dossier")})
        if p == "/api/runs":
            return self._json({"runs": read_state().get("runs", [])})

        if p == "/api/gh":
            path = (q.get("path") or [""])[0]
            if not path.startswith("/"):
                return self._json({"ok": False, "error": "path must start with /"}, 400)
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "osint-dark/" + VERSION,
            }
            if GH_TOKEN:
                headers["Authorization"] = "Bearer " + GH_TOKEN
            try:
                return self._json({"ok": True, "data": http_json("https://api.github.com" + path, headers)})
            except urllib.error.HTTPError as e:
                return self._json({"ok": False, "status": e.code, "error": str(e.reason)}, 200)
            except Exception as e:
                return self._json({"ok": False, "error": str(e)}, 200)

        if p == "/api/crt":
            domain = (q.get("domain") or [""])[0].strip().lower()
            if not domain or "/" in domain:
                return self._json({"ok": False, "error": "bad domain"}, 400)
            url = "https://crt.sh/?q=%25." + urllib.parse.quote(domain) + "&output=json"
            # crt.sh is frequently overloaded: retry transient failures, but stay bounded
            last = None
            for attempt in range(2):
                try:
                    rows = http_json(url, {"User-Agent": "osint-dark/" + VERSION}, timeout=20)
                    names = set()
                    for e in rows if isinstance(rows, list) else []:
                        for n in str(e.get("name_value", "")).split("\n"):
                            n = n.replace("*.", "").strip().lower()
                            if n:
                                names.add(n)
                    return self._json({"ok": True, "domain": domain, "names": sorted(names),
                                       "attempts": attempt + 1})
                except Exception as e:
                    last = e
                    time.sleep(1.0)
            return self._json({"ok": False, "error": str(last), "domain": domain}, 200)

        if p == "/favicon.ico":
            return self._favicon()
        if p in ("/", "/index.html"):
            return self._static("/index.html")
        return self._static(p)

    # ---- POST ----------------------------------------------------------
    def do_POST(self):
        p = self._path()
        body = self._body()
        st = read_state()
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        if p == "/api/hints":
            st["hints"] = {**st.get("hints", {}), **body}
            st["hints_at"] = now
        elif p == "/api/pick":
            st.setdefault("picks", []).append({
                "code": body.get("code"),
                "handle": body.get("handle"),
                "subject": body.get("subject"),
                "at": now,
                "note": body.get("note", ""),
            })
            st["last_pick"] = body.get("code")
        elif p == "/api/dossiers":
            d = st.setdefault("dossiers", {})
            key = body.get("subject") or body.get("key") or "unnamed"
            if body.get("delete"):
                d.pop(key, None)
            else:
                dos = body.get("dossier") or body
                if isinstance(dos, dict):
                    dos.setdefault("when", now[:10])
                d[key] = dos
        elif p == "/api/dossier":
            st["dossier"] = body.get("dossier", body)
        elif p == "/api/session":
            st["session"] = body
        elif p == "/api/run":
            runs = st.setdefault("runs", [])
            runs.append({**body, "at": now})
            st["runs"] = runs[-200:]
        else:
            return self._json({"ok": False, "error": "unknown endpoint", "path": p}, 404)

        write_state(st)
        return self._json({"ok": True, "at": now})

    # ---- DELETE --------------------------------------------------------
    def do_DELETE(self):
        p = self._path()
        q = self._query()
        st = read_state()
        if p == "/api/dossiers":
            key = (q.get("subject") or [None])[0]
            if key:
                st.get("dossiers", {}).pop(key, None)
            else:
                st["dossiers"] = {}
            write_state(st)
            return self._json({"ok": True, "deleted": key or "*"})
        return self._json({"ok": False, "error": "unknown endpoint"}, 404)


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"osint-dark {VERSION} on http://127.0.0.1:{PORT}/  (github token: {'yes' if GH_TOKEN else 'no'})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
