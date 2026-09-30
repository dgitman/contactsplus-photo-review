"""Build a photo-only plan from the exact source state shown in the review."""
def build_plan(contact,decision):
    if contact.get('protected'):raise ValueError('This contact is protected from changes.')
    if not contact.get('liveContactId') or not contact.get('liveEtag'):raise ValueError('Refresh from Contacts+ before applying changes.')
    photos={p['key']:p['sourceUrl'] for p in contact['candidates'] if p.get('presence')=='current'}
    removals=decision.get('removals',[]);choice=decision.get('choice')
    if not isinstance(removals,list) or any(k not in photos for k in removals):raise ValueError('A marked photo is no longer current. Refresh and review again.')
    if choice not in {None,'keep'} and choice not in photos:raise ValueError('The chosen photo is no longer current.')
    remove=list(dict.fromkeys(photos[k] for k in removals))
    primary=photos.get(choice) if choice not in {None,'keep'} else contact.get('primaryUrl')
    if primary in remove:raise ValueError('Choose a remaining primary photo before removing the current primary.')
    keep=list(dict.fromkeys(url for url in photos.values() if url not in remove))
    if not keep:raise ValueError('At least one photo must remain.')
    if not remove and primary==contact.get('primaryUrl'):raise ValueError('No photo changes to apply.')
    return {'contactId':contact['liveContactId'],'etag':contact['liveEtag'],'keepUrls':keep,'removeUrls':remove,'primaryUrl':primary}
