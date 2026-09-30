import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('remove_photos',Path(__file__).resolve().parents[1]/'photo-review/remove-photos.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class PhotoRemovalTests(unittest.TestCase):
 def setUp(self):
  self.current={'contactId':'example','etag':'v1','contactData':{'name':{'givenName':'Example'},'notes':'Preserve this','emails':[{'value':'person@example.com'}],'photos':[{'value':'keep','type':'icloud'},{'value':'old','type':'other'}]}}
  self.plan={'contactId':'example','etag':'v1','keepUrls':['keep'],'removeUrls':['old']}
 def test_only_selected_photo_changes(self):
  updated=module.replacement(self.current,self.plan)
  self.assertEqual(updated['photos'],[{'value':'keep','type':'icloud'}])
  for key in ['name','notes','emails']:self.assertEqual(updated[key],self.current['contactData'][key])
  self.assertEqual(len(self.current['contactData']['photos']),2)
 def test_stale_plan_fails(self):
  self.plan['etag']='old'
  with self.assertRaises(ValueError):module.replacement(self.current,self.plan)
 def test_unknown_photo_fails(self):
  self.plan['removeUrls']=['missing']
  with self.assertRaises(ValueError):module.replacement(self.current,self.plan)
 def test_cannot_remove_every_photo(self):
  self.plan.update(keepUrls=[],removeUrls=['keep','old'])
  with self.assertRaises(ValueError):module.replacement(self.current,self.plan)
 def test_cannot_keep_and_remove_same_photo(self):
  self.plan['removeUrls']=['keep','old']
  with self.assertRaises(ValueError):module.replacement(self.current,self.plan)
if __name__=='__main__':unittest.main()
