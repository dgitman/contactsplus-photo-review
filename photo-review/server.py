"""Local-only review UI. This server has no contact-write or delete endpoint."""
import json,os,tempfile
from http.server import HTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
PUBLIC=ROOT/'public'
CHOICES=ROOT/'choices.json'
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(PUBLIC),**kw)
 def log_message(self,*a):pass
 def valid_host(self):return self.headers.get('Host')=='127.0.0.1:8766'
 def end_headers(self):
  self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'");super().end_headers()
 def send_json(self,obj,code=200):
  data=json.dumps(obj).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data)
 def do_GET(self):
  if not self.valid_host():return self.send_error(403)
  path=urlsplit(self.path).path
  if path=='/choices':return self.send_json(json.loads(CHOICES.read_text()) if CHOICES.exists() else {})
  if path not in ['/', '/index.html','/data.json'] and not (path.startswith('/images/') and Path(path).name in {p.name for p in (PUBLIC/'images').glob('*.png')}):return self.send_error(404)
  super().do_GET()
 def do_POST(self):
  if not self.valid_host() or self.headers.get('Origin')!='http://127.0.0.1:8766' or self.path!='/choices':return self.send_error(403)
  try:
   size=int(self.headers.get('Content-Length',0))
   if not 0<size<200000:raise ValueError()
   decisions=json.loads(self.rfile.read(size));catalog={c['key']:c for c in json.loads((PUBLIC/'data.json').read_text())['contacts']}
   if not isinstance(decisions,dict):raise ValueError()
   for k,d in decisions.items():
    if k not in catalog or set(d)-{'choice','removals'}:raise ValueError()
    ids={p['key'] for p in catalog[k]['candidates']}
    if d.get('choice') not in ids|{'keep',None}:raise ValueError()
    if not isinstance(d.get('removals',[]),list) or not set(d.get('removals',[]))<=ids:raise ValueError()
    if d.get('choice') in d.get('removals',[]):raise ValueError()
    current={p['key'] for p in catalog[k]['candidates'] if p.get('presence')=='current'}
    if not set(d.get('removals',[]))<=current:raise ValueError()
    if catalog[k]['protected'] and d.get('choice') not in {None,'keep'}:raise ValueError()
   fd,tmp=tempfile.mkstemp(dir=ROOT,prefix='.choices-')
   with os.fdopen(fd,'w') as f:json.dump(decisions,f,indent=2)
   os.replace(tmp,CHOICES);self.send_json({'saved':True})
  except (ValueError,TypeError,KeyError):self.send_json({'error':'Invalid choices'},400)
if __name__=='__main__':
 print('Photo review: http://127.0.0.1:8766',flush=True)
 HTTPServer(('127.0.0.1',8766),Handler).serve_forever()
