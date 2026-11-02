import unittest,time
from types import SimpleNamespace
from wide_capture import WideCapture
class WideTests(unittest.IsolatedAsyncioTestCase):
 def setup_controller(self):
  m={'received':time.monotonic(),'sensor_session':'same','heading':179.,'elevation':0.,'roll':-4.,'stable':True,'rate_dps':0.}
  api=SimpleNamespace(motion_snapshot=lambda:dict(m,received=time.monotonic()))
  return WideCapture(api),m
 async def test_yaw_unwrap(self):
  c,m=self.setup_controller();c.sample();m['heading']=-176.;self.assertAlmostEqual(c.sample()['unwrapped_yaw'],5)
 async def test_stop_at_first_ineffective_step(self):
  c,m=self.setup_controller();calls=[]
  async def move(axis,command):
   calls.append(command);a=c.sample();return a,a,0.
  c.move=move
  self.assertFalse(await c.target('pitch',50));self.assertEqual(len(calls),1)
 async def test_small_roll_does_not_stop_wide_capture(self):
  c,m=self.setup_controller();m['roll']=-10.;self.assertEqual((await c.stable())['roll'],-10.)
 async def test_sensor_restart_stops(self):
  c,m=self.setup_controller();c.session='before'
  with self.assertRaises(RuntimeError):c.sample()
if __name__=='__main__':unittest.main()
