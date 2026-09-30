import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'photo-review'))
spec=importlib.util.spec_from_file_location('review_server',Path(__file__).resolve().parents[1]/'photo-review/server.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ServerPlanTests(unittest.TestCase):
 def test_preview_does_not_write_and_apply_is_single_use(self):
  with tempfile.TemporaryDirectory() as tmp:
   public=Path(tmp);public.joinpath('data.json').write_text(json.dumps({'contacts':[{'key':'example','fullName':'Example','liveContactId':'id','liveEtag':'v1','primaryUrl':'a','candidates':[{'key':'a','sourceUrl':'a','presence':'current'},{'key':'b','sourceUrl':'b','presence':'current'}]}]}))
   h=m.Handler.__new__(m.Handler);out=[];h.send_json=lambda data,code=200:out.append((data,code));h.path='/preview'
   m.PLANS.clear();m.REFRESH_STATE={'status':'idle'};m.APPLY_STATE={'status':'idle'}
   with patch.object(m,'PUBLIC',public),patch.object(m.threading,'Thread') as thread:
    h.photo_action({'key':'example','decision':{'choice':'b','removals':['a']}})
    thread.assert_not_called();plan_id=out[-1][0]['planId'];self.assertEqual(out[-1][0]['removeCount'],1)
    h.path='/apply';h.photo_action({'planId':plan_id});self.assertEqual(out[-1][1],202);thread.assert_called_once()
    m.APPLY_STATE={'status':'complete'}
    h.photo_action({'planId':plan_id});self.assertEqual(out[-1][1],409)
 def test_update_blocks_refresh(self):
  m.APPLY_STATE={'status':'running'}
  try:
   with patch.object(m.threading,'Thread') as thread:
    self.assertEqual(m.begin_refresh()['status'],'failed');thread.assert_not_called()
  finally:m.APPLY_STATE={'status':'idle'}
