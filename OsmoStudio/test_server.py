import unittest,tempfile,time,io,asyncio,importlib.util
from pathlib import Path
from PIL import Image
import server

class StudioTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=server.PHOTOS;server.PHOTOS=Path(self.tmp.name);server.JOBS.clear();server.PHONE['seen']=time.time();server.PHONE['proraw48']=True
 def tearDown(self):server.PHOTOS=self.old;self.tmp.cleanup()
 def test_packet_matches_proven_om3_command(self):
  # Frozen reviewed command layout plus independent CRC implementation from tested driver.
  packet=server.packet(50);self.assertEqual(packet.hex(),'551504a902040100000414320000000000040a39cd')
  with self.assertRaises(ValueError):server.packet(1500)
 def test_job_delivered_only_once(self):
  ident=server.enqueue_capture(.5,True);self.assertEqual(server.next_job()['id'],ident);self.assertEqual(server.next_job(),{})
  with self.assertRaises(ValueError):server.enqueue_capture()
 def test_offline_phone_rejected(self):
  server.PHONE['seen']=0
  with self.assertRaises(ValueError):server.enqueue_capture()
 def test_expired_job_not_captured(self):
  ident=server.enqueue_capture();server.JOBS[ident]['expires']=0;self.assertEqual(server.next_job(),{})
 def test_jpeg_rejected_in_raw_mode(self):
  ident=server.enqueue_capture();server.next_job()
  with self.assertRaises(ValueError):server.store_photo(ident,b'not a dng')
 def test_plan_and_stale_sensor(self):
  from automation import plan,Controller
  self.assertEqual(len(plan({'mode':'focus','focus_count':3,'repeat':2})),6)
  with self.assertRaises(ValueError):plan({'half_span':float('nan')})
  with self.assertRaises(ValueError):plan({'mode':'panorama','half_span':100,'step':10,'focus_count':7,'repeat':3})
  c=Controller(lambda:{},None,None,None,None)
  with self.assertRaises(RuntimeError):c.sample()
 def test_unknown_photo_rejected(self):
  with self.assertRaises(ValueError):server.store_photo('../test',b'bad')
 def test_focus_range(self):
  with self.assertRaises(ValueError):server.enqueue_capture(2)
 def test_motion_validation_without_bluetooth(self):
  for axis,degree in [('roll',5),('yaw',30),('pitch',20),('yaw',float('nan'))]:
   with self.assertRaises(ValueError):asyncio.run(server.move(axis,degree))
if __name__=='__main__':unittest.main()
