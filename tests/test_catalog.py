import sys,tempfile,json,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'photo-review'))
from catalog import configured_catalog,ensure_catalog
class CatalogTests(unittest.TestCase):
 def test_first_run_needs_no_contact_export(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'photo-review'
   (Path(tmp)/'config.local.json').write_text(json.dumps({'contacts':[{'key':'example','contactId':'source-id','protected':True}]}))
   result=ensure_catalog(root)
   self.assertEqual(result['contacts'][0]['liveContactId'],'source-id')
   self.assertTrue((root/'public/images').is_dir())
   self.assertEqual(result['contacts'][0]['candidates'],[])
 def test_existing_cache_preserved(self):
  old={'contacts':[{'key':'example','liveContactId':'id','candidates':[{'key':'photo'}]}]}
  result=configured_catalog({'contacts':[{'key':'example','contactId':'id'}]},old)
  self.assertEqual(result['contacts'][0]['candidates'],[{'key':'photo'}])
 def test_changed_source_does_not_reuse_another_persons_photos(self):
  old={'contacts':[{'key':'example','liveContactId':'old','candidates':[{'key':'photo'}]}]}
  result=configured_catalog({'contacts':[{'key':'example','contactId':'new'}]},old)
  self.assertEqual(result['contacts'][0]['candidates'],[])
