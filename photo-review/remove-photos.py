"""Apply an explicit photo-only plan through Contacts+. Dry-run by default."""
import argparse,copy,datetime,json,subprocess
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parent.parent

def replacement(current,plan):
    if current['contactId']!=plan['contactId'] or current.get('etag')!=plan['etag']:
        raise ValueError('Contact changed; review a fresh plan before retrying')
    photos=current['contactData'].get('photos',[])
    urls=[p['value'] for p in photos]
    remove=plan['removeUrls'];keep=plan['keepUrls']
    if not remove or len(set(remove))!=len(remove) or set(remove)&set(keep):raise ValueError('Invalid removal plan')
    if set(urls)!=set(remove)|set(keep) or not keep:raise ValueError('Photo set differs or no photo would remain')
    data=copy.deepcopy(current['contactData']);data['photos']=[p for p in photos if p['value'] not in remove]
    return data

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan',required=True);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    plan=json.loads(Path(args.plan).read_text());config=json.loads((ROOT/'config.local.json').read_text())
    item_id=config['write_oauth_item'] if args.apply else config['oauth_item']
    item=json.loads(subprocess.check_output(['op','item','get',item_id,'--format','json'],timeout=90))
    fields={f['id']:f.get('value') for f in item['fields']};token=fields['credential']
    if args.apply and 'contacts.write' not in fields.get('scope','').split(','):raise ValueError('Write authorization missing')
    def api(method,data):
        req=Request('https://api.contactsplus.com/api/v1/'+method,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
        with urlopen(req,timeout=30) as r:return json.load(r)
    def fetch():
        records=api('contacts.get',{'contactIds':[plan['contactId']]}).get('contacts',[])
        if len(records)!=1:raise ValueError('Expected exactly one contact')
        return records[0]
    current=fetch();data=replacement(current,plan)
    backup=ROOT/'outputs/photo-removals'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup.mkdir(parents=True)
    (backup/'before.json').write_text(json.dumps(current,indent=2));(backup/'plan.json').write_text(json.dumps(plan,indent=2))
    if not args.apply:
        print(json.dumps({'status':'dry_run','removeCount':len(plan['removeUrls']),'keepCount':len(data['photos'])}));return
    request={'contact':{'contactId':current['contactId'],'etag':current['etag'],'contactData':data},'resolveConflicts':False}
    if current.get('teamId'):request['teamId']=current['teamId']
    error=None
    try:api('contacts.update',request)
    except Exception as e:error=type(e).__name__
    after=fetch();(backup/'after.json').write_text(json.dumps(after,indent=2))
    wanted=[p['value'] for p in data['photos']];actual=[p['value'] for p in after['contactData'].get('photos',[])]
    before_other={k:v for k,v in current['contactData'].items() if k!='photos'}
    after_other={k:v for k,v in after['contactData'].items() if k!='photos'}
    verified=actual==wanted and before_other==after_other and current.get('contactMetadata')==after.get('contactMetadata')
    report={'status':'verified' if verified else 'not_verified','removedCount':len(plan['removeUrls']) if verified else None,'remainingPhotoCount':len(actual),'otherFieldsUnchanged':before_other==after_other,'metadataUnchanged':current.get('contactMetadata')==after.get('contactMetadata'),'requestError':error}
    (backup/'result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
    if not verified:raise SystemExit(1)
if __name__=='__main__':main()
