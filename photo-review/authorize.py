"""One-time loopback OAuth setup; secrets stay in memory and 1Password."""
import json, secrets, subprocess, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT.parent/'config.local.json').read_text())
REDIRECT = 'http://127.0.0.1:8765/oauth/callback'
state = secrets.token_urlsafe(32)
item = json.loads(subprocess.check_output(['op','item','get',CONFIG['client_item'],'--format','json']))
fields = {f.get('label'):f.get('value') for f in item['fields']}
client_id, client_secret = fields['Client ID'], fields['Client Secret']
auth_url = 'https://app.contactsplus.com/oauth/authorize?' + urlencode(dict(client_id=client_id,redirect_uri=REDIRECT,scope='contacts.read',state=state))
finished = False

def status(value):
    (ROOT/'authorization-status.json').write_text(json.dumps(value,indent=2))
    print(json.dumps(value),flush=True)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def page(self,text,code=200):
        body=('<!doctype html><meta charset="utf-8"><meta name="referrer" content="no-referrer"><title>Contacts+ authorization</title><style>body{font:18px system-ui;max-width:640px;margin:12vh auto;padding:24px;line-height:1.6}</style><h1>Contacts+ authorization</h1><p>'+text+'</p>').encode()
        self.send_response(code);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer');self.end_headers();self.wfile.write(body)
    def do_GET(self):
        global finished
        if self.headers.get('Host') != '127.0.0.1:8765': return self.page('Invalid host.',400)
        p=urlparse(self.path)
        if p.path=='/start':
            self.send_response(302);self.send_header('Location',auth_url);self.send_header('Cache-Control','no-store');self.end_headers();return
        if p.path!='/oauth/callback':return self.page('Not found.',404)
        q=parse_qs(p.query)
        if not secrets.compare_digest(q.get('state',[''])[0],state):return self.page('Authorization state did not match. Please restart setup.',400)
        if 'error' in q:
            status({'status':'declined'});finished=True;return self.page('Authorization was not granted. No contacts were changed.')
        if not q.get('code'):return self.page('No authorization code received.',400)
        try:
            form=urlencode(dict(client_id=client_id,client_secret=client_secret,redirect_uri=REDIRECT,code=q['code'][0])).encode()
            req=Request('https://api.contactsplus.com/v3/oauth.exchangeAuthCode',data=form,headers={'Content-Type':'application/x-www-form-urlencoded'})
            with urlopen(req,timeout=30) as r: tokens=json.load(r)
            if not tokens.get('access_token') or not tokens.get('refresh_token'):raise ValueError('Missing tokens')
            record={'title':'Contacts+ Photo Review OAuth','category':'API_CREDENTIAL','vault':{'id':item['vault']['id']},'fields':[{'id':'credential','type':'CONCEALED','label':'credential','value':tokens['access_token']},{'id':'refresh_token','type':'CONCEALED','label':'refresh_token','value':tokens['refresh_token']},{'id':'client_item','type':'STRING','label':'client_item','value':item['id']},{'id':'redirect_uri','type':'STRING','label':'redirect_uri','value':REDIRECT},{'id':'scope','type':'STRING','label':'scope','value':tokens.get('scope','contacts.read')}]}
            result=subprocess.run(['op','item','create','--format','json'],input=json.dumps(record),text=True,capture_output=True,timeout=120)
            if result.returncode:raise ValueError('Secure storage failed')
            saved=json.loads(result.stdout)
            check=Request('https://api.contactsplus.com/api/v1/contacts.scroll',data=b'{"size":1}',headers={'Content-Type':'application/json','Authorization':'Bearer '+tokens['access_token']})
            with urlopen(check,timeout=30) as r: data=json.load(r)
            status({'status':'authorized','credentialItemId':saved['id'],'scope':tokens.get('scope','contacts.read'),'readVerified':isinstance(data.get('contacts'),list)})
            self.page('Connected. Read-only contact access is authorized and the credentials are saved in 1Password. No contacts were changed. You can close this tab.')
        except Exception as e:
            status({'status':'failed','stage':'exchange_store_or_verify','errorType':type(e).__name__})
            self.page('Setup did not finish. Return to Codex for the next step. No contacts were changed.',500)
        finished=True

server=HTTPServer(('127.0.0.1',8765),Handler);server.timeout=1
status({'status':'waiting','startUrl':'http://127.0.0.1:8765/start'})
deadline=time.monotonic()+1800
while not finished and time.monotonic()<deadline:server.handle_request()
server.server_close()
