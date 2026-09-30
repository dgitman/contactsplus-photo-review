"""Read-only reconciliation of downloaded candidates with current Contacts+ photos."""
import json,subprocess,datetime,hashlib,re
from urllib.parse import urlparse
from pathlib import Path
from urllib.request import Request,urlopen
root=Path(__file__).resolve().parent
config=json.loads((root.parent/'config.local.json').read_text())
path=root/'public/data.json';catalog=json.loads(path.read_text())
item=json.loads(subprocess.check_output(['op','item','get',config['oauth_item'],'--format','json']))
token=next(f['value'] for f in item['fields'] if f.get('id')=='credential')
queries={c['key']:c['email'] for c in config['contacts'] if c.get('email')}
summary=[]
for c in catalog['contacts']:
 if c['key'] not in queries:continue
 q=queries[c['key']]
 req=Request('https://api.contactsplus.com/api/v1/contacts.search',data=json.dumps({'searchQuery':q}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
 with urlopen(req,timeout=30) as r:data=json.load(r)
 matches=[x for x in data.get('contacts',[]) if any(e.get('value','').lower()==q for e in x.get('contactData',{}).get('emails',[]))]
 if len(matches)!=1 or data.get('cursor'):raise ValueError('Ambiguous source match')
 source_id=matches[0]['contactId']
 req=Request('https://api.contactsplus.com/api/v1/contacts.get',data=json.dumps({'contactIds':[source_id]}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
 with urlopen(req,timeout=30) as r:full=json.load(r)
 records=full.get('contacts',[])
 if len(records)!=1 or records[0]['contactId']!=source_id:raise ValueError('Full source match failed')
 current=records[0];urls={p['value'] for p in current['contactData'].get('photos',[]) if p.get('value')}
 c['liveContactId']=current['contactId'];c['livePhotoCount']=len(urls);c['checkedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 for p in c['candidates']:
  p['presence']='current' if p.get('sourceUrl') in urls else ('historical' if p.get('sourceUrl') else 'unverified')
 for url in sorted(urls-{p.get('sourceUrl') for p in c['candidates']}):
  if urlparse(url).scheme!='https' or urlparse(url).hostname!='img.contactsplus.com':continue
  cid=hashlib.sha256(url.encode()).hexdigest()[:16]
  originals=root/'private-originals';originals.mkdir(exist_ok=True)
  original=originals/cid
  with urlopen(url,timeout=30) as r:blob=r.read(20*1024*1024+1)
  if len(blob)>20*1024*1024:raise ValueError('Image too large')
  original.write_bytes(blob);out=root/'public/images'/f'{cid}.png'
  subprocess.run(['sips','-s','format','png',str(original),'--out',str(out)],check=True,capture_output=True)
  dims=re.findall(r'pixel(?:Width|Height): (\d+)',subprocess.check_output(['sips','-g','pixelWidth','-g','pixelHeight',str(out)],text=True))
  if len(dims)!=2:raise ValueError('Photo could not decode')
  c['candidates'].insert(0,{'key':cid,'src':'/images/'+out.name,'width':int(dims[0]),'height':int(dims[1]),'at':None,'action':'Current','source':'Contacts+ current photo','sourceId':current['contactId'],'sourceUrl':url,'sha256':hashlib.sha256(blob).hexdigest(),'file':str(original),'removed':False,'presence':'current'})
 summary.append({'contact':c['name'],'currentPhotos':len(urls),'downloadedCurrent':sum(p['presence']=='current' for p in c['candidates'])})
path.write_text(json.dumps(catalog,indent=2));print(json.dumps(summary))
