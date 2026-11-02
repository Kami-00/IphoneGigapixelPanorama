"""Full native-density 2:1 sphere; absent source coverage is explicitly black.
Projection/composition runs in strips backed by disk to bound RAM use.
"""
from pathlib import Path
import cv2 as cv,numpy as np,json,math,subprocess,time,struct,zlib,sys
ROOT=Path(__file__).resolve().parent

def log(s):print(s,flush=True)
def orient(cameras,metas):
 A=np.array([c.R[:,2] for c in cameras],float)
 headings=np.array([m['shutter_motion']['heading'] for m in metas]);els=np.radians([m['shutter_motion']['elevation'] for m in metas])
 refs=np.radians([m['shutter_motion']['heading']-m['request']['yaw'] for m in metas]);ref=math.atan2(np.sin(refs).mean(),np.cos(refs).mean())
 fits=[]
 for sign in [-1,1]:
  hs=sign*(np.radians(headings)-ref);B=np.stack([np.sin(hs)*np.cos(els),-np.sin(els),np.cos(hs)*np.cos(els)],axis=1)
  u,_,vt=np.linalg.svd(A.T@B);D=np.eye(3);D[-1,-1]=np.linalg.det(u@vt);Q=u@D@vt
  errs=np.degrees(np.arccos(np.clip(np.sum((A@Q)*B,axis=1),-1,1)))
  fits.append((float(np.median(errs)),Q,errs,sign))
 err,Q,errs,sign=min(fits,key=lambda t:t[0])
 if err>10 or max(errs)>28:raise RuntimeError('Bildausrichtung widerspricht den Gyrodaten: '+str(errs.tolist()))
 for c in cameras:c.R=(Q.T@c.R).astype(np.float32)
 return {'median_sensor_difference_degrees':err,'per_image_difference_degrees':errs.tolist(),'heading_sign':sign,'reference_heading':math.degrees(ref)}

def write_png(path,arr):
 h,w=arr.shape[:2]
 def chunk(f,kind,data):f.write(struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff))
 with open(path,'wb') as f:
  f.write(b'\x89PNG\r\n\x1a\n');chunk(f,b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0));comp=zlib.compressobj(3)
  for y in range(h):
   # SUB filter on RGB bytes reduces size without changing any pixels.
   row=np.asarray(arr[y,:,::-1]).copy().reshape(-1);filtered=row.copy();filtered[3:]=row[3:]-row[:-3]
   data=comp.compress(b'\x01'+filtered.tobytes())
   if data:chunk(f,b'IDAT',data)
  data=comp.flush()
  if data:chunk(f,b'IDAT',data)
  chunk(f,b'IEND',b'')

def export(folder,resume=False,preview_only=False):
 folder=Path(folder).resolve();cache=folder/'360-Arbeitsdateien';cache.mkdir(exist_ok=True);(folder/'Entwickelt').mkdir(exist_ok=True)
 files=sorted(folder.glob('20*.dng'));metas=[json.loads(p.with_suffix('.json').read_text()) for p in files]
 if len(files)<3:raise RuntimeError('Zu wenige Aufnahmen')
 images=[];scales=[];sizes=[];source_cache=[]
 for i,p in enumerate(files):
  src=folder/'Entwickelt'/(p.stem+'.png')
  if not src.exists():subprocess.run([str(ROOT/'tools/render_raw'),str(p),str(src)],check=True,timeout=180,capture_output=True)
  cached=cache/(p.stem+'.npy');im=np.load(cached,mmap_mode='r') if cached.exists() else cv.imread(str(src));sizes.append((im.shape[1],im.shape[0]));scale=min(1.,math.sqrt(2_000_000/(im.shape[0]*im.shape[1])));size=(round(im.shape[1]*scale),round(im.shape[0]*scale))
  images.append(cv.resize(im,size,interpolation=cv.INTER_AREA));scales.append(size[0]/im.shape[1])
  npy=cache/(p.stem+'.npy')
  if not npy.exists():np.save(npy,im)
  source_cache.append(npy);log(f'Original vorbereitet {i+1}/{len(files)}')
 if resume and (folder/'360-Kalibrierung.json').exists():
  from types import SimpleNamespace
  saved=json.loads((folder/'360-Kalibrierung.json').read_text())
  if saved['files']!=[str(p) for p in files]:raise RuntimeError('Kalibrierung passt nicht zur Aufnahmereihe')
  cameras=[SimpleNamespace(R=np.array(r,np.float32)) for r in saved['R']];Ks=[np.array(k,np.float32) for k in saved['K']];gyro=saved['gyro_alignment']
  log('Geprüfte Kalibrierung wiederverwendet')
 else:
  from estimate_wide import estimate
  cameras=estimate(images,metas)
  gyro=orient(cameras,metas);log('Gyrovergleich: '+json.dumps(gyro))
  work=1.;Ks=[]
  for c,s in zip(cameras,scales):
   K=c.K().astype(np.float32);K[0,:]/=s*work;K[1,:]/=s*work;Ks.append(K)
 focal=max(float(k[0,0]) for k in Ks);expected=24/math.sqrt(36**2+24**2)*math.hypot(*sizes[0])
 if not .65*expected<focal<1.5*expected:raise RuntimeError(f'Unplausible Brennweite {focal}, erwartet ungefähr {expected}')
 W=int(math.ceil(2*math.pi*focal/2)*2);H=W//2;f=W/(2*math.pi);lowW=4096;lowf=lowW/(2*math.pi)
 log(f'Native 360°-Bildfläche: {W} × {H}')
 checkpoint={'width':W,'height':H,'focal':f,'gyro_alignment':gyro,'files':[str(p) for p in files],'K':[k.tolist() for k in Ks],'R':[c.R.tolist() for c in cameras]}
 if not (folder/'360-Kalibrierung.json').exists():(folder/'360-Kalibrierung.json').write_text(json.dumps(checkpoint,indent=2))
 lows=[];masks=[];corners=[]
 warper=cv.PyRotationWarper('spherical',lowf)
 for im,K,c,s in zip(images,Ks,cameras,scales):
  k=K.copy();k[0,:]*=s;k[1,:]*=s
  corner,warped=warper.warp(im,k,c.R,cv.INTER_LINEAR,cv.BORDER_REFLECT)
  _,mask=warper.warp(np.full(im.shape[:2],255,np.uint8),k,c.R,cv.INTER_NEAREST,cv.BORDER_CONSTANT)
  lows.append(warped);masks.append(mask);corners.append(corner)
 compensator=cv.detail.BlocksChannelsCompensator(96,96,2);compensator.setNrGainsFilteringIterations(2)
 if resume and saved.get('gain_model')=='local RGB blocks' and saved.get('gain_low_width')==lowW:
  gains=[np.asarray(x,np.float32) for x in saved['gain_maps']];compensator.setMatGains(gains);log('Lokalen Farbabgleich wiederverwendet')
 else:
  compensator.feed(corners,lows,masks);gains=[np.asarray(x,np.float32) for x in compensator.getMatGains()]
 low_shapes=[im.shape[:2] for im in lows]
 for i in range(len(lows)):compensator.apply(i,corners[i],lows[i],masks[i])
 seam_masks=[cv.UMat(m.copy()) for m in masks]
 cv.detail.DpSeamFinder('COLOR_GRAD').find([im.astype(np.float32) for im in lows],corners,seam_masks)
 seams=[cv.dilate(m.get(),np.ones((3,3),np.uint8)) for m in seam_masks]
 calibration={'width':W,'height':H,'focal':f,'gyro_alignment':gyro,'files':[str(p) for p in files],'K':[k.tolist() for k in Ks],'R':[c.R.tolist() for c in cameras],'gain_maps':[g.tolist() for g in gains],'gain_model':'local RGB blocks','gain_low_width':lowW}
 (folder/'360-Kalibrierung.json').write_text(json.dumps(calibration,indent=2))
 if preview_only:
  canvas=np.zeros((lowW//2,lowW,3),np.float32);weights=np.zeros((lowW//2,lowW),np.float32);fallback=np.zeros_like(canvas);seen=np.zeros(weights.shape,bool)
  for im,mask,seam,corner in zip(lows,masks,seams,corners):
   x,y=corner[0]+lowW//2,corner[1];hh,ww=mask.shape;x0=max(0,x);y0=max(0,y);x1=min(lowW,x+ww);y1=min(lowW//2,y+hh)
   if x1<=x0 or y1<=y0:continue
   sx,sy=x0-x,y0-y;a=im[sy:sy+y1-y0,sx:sx+x1-x0];valid=mask[sy:sy+y1-y0,sx:sx+x1-x0]>0;weight=seam[sy:sy+y1-y0,sx:sx+x1-x0].astype(np.float32)/255*valid
   target=fallback[y0:y1,x0:x1];known=seen[y0:y1,x0:x1];take=valid&~known;target[take]=a[take];known|=valid
   canvas[y0:y1,x0:x1]+=a*weight[:,:,None];weights[y0:y1,x0:x1]+=weight
  ok=weights>0;fallback[ok]=canvas[ok]/weights[ok,None];fallback[~seen]=0
  cv.imwrite(str(folder/'Farbabgleich-Vorschau.jpg'),np.clip(fallback,0,255).astype(np.uint8),[cv.IMWRITE_JPEG_QUALITY,95]);log('Farbabgleich-Vorschau fertig');return
 del lows,images,masks,seam_masks
 sources=[np.load(p,mmap_mode='r') for p in source_cache]
 result=np.lib.format.open_memmap(cache/'sphere.npy',mode='w+',dtype=np.uint8,shape=(H,W,3));covered_total=0
 for y0 in range(0,H,96):
  height=min(96,H-y0);theta=(np.arange(y0,y0+height,dtype=np.float32)/f)[:,None]
  for x0 in range(0,W,8192):
   width=min(8192,W-x0);lon=((np.arange(x0,x0+width,dtype=np.float32)-W/2)/f)[None,:]
   rx=np.sin(theta)*np.sin(lon);ry=-np.cos(theta);rz=np.sin(theta)*np.cos(lon)
   accum=np.zeros((height,width,3),np.float32);weights=np.zeros((height,width),np.float32);fallback=np.zeros((height,width,3),np.uint8);coverage=np.zeros((height,width),bool)
   worldlowx=np.broadcast_to(lon*lowf,(height,width)).copy();worldlowy=np.broadcast_to(theta*lowf,(height,width)).copy()
   for i,(src,K,c,seam,corner,gain) in enumerate(zip(sources,Ks,cameras,seams,corners,gains)):
    Rt=c.R.T;cz=Rt[2,0]*rx+Rt[2,1]*ry+Rt[2,2]*rz
    if not np.any(cz>0):continue
    cx=Rt[0,0]*rx+Rt[0,1]*ry+Rt[0,2]*rz;cy=Rt[1,0]*rx+Rt[1,1]*ry+Rt[1,2]*rz;z=np.where(cz>1e-6,cz,1.)
    mx=(K[0,0]*cx/z+K[0,2]).astype(np.float32);my=(K[1,1]*cy/z+K[1,2]).astype(np.float32)
    valid=(cz>0)&(mx>=1)&(my>=1)&(mx<src.shape[1]-2)&(my<src.shape[0]-2)
    if not np.any(valid):continue
    warped=cv.remap(src,mx,my,cv.INTER_CUBIC,borderMode=cv.BORDER_REFLECT)
    gh,gw=gain.shape[:2];lh,lw=low_shapes[i]
    gx=((worldlowx-corner[0]+.5)*gw/lw-.5).astype(np.float32);gy=((worldlowy-corner[1]+.5)*gh/lh-.5).astype(np.float32)
    local_gain=cv.remap(gain,gx,gy,cv.INTER_LINEAR,borderMode=cv.BORDER_REPLICATE)
    warped=np.clip(warped.astype(np.float32)*local_gain,0,255).astype(np.uint8)
    take=valid&~coverage;fallback[take]=warped[take];coverage|=valid
    weight=cv.remap(seam,worldlowx-corner[0],worldlowy-corner[1],cv.INTER_LINEAR,borderMode=cv.BORDER_CONSTANT).astype(np.float32)/255;weight*=valid
    accum+=warped.astype(np.float32)*weight[:,:,None];weights+=weight
   ok=weights>0;tile=fallback;tile[ok]=np.clip(accum[ok]/weights[ok,None],0,255).astype(np.uint8);tile[~coverage]=0
   result[y0:y0+height,x0:x0+width]=tile;covered_total+=int(coverage.sum())
  if y0%(96*12)==0:log(f'360°-Pixel berechnet: {100*(y0+height)/H:.0f}%')
 result.flush();log('360°-PNG speichern')
 png=folder/'Rundblick-360.png';tmp=folder/'Rundblick-360.tmp.png';write_png(tmp,result);tmp.replace(png)
 jpg=folder/'Rundblick-360.jpg';log('360°-JPEG speichern')
 if W<=65500 and H<=65500:
  if not cv.imwrite(str(jpg),result,[cv.IMWRITE_JPEG_QUALITY,100]):raise RuntimeError('JPEG-Export fehlgeschlagen')
  subprocess.run(['/opt/homebrew/bin/exiftool','-overwrite_original','-XMP-GPano:ProjectionType=equirectangular','-XMP-GPano:UsePanoramaViewer=True',f'-XMP-GPano:FullPanoWidthPixels={W}',f'-XMP-GPano:FullPanoHeightPixels={H}',f'-XMP-GPano:CroppedAreaImageWidthPixels={W}',f'-XMP-GPano:CroppedAreaImageHeightPixels={H}','-XMP-GPano:CroppedAreaLeftPixels=0','-XMP-GPano:CroppedAreaTopPixels=0',str(jpg)],check=True,capture_output=True)
 preview=cv.resize(result,(8192,4096),interpolation=cv.INTER_AREA);cv.imwrite(str(folder/'360-Vorschau.jpg'),preview,[cv.IMWRITE_JPEG_QUALITY,93])
 report={'width':W,'height':H,'megapixels':W*H/1e6,'covered_percent':100*covered_total/(W*H),'black_unseen_percent':100*(1-covered_total/(W*H)),'source_count':len(files),'png':str(png),'jpg':str(jpg),'projection':'equirectangular 360x180 degrees','missing_regions':'black, no generated scene content','native_resolution':True,'gyro_alignment':gyro}
 (folder/'360-Ergebnis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));log(json.dumps(report));return report
if __name__=='__main__':export(sys.argv[1],resume='--resume' in sys.argv,preview_only='--preview' in sys.argv)
