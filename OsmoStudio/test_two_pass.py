import unittest,time,tempfile,json
from pathlib import Path
from unittest.mock import patch,AsyncMock
import server
class TwoPassTests(unittest.IsolatedAsyncioTestCase):
 async def test_first_pass_waits_without_processing(self):
  with tempfile.TemporaryDirectory() as d:
   run=dict(active=True,done=6,total=6,message='Fertig',config={'mode':'panorama','two_pass':True},pass_index=1,folder=d)
   with patch.object(server,'RUN',run),patch.object(server,'RUN_DIR',Path(d)),patch.object(server,'CLIENT',None),patch.object(server,'MOTION',{'heading':10,'sensor_session':'x'}),patch.object(server,'process_run_folder',new_callable=AsyncMock) as process:
    await server.finish_run();self.assertTrue(run['awaiting_turn']);self.assertFalse(run['active']);process.assert_not_awaited();self.assertTrue(json.loads((Path(d)/'reihe.json').read_text())['awaiting_turn'])
 async def test_continue_requires_rotation_and_same_sensor(self):
  run={'awaiting_turn':True,'turn_heading':10,'sensor_session':'x','config':{'mode':'panorama','two_pass':True}}
  m={'received':time.monotonic(),'heading':15,'sensor_session':'x'}
  with patch.object(server,'RUN',run),patch.object(server,'MOTION',m),patch.object(server,'start_run',new_callable=AsyncMock) as start:
   with self.assertRaises(ValueError):await server.continue_run()
   start.assert_not_awaited();m['heading']=-170;await server.continue_run();start.assert_awaited_once_with(run['config'],resume=True)
   m['sensor_session']='new'
   with self.assertRaises(ValueError):await server.continue_run()
if __name__=='__main__':unittest.main()
