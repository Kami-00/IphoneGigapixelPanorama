import unittest
import numpy as np
from planar_stitch import project,warp_mesh
class PlanarTests(unittest.TestCase):
 def test_identity_preserves_source_pixels(self):
  a=np.random.default_rng(4).integers(0,256,(64,80,3),dtype=np.uint8)
  mesh={'grids':[np.zeros((3,3,2),np.float32)],'scale':1.,'step':40.}
  out,mask=warp_mesh(a,np.eye(3),(0,0),(80,64),mesh,0)
  np.testing.assert_array_equal(out[2:-3,2:-3],a[2:-3,2:-3])
  self.assertTrue(np.all(mask[2:-3,2:-3]==255));self.assertEqual(mask[0,0],0)
 def test_constant_mesh_shift_uses_inverse_mapping(self):
  a=np.random.default_rng(8).integers(0,256,(64,80,3),dtype=np.uint8)
  grid=np.zeros((3,3,2),np.float32);grid[:]=[3,2]
  out,mask=warp_mesh(a,np.eye(3),(0,0),(80,64),{'grids':[grid],'scale':1.,'step':40.},0)
  np.testing.assert_array_equal(out[5:50,6:70],a[3:48,3:67])
 def test_projective_normalization(self):
  p=np.array([[1,2],[3,4]],float);H=np.array([[2,0,4],[0,2,6],[0,0,2]],float)
  np.testing.assert_allclose(project(H,p),p+[2,3])
if __name__=='__main__':unittest.main()
