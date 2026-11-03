import unittest,time
import server
from automation import plan

class TeleTests(unittest.TestCase):
 def setUp(self):
  self.old=dict(server.PHONE);self.jobs=dict(server.JOBS);server.JOBS.clear()
 def tearDown(self):
  server.PHONE.clear();server.PHONE.update(self.old);server.JOBS.clear();server.JOBS.update(self.jobs)
 def camera(self):return dict(camera='tele',physical_camera='AVCaptureDeviceTypeBuiltInTelephotoCamera',zoom_factor=1,raw_ready=True,portrait_hfov=20.,portrait_vfov=26.)
 def test_exactly_nine_single_photos(self):
  c=server.tele_grid_config(self.camera());shots=plan(c)
  self.assertEqual(len(shots),9);self.assertEqual(len({(s['yaw'],s['pitch']) for s in shots}),9)
  self.assertEqual(c['half_span'],15);self.assertEqual(c['pitch_span'],19.5)
  self.assertTrue(all(s['focus']==-1 and s['repeat']==0 for s in shots))
 def test_digital_crop_is_rejected(self):
  c=self.camera();c['physical_camera']='AVCaptureDeviceTypeBuiltInWideAngleCamera'
  with self.assertRaises(ValueError):server.tele_grid_config(c)
  c=self.camera();c['zoom_factor']=3
  with self.assertRaises(ValueError):server.tele_grid_config(c)
 def test_invalid_fov_and_overlap(self):
  for fov in [float('nan'),0,100]:
   c=self.camera();c['portrait_hfov']=fov
   with self.assertRaises(ValueError):server.tele_grid_config(c)
  with self.assertRaises(ValueError):server.tele_grid_config(self.camera(),.05)
 def test_tele_capture_has_distinct_format(self):
  server.PHONE.update(self.camera(),seen=time.time(),proraw48=False)
  ident=server.enqueue_capture(context={'camera':'tele'})
  self.assertEqual(server.JOBS[ident]['format'],'proraw12tele')
  server.JOBS.clear()
  with self.assertRaises(ValueError):server.enqueue_capture()
if __name__=='__main__':unittest.main()
