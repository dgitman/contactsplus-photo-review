"""Local-only review UI. Reviewed photo changes require a separate preview and apply action."""
import json,os,tempfile,subprocess,sys,threading,secrets,time
from photo_plan import build_plan
from http.server import HTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
PUBLIC=ROOT/'public'
CHOICES=ROOT/'choices.json'
REFRESH_LOCK=threading.Lock()
REFRESH_STATE={'status':'idle'}
APPLY_STATE={'status':'idle'}
PLANS={}
def refresh_worker():
 global REFRESH_STATE
 try:
  result=subprocess.run([sys.executable,str(ROOT/'refresh-presence.py')],capture_output=True,text=True,timeout=240)
  if result.returncode:raise RuntimeError('Refresh failed')
  summary=json.loads(result.stdout)
  state={'status':'complete',**summary}
 except Exception:
  state={'status':'failed','message':'Could not refresh Contacts+. Check 1Password access and Contacts+ authorization, then try again. Your previous photos are still available.'}
 with REFRESH_LOCK:REFRESH_STATE=state

def begin_refresh():
 global REFRESH_STATE
 with REFRESH_LOCK:
  if APPLY_STATE['status']=='running':return {'status':'failed','message':'Wait for the photo update to finish.'}
  if REFRESH_STATE['status']!='running':
   REFRESH_STATE={'status':'running'}
   threading.Thread(target=refresh_worker,daemon=True).start()
  return dict(REFRESH_STATE)

def apply_worker(plan):
 global APPLY_STATE
 try:
  output=ROOT.parent/'outputs/photo-plans';output.mkdir(parents=True,exist_ok=True)
  path=output/(secrets.token_hex(16)+'.json');path.write_text(json.dumps(plan))
  result=subprocess.run([sys.executable,str(ROOT/'remove-photos.py'),'--plan',str(path),'--apply'],capture_output=True,text=True,timeout=180)
  if result.returncode:raise RuntimeError('Not verified')
  report=json.loads(result.stdout)
  if report.get('status')!='verified':raise RuntimeError('Not verified')
  state={'status':'complete','message':'Photo changes saved to Contacts+ and verified. Other fields are unchanged.'}
 except Exception:
  state={'status':'failed','message':'The update was not verified. Refresh from Contacts+ and review before trying again. No automatic retry was made.'}
 with REFRESH_LOCK:APPLY_STATE=state

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
  if path=='/apply-status':
   with REFRESH_LOCK:return self.send_json(dict(APPLY_STATE))
  if path=='/refresh-status':
   with REFRESH_LOCK:return self.send_json(dict(REFRESH_STATE))
  if path=='/choices':return self.send_json(json.loads(CHOICES.read_text()) if CHOICES.exists() else {})
  if path not in ['/', '/index.html','/data.json'] and not (path.startswith('/images/') and Path(path).name in {p.name for p in (PUBLIC/'images').glob('*.png')}):return self.send_error(404)
  super().do_GET()
 def do_POST(self):
  if not self.valid_host() or self.headers.get('Origin')!='http://127.0.0.1:8766' or self.path not in {'/choices','/refresh','/preview','/apply'}:return self.send_error(403)
  if self.path=='/refresh':return self.send_json(begin_refresh(),202)
  try:
   size=int(self.headers.get('Content-Length',0))
   if not 0<size<200000:raise ValueError()
   decisions=json.loads(self.rfile.read(size))
   if not isinstance(decisions,dict):raise ValueError()
   if self.path in {'/preview','/apply'}:return self.photo_action(decisions)
   catalog={c['key']:c for c in json.loads((PUBLIC/'data.json').read_text())['contacts']}
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
 def photo_action(self,payload):
  global APPLY_STATE
  with REFRESH_LOCK:
   if REFRESH_STATE['status']=='running' or APPLY_STATE['status']=='running':return self.send_json({'error':'Wait for the current operation to finish.'},409)
   if self.path=='/preview':
    try:
     catalog=json.loads((PUBLIC/'data.json').read_text())
     contact=next(c for c in catalog['contacts'] if c['key']==payload['key'])
     plan=build_plan(contact,payload['decision'])
    except (ValueError,KeyError,StopIteration,TypeError) as e:return self.send_json({'error':str(e) if isinstance(e,ValueError) else 'Invalid photo review.'},400)
    now=time.monotonic()
    for key in list(PLANS):
     if now-PLANS[key][0]>600:del PLANS[key]
    if len(PLANS)>=100:return self.send_json({'error':'Too many previews. Try again shortly.'},429)
    plan_id=secrets.token_urlsafe(24);PLANS[plan_id]=(now,plan)
    return self.send_json({'planId':plan_id,'name':contact['fullName'],'removeCount':len(plan['removeUrls']),'remainingCount':len(plan['keepUrls']),'primaryChanged':plan['primaryUrl']!=contact.get('primaryUrl')})
   entry=PLANS.pop(payload.get('planId'),None)
   if not entry or time.monotonic()-entry[0]>600:return self.send_json({'error':'Preview expired. Review the changes again.'},409)
   APPLY_STATE={'status':'running','message':'Saving to Contacts+ and verifying…'}
   threading.Thread(target=apply_worker,args=(entry[1],),daemon=True).start()
   return self.send_json(dict(APPLY_STATE),202)

if __name__=='__main__':
 print('Photo review: http://127.0.0.1:8766',flush=True)
 HTTPServer(('127.0.0.1',8766),Handler).serve_forever()
