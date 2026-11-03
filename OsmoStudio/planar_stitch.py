"""Feature-optimized planar mosaic for close, approximately flat subjects.
This is deliberately separate from the rotation-only spherical panorama path.
"""
from pathlib import Path
import json,math,time
import cv2 as cv
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix

def project(H,p):
 q=np.column_stack((p,np.ones(len(p))))@H.T
 return q[:,:2]/q[:,2,None]

def fit_transforms(images):
 scale=min(1.,math.sqrt(2_000_000/max(im.shape[0]*im.shape[1] for im in images)))
 small=[cv.resize(im,None,fx=scale,fy=scale,interpolation=cv.INTER_AREA) for im in images]
 sift=cv.SIFT_create(nfeatures=18000,contrastThreshold=.018)
 feats=[sift.detectAndCompute(cv.cvtColor(im,cv.COLOR_BGR2GRAY),None) for im in small]
 pairs=[];bf=cv.BFMatcher();n=len(images)
 for i in range(n):
  for j in range(i+1,n):
   if feats[i][1] is None or feats[j][1] is None:continue
   good=[m for m,k in bf.knnMatch(feats[i][1],feats[j][1],k=2) if m.distance<.68*k.distance]
   if len(good)<25:continue
   a=np.float64([feats[i][0][m.queryIdx].pt for m in good]);b=np.float64([feats[j][0][m.trainIdx].pt for m in good])
   H,valid=cv.findHomography(a,b,cv.USAC_MAGSAC,1.3,maxIters=10000,confidence=.999)
   if H is None:continue
   a,b=a[valid.ravel()>0],b[valid.ravel()>0]
   if len(a)<25:continue
   # A credible overlap must have features distributed over a substantial region.
   if min(np.ptp(a[:,0])*np.ptp(a[:,1]),np.ptp(b[:,0])*np.ptp(b[:,1]))<25000:continue
   if len(a)>600:
    ix=np.linspace(0,len(a)-1,600).astype(int);a,b=a[ix],b[ix]
   pairs.append((i,j,a,b,H))
 anchor=1 if n>1 else 0;trans={anchor:np.eye(3)}
 while len(trans)<n:
  edges=[p for p in pairs if (p[0] in trans)!=(p[1] in trans)]
  if not edges:raise RuntimeError('Nicht alle Bilder durch verlässliche flächige Bildmerkmale verbunden')
  i,j,a,b,H=max(edges,key=lambda p:len(p[2]))
  if i in trans:trans[j]=trans[i]@np.linalg.inv(H)
  else:trans[i]=trans[j]@H
 # Repeated logos can produce internally consistent but entirely wrong pair matches.
 rejected=[];accepted=[]
 for pair in pairs:
  i,j,a,b,H=pair;train=np.arange(len(a))%4!=0
  error=np.median(np.linalg.norm(project(trans[i],a[train])-project(trans[j],b[train]),axis=1))
  if error>20:rejected.append([i+1,j+1,float(error)])
  else:accepted.append(pair)
 pairs=accepted
 print('Verworfene falsche Verbindungen',rejected,flush=True)
 S=np.diag([1000.,1000.,1.]);ids=[i for i in range(n) if i!=anchor]
 initial=[np.linalg.inv(S)@trans[i]@S for i in ids]
 x0=np.concatenate([(H/H[2,2]).ravel()[:8] for H in initial])
 def expand(x):
  result={anchor:np.eye(3)}
  for k,i in enumerate(ids):result[i]=S@np.r_[x[k*8:k*8+8],1.].reshape(3,3)@np.linalg.inv(S)
  return result
 train=[];held=[]
 for i,j,a,b,H in pairs:
  test=np.arange(len(a))%4==0
  train.append((i,j,a[~test],b[~test]));held.append((i,j,a[test],b[test]))
 rows=sum(len(a)*2 for _,_,a,_ in train);sparse=lil_matrix((rows,len(x0)),dtype=int);offset=0
 for i,j,a,b in train:
  for v in (i,j):
   if v in ids:k=ids.index(v);sparse[offset:offset+2*len(a),k*8:k*8+8]=1
  offset+=2*len(a)
 def residual(x,data=train):
  T=expand(x);return np.concatenate([(project(T[i],a)-project(T[j],b)).ravel() for i,j,a,b in data])
 fit=least_squares(residual,x0,jac_sparsity=sparse.tocsr(),loss='soft_l1',f_scale=.5,max_nfev=100,ftol=1e-8,xtol=1e-8)
 T=expand(fit.x);report=[]
 for i,j,a,b in held:
  err=np.linalg.norm(project(T[i],a)-project(T[j],b),axis=1)/scale
  report.append(dict(pair=[i+1,j+1],heldout_points=len(a),median_native_pixels=float(np.median(err)),p90_native_pixels=float(np.percentile(err,90))))
 print('Unbenutzte Kontrollpunkte:',json.dumps(report),flush=True)
 fullscale=np.diag([scale,scale,1.]);Hs=[np.linalg.inv(fullscale)@T[i]@fullscale for i in range(n)]
 return Hs,{'registration_scale':scale,'anchor_index':anchor,'heldout':report,'optimizer_success':bool(fit.success),'optimizer_message':fit.message,'transforms':[H.tolist() for H in Hs], 'rejected_pairs':rejected},(train,held,small,T,scale,anchor)

def refine_mesh(data):
 from scipy.sparse import coo_matrix,vstack,diags
 from scipy.sparse.linalg import lsqr
 train,held,small,T,scale,anchor=data
 step=180.;shapes=[(math.ceil(im.shape[0]/step)+1,math.ceil(im.shape[1]/step)+1) for im in small]
 offsets={};count=0
 for i,(h,w) in enumerate(shapes):
  if i!=anchor:offsets[i]=count;count+=h*w
 def basis(i,p):
  h,w=shapes[i];u=np.clip(p[:,0]/step,0,w-1.0001);v=np.clip(p[:,1]/step,0,h-1.0001);x=u.astype(int);y=v.astype(int);a=u-x;b=v-y
  return np.stack([y*w+x,y*w+x+1,(y+1)*w+x,(y+1)*w+x+1],axis=1),np.stack([(1-a)*(1-b),a*(1-b),(1-a)*b,a*b],axis=1)
 rows=[];cols=[];vals=[];targets=[];offset=0
 for i,j,a,b in train:
  n=len(a);targets.append(project(T[j],b)-project(T[i],a))
  for index,p,sign in [(i,a,1),(j,b,-1)]:
   if index==anchor:continue
   ids,weights=basis(index,p)
   rows.extend(np.repeat(np.arange(offset,offset+n),4));cols.extend((ids+offsets[index]).ravel());vals.extend((weights*sign).ravel())
  offset+=n
 A=coo_matrix((vals,(rows,cols)),shape=(offset,count)).tocsr();target=np.concatenate(targets)
 rr=[];cc=[];vv=[];row=0
 for i,start in offsets.items():
  h,w=shapes[i]
  for y in range(h):
   for x in range(w):
    k=start+y*w+x;neigh=[]
    if x>0:neigh.append(k-1)
    if x<w-1:neigh.append(k+1)
    if y>0:neigh.append(k-w)
    if y<h-1:neigh.append(k+w)
    rr.append(row);cc.append(k);vv.append(1.)
    for q in neigh:rr.append(row);cc.append(q);vv.append(-1/len(neigh))
    row+=1
 smooth=coo_matrix((vv,(rr,cc)),shape=(row,count)).tocsr()
 prior=diags(np.full(count,.005));weight=np.ones(len(target));solution=None
 for iteration in range(6):
  W=diags(np.sqrt(weight));matrix=vstack([W@A,smooth,prior]).tocsr()
  solution=np.column_stack([lsqr(matrix,np.r_[np.sqrt(weight)*target[:,axis],np.zeros(row+count)],atol=1e-7,btol=1e-7,iter_lim=1000)[0] for axis in range(2)])
  err=np.linalg.norm(A@solution-target,axis=1);weight=np.minimum(1,.4/np.maximum(err,1e-6))
 meshes=[]
 for i,(h,w) in enumerate(shapes):
  grid=np.zeros((h,w,2),np.float32) if i==anchor else solution[offsets[i]:offsets[i]+h*w].reshape(h,w,2).astype(np.float32)
  if np.max(np.linalg.norm(grid,axis=2))/scale>100:raise RuntimeError('Lokale Korrektur zu groß; Ergebnis verworfen')
  meshes.append(grid)
 def displacement(i,p):
  ids,weights=basis(i,p);return (meshes[i].reshape(-1,2)[ids]*weights[:,:,None]).sum(axis=1)
 checks=[]
 for i,j,a,b in held:
  error=np.linalg.norm(project(T[i],a)+displacement(i,a)-project(T[j],b)-displacement(j,b),axis=1)/scale
  checks.append(dict(pair=[i+1,j+1],count=len(a),median_native_pixels=float(np.median(error)),p90_native_pixels=float(np.percentile(error,90))))
 print('Lokale Kontrolle:',json.dumps(checks),flush=True)
 return {'grids':meshes,'step':step,'scale':scale},checks

def warp_mesh(im,H,corner,size,mesh,index,outscale=1.):
 w,h=(math.ceil(size[0]*outscale),math.ceil(size[1]*outscale));dest=np.zeros((h,w,3),np.uint8);mask=np.zeros((h,w),np.uint8)
 inv=np.linalg.inv(H);grid=mesh['grids'][index];scale=mesh['scale'];step=mesh['step']
 for y in range(0,h,128):
  hh=min(128,h-y);xx,yy=np.meshgrid(np.arange(w,dtype=np.float32)/outscale+corner[0],np.arange(y,y+hh,dtype=np.float32)/outscale+corner[1]);qx=xx.copy();qy=yy.copy()
  for _ in range(4):
   z=inv[2,0]*qx+inv[2,1]*qy+inv[2,2];sx=((inv[0,0]*qx+inv[0,1]*qy+inv[0,2])/z).astype(np.float32);sy=((inv[1,0]*qx+inv[1,1]*qy+inv[1,2])/z).astype(np.float32)
   shift=cv.remap(grid,sx*scale/step,sy*scale/step,cv.INTER_LINEAR,borderMode=cv.BORDER_REPLICATE)/scale
   qx=xx-shift[:,:,0];qy=yy-shift[:,:,1]
  valid=(sx>=1)&(sy>=1)&(sx<im.shape[1]-2)&(sy<im.shape[0]-2)
  dest[y:y+hh]=cv.remap(im,sx,sy,cv.INTER_CUBIC,borderMode=cv.BORDER_REFLECT);mask[y:y+hh]=valid.astype(np.uint8)*255
 return dest,mask

def compose(images,Hs,mesh=None):
 corners=[];sizes=[];local=[]
 for im,H in zip(images,Hs):
  h,w=im.shape[:2];q=project(H,np.float64([[0,0],[w,0],[w,h],[0,h]]));lo=np.floor(q.min(axis=0)).astype(int)-48;hi=np.ceil(q.max(axis=0)).astype(int)+48
  corners.append(tuple(map(int,lo)));sizes.append(tuple(map(int,hi-lo)));T=np.eye(3);T[:2,2]=-lo;local.append(T@H)
 x=min(c[0] for c in corners);y=min(c[1] for c in corners);right=max(c[0]+s[0] for c,s in zip(corners,sizes));bottom=max(c[1]+s[1] for c,s in zip(corners,sizes))
 if right-x>30000 or bottom-y>30000 or (right-x)*(bottom-y)>300_000_000:raise RuntimeError('Unplausible Projektionsgröße')
 sc=.25;small=[];masks=[];cs=[]
 for k,(im,H,c,size) in enumerate(zip(images,local,corners,sizes)):
  A=np.diag([sc,sc,1.])@H;sz=(math.ceil(size[0]*sc),math.ceil(size[1]*sc))
  if mesh is not None:
   warped,mask=warp_mesh(im,Hs[k],c,size,mesh,k,sc);small.append(warped);masks.append(mask)
  else:
   small.append(cv.warpPerspective(im,A,sz,flags=cv.INTER_AREA,borderMode=cv.BORDER_REFLECT))
   masks.append(cv.warpPerspective(np.full(im.shape[:2],255,np.uint8),A,sz,flags=cv.INTER_NEAREST))
  cs.append((round(c[0]*sc),round(c[1]*sc)))
 gains=cv.detail.ExposureCompensator_createDefault(cv.detail.ExposureCompensator_GAIN)
 gains.feed(cs,small,masks)
 seam=[cv.UMat(m.copy()) for m in masks]
 cv.detail.GraphCutSeamFinder('COST_COLOR_GRAD').find([im.astype(np.float32) for im in small],cs,seam)
 blender=cv.detail.MultiBandBlender();blender.setNumBands(2);blender.prepare((x,y,right-x,bottom-y))
 for k,(im,H,c,size) in enumerate(zip(images,local,corners,sizes)):
  if mesh is not None:warped,mask=warp_mesh(im,Hs[k],c,size,mesh,k)
  else:
   warped=cv.warpPerspective(im,H,size,flags=cv.INTER_CUBIC,borderMode=cv.BORDER_REFLECT)
   mask=cv.warpPerspective(np.full(im.shape[:2],255,np.uint8),H,size,flags=cv.INTER_NEAREST)
  gains.apply(k,c,warped,mask)
  m=cv.resize(seam[k].get(),size,interpolation=cv.INTER_NEAREST);m=cv.dilate(m,np.ones((7,7),np.uint8));m=cv.bitwise_and(m,mask)
  blender.feed(warped.astype(np.int16),m,c);print(f'Kartenansicht {k+1}/{len(images)}',flush=True)
 result,mask=blender.blend(None,None)
 result=np.clip(result,0,255).astype(np.uint8);result[mask==0]=0
 return result,mask,dict(origin=[x,y],size=[right-x,bottom-y])

def process(folder):
 folder=Path(folder);files=sorted((folder/'Entwickelt').glob('*.png'));images=[cv.imread(str(p)) for p in files]
 if len(images)<2 or any(im is None for im in images):raise ValueError('Entwickelte Originale fehlen')
 start=time.monotonic();Hs,report,data=fit_transforms(images);mesh,checks=refine_mesh(data);report['local_heldout']=checks;report['mesh']={'step':mesh['step'],'scale':mesh['scale'],'grids':[g.tolist() for g in mesh['grids']]};pano,mask,layout=compose(images,Hs,mesh)
 out=folder/'Panorama-Karten';cv.imwrite(str(out.with_suffix('.jpg')),pano,[cv.IMWRITE_JPEG_QUALITY,100]);cv.imwrite(str(out.with_suffix('.png')),pano,[cv.IMWRITE_PNG_COMPRESSION,3])
 preview=cv.resize(pano,None,fx=min(1,1600/max(pano.shape[:2])),fy=min(1,1600/max(pano.shape[:2])),interpolation=cv.INTER_AREA);cv.imwrite(str(folder/'Karten-Vorschau.jpg'),preview)
 report.update(layout=layout,seconds=time.monotonic()-start,sources=[str(p) for p in files],projection='planar homography with bounded local feature mesh, native pixels, black outside source coverage')
 (folder/'Karten-Ausrichtung.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':
 import sys
 process(sys.argv[1])
