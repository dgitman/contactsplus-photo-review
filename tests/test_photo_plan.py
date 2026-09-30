import importlib.util,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'photo-review'))
from photo_plan import build_plan
spec=importlib.util.spec_from_file_location('remove',Path(__file__).resolve().parents[1]/'photo-review/remove-photos.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PlanTests(unittest.TestCase):
 def setUp(self):
  self.contact={'liveContactId':'id','liveEtag':'v1','primaryUrl':'a','candidates':[{'key':'a','sourceUrl':'a','presence':'current'},{'key':'b','sourceUrl':'b','presence':'current'}]}
 def test_primary_only_reorders_and_preserves_fields(self):
  plan=build_plan(self.contact,{'choice':'b','removals':[]})
  current={'contactId':'id','etag':'v1','contactData':{'notes':'keep','photos':[{'value':'a','type':'one'},{'value':'b','type':'two'}]}}
  result=m.replacement(current,plan)
  self.assertEqual(result,{'notes':'keep','photos':[{'value':'b','type':'two'},{'value':'a','type':'one'}]})
 def test_remove_old_primary_requires_new_primary(self):
  with self.assertRaises(ValueError):build_plan(self.contact,{'choice':'keep','removals':['a']})
  plan=build_plan(self.contact,{'choice':'b','removals':['a']})
  self.assertEqual(plan['primaryUrl'],'b');self.assertEqual(plan['keepUrls'],['b'])
 def test_protected_contact_cannot_change(self):
  self.contact['protected']=True
  with self.assertRaises(ValueError):build_plan(self.contact,{'choice':'b'})
 def test_no_op_rejected(self):
  with self.assertRaises(ValueError):build_plan(self.contact,{'choice':'a'})
 def test_unknown_photo_rejected(self):
  with self.assertRaises(ValueError):build_plan(self.contact,{'choice':'unknown'})
 def test_missing_fresh_version_rejected(self):
  self.contact.pop('liveEtag')
  with self.assertRaises(ValueError):build_plan(self.contact,{'choice':'b'})
