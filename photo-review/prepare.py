import json,hashlib,subprocess,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
config=json.loads((ROOT.parent/'config.local.json').read_text())
SRC=ROOT.parent/'outputs/contact-photo-recovery'
rows=json.loads((SRC/'downloaded-candidates.json').read_text())
for extra in config.get('extra_candidates',[]):
 rows.append({'name':extra['name'],'file':str(SRC/extra['file']),'at':None,'action':'Export','id':None})
contacts=[]
for entry in config['contacts']:
 full=entry['fullName']
 c={k:entry[k] for k in ['key','name','fullName','protected']}
 c['candidates']=[]
 for r in sorted([x for x in rows if x['name']==full],key=lambda x:x.get('at') or '',reverse=True):
  original=Path(r['file']);digest=hashlib.sha256(original.read_bytes()).hexdigest();cid=digest[:16]
  out=ROOT/'public/images'/f'{cid}.png'
  p=subprocess.run(['sips','-s','format','png',str(original),'--out',str(out)],capture_output=True)
  info=subprocess.check_output(['sips','-g','pixelWidth','-g','pixelHeight',str(out)],text=True)
  dims=re.findall(r'pixel(?:Width|Height): (\d+)',info)
  if len(dims)!=2:raise ValueError('Cannot decode '+original.name)
  c['candidates'].append({'key':cid,'src':'/images/'+out.name,'width':int(dims[0]),'height':int(dims[1]),'at':r.get('at'),'action':r['action'],'source':'vCard export' if r['action']=='Export' else 'Contacts+ history','sourceId':r.get('id'),'sourceUrl':r.get('url'),'sha256':digest,'file':str(original),'removed':r['action']=='Removed'})
 contacts.append(c)
(ROOT/'public/data.json').write_text(json.dumps({'snapshot':config.get('snapshot'),'contacts':contacts},indent=2))
print(json.dumps({'contacts':len(contacts),'images':sum(len(c['candidates']) for c in contacts)}))
