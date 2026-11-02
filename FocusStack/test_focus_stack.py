import unittest,tempfile
from pathlib import Path
import numpy as np,cv2 as cv
from PIL import Image
from focus_stack import focus_score,selection,pyramid_fuse,global_alignment,local_alignment

class FocusTests(unittest.TestCase):
 def setUp(self):
  rng=np.random.default_rng(42);a=rng.integers(30,220,(640,800,3),dtype=np.uint8);a=cv.GaussianBlur(a,(0,0),1)
  for y in range(45,640,55):cv.putText(a,'FOCUS 123 Test',(30,y),cv.FONT_HERSHEY_SIMPLEX,.8,(240,240,240),2,cv.LINE_AA)
  self.a=a
 def test_complementary_focus_beats_average(self):
  a=self.a;blur=cv.GaussianBlur(a,(0,0),3);left=a.copy();right=a.copy();left[:,400:]=blur[:,400:];right[:,:400]=blur[:,:400]
  scores=[focus_score(x) for x in [left,right]];valid=[np.ones(a.shape[:2],bool)]*2;labels=selection(scores,valid,0)
  self.assertGreater((labels[40:-40,40:350]==0).mean(),.95);self.assertGreater((labels[40:-40,450:-40]==1).mean(),.95)
  with tempfile.TemporaryDirectory() as d:
   paths=[]
   for i,im in enumerate([left,right]):p=Path(d)/f'{i}.png';Image.fromarray(im).save(p);paths.append(p)
   masks=[cv.GaussianBlur((labels==i).astype(np.float32),(0,0),2) for i in range(2)];out=pyramid_fuse(paths,masks,a.shape[:2])
  mse=lambda x:np.mean((x.astype(float)-a)**2)
  self.assertLess(mse(out),mse((left.astype(float)+right)/2)*.25)
 def test_translation_registration(self):
  a=self.a;M=np.array([[1.,0,5.4],[0,1.,-3.7]],np.float32);b=cv.warpAffine(a,M,(800,640),borderMode=cv.BORDER_REFLECT101)
  H,info=global_alignment(a,b);p=cv.perspectiveTransform(np.float32([[[400,320]]]),H)[0,0]
  self.assertLess(np.linalg.norm(p-[405.4,316.3]),.4)
 def test_local_shift_registration(self):
  a=self.a;b=cv.warpAffine(a,np.float32([[1,0,2],[0,1,-1]]),(800,640),borderMode=cv.BORDER_REFLECT101)
  result,mask,conf,info=local_alignment(a,b,np.ones(a.shape[:2],bool))
  mse=lambda x:np.mean((x[30:-30,30:-30].astype(float)-a[30:-30,30:-30])**2)
  self.assertLess(mse(result),mse(b)*.3)
 def test_invalid_sources_never_selected(self):
  s=[np.ones((80,80),np.float32),np.ones((80,80),np.float32)*5];v=[np.ones((80,80),bool),np.zeros((80,80),bool)]
  self.assertTrue(np.all(selection(s,v,0)==0))

if __name__=='__main__':unittest.main()
