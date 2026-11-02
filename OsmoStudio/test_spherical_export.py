import unittest,tempfile,math
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation
from spherical_export import write_png,orient
class ExportTests(unittest.TestCase):
 def test_streaming_png_preserves_pixels(self):
  src=np.random.default_rng(42).integers(0,256,size=(13,29,3),dtype=np.uint8);src[:2]=0
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'test.png';write_png(p,src);got=np.array(Image.open(p));self.assertTrue(np.array_equal(got,src[:,:,::-1]))
 def test_gravity_reference_recovers_global_rotation(self):
  G=Rotation.from_euler('xyz',[25,18,-12],degrees=True).as_matrix();cams=[];metas=[]
  for h,e in [(-120,0),(-50,50),(0,-50),(60,50),(110,-30)]:
   R=Rotation.from_euler('y',h,degrees=True).as_matrix()@Rotation.from_euler('x',e,degrees=True).as_matrix()
   cams.append(SimpleNamespace(R=(G@R).astype(np.float32)))
   metas.append({'shutter_motion':{'heading':h+10,'elevation':e},'request':{'yaw':h}})
  report=orient(cams,metas);self.assertLess(report['median_sensor_difference_degrees'],.02)
if __name__=='__main__':unittest.main()
