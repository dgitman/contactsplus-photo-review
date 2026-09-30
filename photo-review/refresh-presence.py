"""Fetch full Contacts+ photo lists and cache previews for the local review UI."""
import datetime,hashlib,json,os,re,subprocess,tempfile
from urllib.parse import urlparse
from pathlib import Path
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parent

def fetch_contact(contact,email,api):
    source_id=contact.get('liveContactId')
    if not source_id:
        data=api('contacts.search',{'searchQuery':email})
        matches=[x for x in data.get('contacts',[]) if any(e.get('value','').lower()==email.lower() for e in x.get('contactData',{}).get('emails',[]))]
        if len(matches)!=1 or data.get('cursor'):raise ValueError('Ambiguous source match')
        source_id=matches[0]['contactId']
    records=api('contacts.get',{'contactIds':[source_id]}).get('contacts',[])
    if len(records)!=1 or records[0]['contactId']!=source_id:raise ValueError('Full source match failed')
    return records[0]

def reconcile(contact,current,download):
    urls={p['value'] for p in current['contactData'].get('photos',[]) if p.get('value')}
    contact['primaryUrl']=next((p['value'] for p in current['contactData'].get('photos',[]) if p.get('value')),None)
    name=current['contactData'].get('name',{})
    full=name.get('fullName') or ' '.join(filter(None,[name.get('givenName'),name.get('familyName')]))
    if full:contact['fullName']=full
    contact.update(liveContactId=current['contactId'],liveEtag=current['etag'],livePhotoCount=len(urls),checkedAt=datetime.datetime.now(datetime.timezone.utc).isoformat())
    for p in contact['candidates']:
        if p.get('sourceUrl') in urls:p.pop('removalConfirmedAt',None)
        p['presence']='current' if p.get('sourceUrl') in urls else ('historical' if p.get('sourceUrl') else 'unverified')
    for url in sorted(urls):
        existing=next((p for p in contact['candidates'] if p.get('sourceUrl')==url),None)
        if existing and (ROOT/'public'/existing['src'].lstrip('/')).is_file():continue
        candidate=download(url,current['contactId'])
        if existing:
            candidate['key']=existing['key']
            existing.update(candidate)
        else:contact['candidates'].append(candidate)

def download(url,contact_id):
    if urlparse(url).scheme!='https' or urlparse(url).hostname!='img.contactsplus.com':raise ValueError('Unsupported photo host')
    cid=hashlib.sha256(url.encode()).hexdigest()[:16]
    originals=ROOT/'private-originals';originals.mkdir(exist_ok=True)
    original=originals/cid;out=ROOT/'public/images'/f'{cid}.png';out.parent.mkdir(exist_ok=True)
    with urlopen(url,timeout=30) as r:blob=r.read(20*1024*1024+1)
    if len(blob)>20*1024*1024:raise ValueError('Image too large')
    original.write_bytes(blob)
    subprocess.run(['sips','-s','format','png',str(original),'--out',str(out)],check=True,capture_output=True,timeout=30)
    dims=re.findall(r'pixel(?:Width|Height): (\d+)',subprocess.check_output(['sips','-g','pixelWidth','-g','pixelHeight',str(out)],text=True,timeout=30))
    if len(dims)!=2:raise ValueError('Photo could not decode')
    return {'key':cid,'src':'/images/'+out.name,'width':int(dims[0]),'height':int(dims[1]),'at':None,'action':'Current','source':'Contacts+ current photo','sourceId':contact_id,'sourceUrl':url,'sha256':hashlib.sha256(blob).hexdigest(),'file':str(original),'removed':False,'presence':'current'}

def main():
    config=json.loads((ROOT.parent/'config.local.json').read_text())
    path=ROOT/'public/data.json';catalog=json.loads(path.read_text())
    item=json.loads(subprocess.check_output(['op','item','get',config['oauth_item'],'--format','json'],timeout=90))
    token=next(f['value'] for f in item['fields'] if f.get('id')=='credential')
    def api(method,data):
        req=Request('https://api.contactsplus.com/api/v1/'+method,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
        with urlopen(req,timeout=30) as r:return json.load(r)
    queries={c['key']:c['email'] for c in config['contacts'] if c.get('email')}
    count=0
    for contact in catalog['contacts']:
        if contact.get('protected') or contact['key'] not in queries:continue
        reconcile(contact,fetch_contact(contact,queries[contact['key']],api),download);count+=1
    catalog['sourceUpdatedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.catalog-')
    try:
        with os.fdopen(fd,'w') as f:json.dump(catalog,f,indent=2)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print(json.dumps({'contacts':count,'updatedAt':catalog['sourceUpdatedAt']}))
if __name__=='__main__':main()
