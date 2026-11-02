"""Feature refinement anchored to measured phone orientation, rejecting repeated-pattern false matches."""
import cv2 as cv,numpy as np,math
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix

def estimate(images,metas):
 n=len(images);detector=cv.SIFT_create(nfeatures=14000,contrastThreshold=.015)
 features=[cv.detail.computeImageFeatures2(detector,im) for im in images]
 for i,f in enumerate(features):f.img_idx=i
 hs=np.radians([m['shutter_motion']['heading'] for m in metas]);es=np.radians([m['shutter_motion']['elevation'] for m in metas]);rolls=np.radians([m['shutter_motion']['roll'] for m in metas])
 vectors=np.stack([np.sin(hs)*np.cos(es),np.sin(es),np.cos(hs)*np.cos(es)],axis=1)
 mask=(vectors@vectors.T>math.cos(math.radians(70))).astype(np.uint8);np.fill_diagonal(mask,0)
 matcher=cv.detail.BestOf2NearestMatcher_create(False,.35);matches=matcher.apply2(features,mask);matcher.collectGarbage()
 f0=24/math.sqrt(36**2+24**2)*math.hypot(images[0].shape[1],images[0].shape[0]);pps=np.array([[im.shape[1]/2,im.shape[0]/2] for im in images])
 pairs=[]
 for i in range(n):
  for j in range(i+1,n):
   m=matches[i*n+j]
   if m.num_inliers<8:continue
   good=np.asarray(m.getInliers(),bool);ms=m.getMatches()
   p=np.array([features[i].keypoints[k.queryIdx].pt for k in ms])[good];q=np.array([features[j].keypoints[k.trainIdx].pt for k in ms])[good]
   if len(p)>500:
    ix=np.linspace(0,len(p)-1,500).astype(int);p=p[ix];q=q[ix]
   pairs.append((i,j,p,q))
 def rays(p,index,f,R):
  xy=(p-pps[index])/f;v=np.column_stack([xy,np.ones(len(xy))]);v/=np.linalg.norm(v,axis=1)[:,None];return v@R.T
 candidates=[]
 for hsign in [-1,1]:
  for rsign in [-1,1]:
   rs=[Rotation.from_euler('y',h*hsign).as_matrix()@Rotation.from_euler('x',e).as_matrix()@Rotation.from_euler('z',r*rsign).as_matrix() for h,e,r in zip(hs,es,rolls)]
   errors=np.concatenate([np.linalg.norm(rays(p,i,f0,rs[i])-rays(q,j,f0,rs[j]),axis=1) for i,j,p,q in pairs])
   candidates.append((np.median(errors),rs,hsign,rsign))
 _,base,hsign,rsign=min(candidates,key=lambda x:x[0]);print('Gyro-Achsen',hsign,rsign,flush=True)
 filtered=[]
 for i,j,p,q in pairs:
  errors=np.linalg.norm(rays(p,i,f0,base[i])-rays(q,j,f0,base[j]),axis=1)
  good=errors<math.radians(4)
  if good.sum()>=8:filtered.append((i,j,p[good],q[good]))
 pairs=filtered
 if not pairs:raise RuntimeError('Keine zum Gyro passenden Bildmerkmale')
 print('Gyro-geprüfte Verbindungen',[(i,j,len(p)) for i,j,p,q in pairs],flush=True)
 rows=sum(len(p)*3 for _,_,p,_ in pairs);sparsity=lil_matrix((rows+3*n+1,3*n+1),dtype=int);cursor=0
 for i,j,p,q in pairs:
  end=cursor+len(p)*3;sparsity[cursor:end,i*3:i*3+3]=1;sparsity[cursor:end,j*3:j*3+3]=1;sparsity[cursor:end,-1]=1;cursor=end
 for k in range(3*n):sparsity[rows+k,k]=1
 sparsity[-1,-1]=1
 def expand(x):return [Rotation.from_rotvec(x[i*3:i*3+3]).as_matrix()@base[i] for i in range(n)],f0*math.exp(x[-1])
 def residual(x):
  rs,f=expand(x);values=[]
  for i,j,p,q in pairs:values.append(((rays(p,i,f,rs[i])-rays(q,j,f,rs[j]))*f0).ravel())
  values.append(x[:-1]/math.radians(.35));values.append(np.array([x[-1]/.05]));return np.concatenate(values)
 bounds=(np.r_[np.full(3*n,-math.radians(4)),math.log(.85)],np.r_[np.full(3*n,math.radians(4)),math.log(1.15)])
 fit=least_squares(residual,np.zeros(3*n+1),bounds=bounds,jac_sparsity=sparsity.tocsr(),loss='soft_l1',f_scale=2,max_nfev=120,ftol=1e-5,xtol=1e-5)
 rs,f=expand(fit.x);cameras=[]
 for i,R in enumerate(rs):
  c=cv.detail.CameraParams();c.focal=f;c.aspect=1.;c.ppx=pps[i,0];c.ppy=pps[i,1];c.R=R.astype(np.float32);c.t=np.zeros((3,1),np.float64);cameras.append(c)
 print('Verfeinerung',fit.message,'Brennweite',f,'max Korrektur Grad',np.degrees(np.linalg.norm(fit.x[:-1].reshape(n,3),axis=1)).max(),flush=True)
 return cameras
