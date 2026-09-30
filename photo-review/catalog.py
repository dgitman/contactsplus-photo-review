"""Initialize the review cache from a configured Contacts+ contact list."""
import copy,json,os,tempfile

def configured_catalog(config,existing=None):
    existing=existing or {'contacts':[]}
    catalog=copy.deepcopy({k:v for k,v in existing.items() if k!='contacts'})
    previous={c['key']:c for c in existing['contacts']}
    contacts=[];seen=set()
    for entry in config.get('contacts',[]):
        key=entry['key']
        if key in seen:raise ValueError('Duplicate contact key in configuration')
        seen.add(key)
        old=previous.get(key,{})
        source_id=entry.get('contactId')
        if source_id and old.get('liveContactId') not in {None,source_id}:old={}
        contact=copy.deepcopy(old)
        label=entry.get('name') or entry.get('fullName') or entry.get('email') or key
        contact.update(key=key,name=label,fullName=entry.get('fullName') or contact.get('fullName') or label,protected=bool(entry.get('protected',False)))
        contact.setdefault('candidates',[])
        if source_id:contact['liveContactId']=source_id
        contacts.append(contact)
    catalog['contacts']=contacts
    return catalog

def ensure_catalog(root):
    config_path=root.parent/'config.local.json'
    if not config_path.exists():raise ValueError('Copy config.example.json to config.local.json and configure Contacts+ access first.')
    config=json.loads(config_path.read_text());path=root/'public/data.json'
    existing=json.loads(path.read_text()) if path.exists() else None
    catalog=configured_catalog(config,existing)
    path.parent.mkdir(parents=True,exist_ok=True);(path.parent/'images').mkdir(exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.catalog-')
    try:
        with os.fdopen(fd,'w') as f:json.dump(catalog,f,indent=2)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return catalog
