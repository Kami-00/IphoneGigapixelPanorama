import unittest,time
from automation import Controller,plan,delta

class ControlTests(unittest.IsolatedAsyncioTestCase):
 def make(self,roll=4):
  m=dict(heading=179.,elevation=0.,roll=roll,rate_dps=0.,acceleration_g=0.,stable=True,sensor_session='a')
  captured=[];finished=[];messages=[]
  async def send(axis,degrees):m[{'yaw':'heading','pitch':'elevation','roll':'roll'}[axis]]+=degrees*(-1 if axis=='roll' else 1)
  async def capture(shot,config):captured.append(dict(shot))
  async def finish():finished.append(True)
  c=Controller(lambda:dict(m,received=time.monotonic()),send,capture,lambda *args:messages.append(args),finish)
  async def pulse(axis,degree):c.sample();await send(axis,degree);return c.sample()
  c.pulse=pulse
  return c,m,captured,finished,messages
 async def test_level_learns_reversed_roll_direction(self):
  c,m,shots,finished,_=self.make();await c.run({'mode':'level'},[])
  self.assertLessEqual(abs(m['roll']),1);self.assertTrue(finished);self.assertEqual(shots,[])
 async def test_panorama_returns_and_captures(self):
  c,m,shots,finished,_=self.make(0);cfg={'mode':'panorama','half_span':5,'pitch_span':5,'focus_count':2}
  expected=plan(cfg);await c.run(cfg,expected)
  self.assertEqual(len(shots),len(expected));self.assertLessEqual(abs(delta(m['heading'],179)),1);self.assertLessEqual(abs(m['elevation']),1)
 async def test_stall_does_not_capture(self):
  c,m,shots,finished,messages=self.make()
  async def no_response(axis,degree):return c.sample()
  c.pulse=no_response;await c.run({'mode':'level'},[])
  self.assertEqual(shots,[]);self.assertTrue(finished);self.assertIn('keine verlässliche Reaktion',messages[-1][0])
 async def test_small_roll_does_not_block_capture(self):
  c,m,shots,finished,messages=self.make(-1.9)
  await c.run({'mode':'focus'},plan({'focus_count':1}))
  self.assertEqual(len(shots),1);self.assertEqual(m['roll'],-1.9)
 async def test_restart_detected(self):
  c,m,*_=self.make();c.session='a';m['sensor_session']='b'
  with self.assertRaises(RuntimeError):c.sample()
 async def test_cancel_prevents_commands(self):
  c,*_=self.make();c.abort()
  with self.assertRaises(RuntimeError):c.sample()
if __name__=='__main__':unittest.main()
