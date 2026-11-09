#!/usr/bin/env python3
"""osint-dark server: static + /api/hints + /api/pick  (writes selection state to disk for the agent)"""
import json,os,threading,time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT=Path(__file__).parent
STATE=ROOT/'state.json'

def read_state():
    try:return json.loads(STATE.read_text())
    except:return{"picks":[],"hints":{}}

class H(SimpleHTTPRequestHandler):
    def __init__(self,*a,**k):super().__init__(*a,directory=str(ROOT),**k)
    def log_message(self,*a):pass
    def _json(self,obj,code=200):
        b=json.dumps(obj).encode();self.send_response(code)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)))
        self.end_headers();self.wfile.write(b)
    def do_GET(self):
        p=self.path.split('?')[0]
        p0=self.path.split('?')[0]
        if p0.endswith('/api/dossier') and self.command=='GET':return self._json({'dossier':read_state().get('dossier')})
        if p.endswith('/api/state') or p0=='/api/state':return self._json(read_state())
        return super().do_GET()
    def do_POST(self):
        n=int(self.headers.get('Content-Length') or 0)
        body=json.loads(self.rfile.read(n) or b'{}') if n else {}
        st=read_state()
        p=self.path.split('?')[0]
        if p.endswith('/api/hints'):
            st['hints']={**st.get('hints',{}),**body};st['hints_at']=time.strftime('%Y-%m-%d %H:%M:%S')
        elif p.endswith('/api/pick'):
            st.setdefault('picks',[]).append({'code':body.get('code'),'at':time.strftime('%H:%M:%S'),'note':body.get('note','')})
            st['last_pick']=body.get('code')
        elif p.endswith('/api/dossier'):
            if 'overwrite' in body or True: st['dossier']=body.get('dossier',body)
        elif p.endswith('/api/session'):
            st['session']=body
        else:return self._json({'ok':False,'error':'unknown'},404)
        STATE.write_text(json.dumps(st,indent=1))
        self._json({'ok':True})

ThreadingHTTPServer(('127.0.0.1',18790),H).serve_forever()
