"""Develop original ProRAW and stitch real overlapping views, never synthesize coverage."""
from pathlib import Path
import subprocess,json,time,math
import cv2 as cv
import numpy as np
ROOT=Path(__file__).resolve().parent

def process(folder,variant='sharp',output_name='Panorama'):
 folder=Path(folder).resolve()
 if not folder.is_relative_to((ROOT/'photos').resolve()):raise ValueError('Ungültiger Aufnahmeordner')
 candidates=[]
 for p in sorted(folder.glob('*.dng')):
  meta=json.loads(p.with_suffix('.json').read_text());candidates.append((p,meta))
 if len(candidates)<2:raise ValueError('Mindestens zwei Blickrichtungen erforderlich')
 groups={}
 for p,m in candidates:
  pose=m.get('request',{});key=(pose.get('yaw'),pose.get('pitch'),pose.get('pass_index',1))
  if key[:2]==(None,None):key=(round(m['shutter_motion']['heading'],1),round(m['shutter_motion']['elevation'],1))
  # Focus stacking is a separate step. Prefer a mid-range exposure instead of duplicating views.
  score=abs(m.get('lens_position',.7)-.7)
  if key not in groups or score<groups[key][2]:groups[key]=(p,m,score)
 selected=list(groups.values())
 if len(selected)<2:raise ValueError('Diese Reihe enthält nur eine Blickrichtung')
 # Main camera is fixed at 24 mm equivalent; reject disconnected angular coverage.
 def connected(a,b):
  ma=a[1]['shutter_motion'];mb=b[1]['shutter_motion']
  yaw=abs((ma['heading']-mb['heading']+180)%360-180)
  return yaw<54 and abs(ma['elevation']-mb['elevation'])<68
 seen={0}
 while True:
  more={j for i in seen for j in range(len(selected)) if connected(selected[i],selected[j])}
  if more<=seen:break
  seen|=more
 if len(seen)!=len(selected):raise RuntimeError('Zwischen den Blickrichtungen fehlen überlappende Fotos. Kein geschlossenes Panorama möglich.')
 developed=folder/'Entwickelt';developed.mkdir(exist_ok=True)
 images=[]
 for p,m,_ in selected:
  jpg=developed/(p.stem+'.png')
  if not jpg.exists():subprocess.run([str(ROOT/'tools/render_raw'),str(p),str(jpg)],check=True,timeout=180,capture_output=True)
  im=cv.imread(str(jpg))
  if im is None:raise RuntimeError('Entwickeltes Bild nicht lesbar')
  # Keep every original source pixel for final composition.
  images.append(im)
 stitcher=cv.Stitcher_create(cv.Stitcher_PANORAMA)
 stitcher.setRegistrationResol(2);stitcher.setSeamEstimationResol(.2);stitcher.setCompositingResol(-1)
 status=stitcher.estimateTransform(images)
 if status==cv.Stitcher_OK and len(stitcher.component())!=len(images):raise RuntimeError('Nicht alle Blickrichtungen ließen sich verbinden')
 if status==cv.Stitcher_OK:
  if variant=='sharp':
   from sharp_composite import compose
   pano=compose(images,stitcher)
  else:status,pano=stitcher.composePanorama()
 if status!=cv.Stitcher_OK:raise RuntimeError('Bilder lassen sich nicht zuverlässig verbinden: zu wenig Überlappung oder unpassende Perspektive (Code %d)'%status)
 # Trim only outer empty rows/columns; keep actual irregular coverage visible.
 mask=np.any(pano>0,axis=2).astype(np.uint8);x,y,w,h=cv.boundingRect(mask);pano=pano[y:y+h,x:x+w]
 # Largest rectangular interior, using a small mask, avoids black border wedges.
 scale=min(1.,600/max(pano.shape[:2]));small=cv.resize(np.any(pano>0,axis=2).astype(np.uint8),(round(pano.shape[1]*scale),round(pano.shape[0]*scale)),interpolation=cv.INTER_AREA)
 small=cv.erode(small,np.ones((3,3),np.uint8));hist=np.zeros(small.shape[1],dtype=int);best=(0,0,0,0,0)
 for row,values in enumerate(small):
  hist=np.where(values>0,hist+1,0);stack=[]
  for col,height in enumerate(list(hist)+[0]):
   left=col
   while stack and stack[-1][1]>height:
    start,hh=stack.pop();area=(col-start)*hh
    if area>best[0]:best=(area,start,row-hh+1,col-start,hh)
    left=start
   stack.append((left,height))
 _,xx,yy,ww,hh=best
 if ww and hh:
  x0,y0=int(math.ceil(xx/scale)),int(math.ceil(yy/scale));x1,y1=int((xx+ww)/scale),int((yy+hh)/scale);pano=pano[y0:y1,x0:x1]
 h,w=pano.shape[:2]
 path=folder/(output_name+'.jpg');tmp=folder/(output_name+'.tmp.jpg') 
 if not cv.imwrite(str(tmp),pano,[cv.IMWRITE_JPEG_QUALITY,100]):raise RuntimeError('Panorama konnte nicht gespeichert werden')
 tmp.replace(path)
 lossless=folder/(output_name+'.png');pngtmp=folder/(output_name+'.tmp.png')
 if not cv.imwrite(str(pngtmp),pano,[cv.IMWRITE_PNG_COMPRESSION,3]):raise RuntimeError('Verlustfreies Panorama konnte nicht gespeichert werden')
 pngtmp.replace(lossless)
 report={'file':str(path),'lossless_file':str(lossless),'blending':variant,'source_resolution':'native, no downsampling','compositing_megapixel_limit':None,'width':w,'height':h,'sources':[str(p) for p,_,_ in selected],'projection':'spherical, cropped','complete_360':False,'note':'Teilpanorama. Keine nicht fotografierten Bereiche ergänzt.','created':time.time()}
 (folder/(output_name+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2));return report
if __name__=='__main__':
 import sys
 print(json.dumps(process(sys.argv[1]),ensure_ascii=False))
