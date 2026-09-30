import importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('refresh',Path(__file__).resolve().parents[1]/'photo-review/refresh-presence.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RefreshTests(unittest.TestCase):
 def test_known_id_uses_full_record(self):
  calls=[]
  def api(method,data):
   calls.append(method);return {'contacts':[{'contactId':'id','contactData':{'photos':[]}}]}
  m.fetch_contact({'liveContactId':'id'},'person@example.com',api)
  self.assertEqual(calls,['contacts.get'])
 def test_ambiguous_email_fails(self):
  record={'contactId':'id','contactData':{'emails':[{'value':'person@example.com'}]}}
  with self.assertRaises(ValueError):m.fetch_contact({},'person@example.com',lambda *a:{'contacts':[record,record]})
 def test_missing_photo_becomes_historical_and_new_photo_downloads(self):
  c={'candidates':[{'key':'old','sourceUrl':'old','presence':'current'}]}
  downloaded=[]
  def download(url,cid):
   downloaded.append(url);return {'key':'new','sourceUrl':url,'presence':'current'}
  m.reconcile(c,{'contactId':'id','etag':'v2','contactData':{'photos':[{'value':'new'}]}},download)
  self.assertEqual(c['candidates'][0]['presence'],'historical');self.assertEqual(downloaded,['new']);self.assertEqual(c['liveEtag'],'v2')
 def test_existing_preview_preserves_key_and_is_reused(self):
  c={'candidates':[{'key':'chosen','src':'/images/cached.png','sourceUrl':'same','removalConfirmedAt':'old'}]}
  with patch.object(Path,'is_file',return_value=True):
   m.reconcile(c,{'contactId':'id','etag':'v2','contactData':{'photos':[{'value':'same'}]}},lambda *a:self.fail('Should reuse preview'))
  self.assertEqual(c['candidates'][0]['key'],'chosen');self.assertNotIn('removalConfirmedAt',c['candidates'][0])
