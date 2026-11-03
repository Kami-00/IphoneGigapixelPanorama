#!/usr/bin/env python3
"""Planar mosaic for flat subjects: overlapping frames into one native-resolution image.
Originals are never modified and uncovered areas are never invented.
"""
from pathlib import Path
import argparse,json,math,os,shutil,subprocess,time
import cv2 as cv
import numpy as np
from scipy.optimize import least_squares
cv.setNumThreads(4)

ROOT=Path(__file__).resolve().parent.parent
RENDER_RAW=Path(os.environ.get('RENDER_RAW',ROOT/'OsmoStudio/tools/render_raw'))
RAW=('.dng',)
APPLE=('.heic','.heif')

def log(s): print(s,flush=True)
def S(s): return np.array([[s,0,0],[0,s,0],[0,0,1]],float)
def T(x,y): return np.array([[1,0,x],[0,1,y],[0,0,1]],float)

def project(H,p):
    q=np.column_stack((p,np.ones(len(p))))@H.T
    return q[:,:2]/q[:,2,None]

def develop(paths,cache):
    """DNG through the project's CoreImage renderer, HEIC through macOS; others as they are."""
    cache.mkdir(parents=True,exist_ok=True);out=[]
    for p in paths:
        suffix=p.suffix.lower();target=cache/(p.stem+'.png')
        if suffix in RAW:
            if not target.exists():
                if not RENDER_RAW.exists():raise RuntimeError(f'RAW-Entwickler fehlt: {RENDER_RAW}. Einmal ./setup-mac.sh ausführen.')
                subprocess.run([str(RENDER_RAW),str(p),str(target)],check=True,timeout=300,capture_output=True)
            out.append(target)
        elif suffix in APPLE:
            if not target.exists():subprocess.run(['sips','-s','format','png',str(p),'--out',str(target)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            out.append(target)
        else:out.append(p)
    return out

# ---------------------------------------------------------------- registration
def features(paths,reg_max,nfeat):
    """SIFT on a bounded working size; the scale back to native pixels is uniform."""
    sift=cv.SIFT_create(nfeatures=nfeat,contrastThreshold=.018)
    kps,dess,sizes,scale=[],[],[],None
    for p in paths:
        im=cv.imread(str(p),cv.IMREAD_COLOR)
        if im is None:raise ValueError(f'Bild nicht lesbar: {p}')
        h,w=im.shape[:2];sizes.append((w,h));s=min(1.,reg_max/max(w,h))
        if scale is not None and abs(s-scale)>1e-9:raise ValueError('Alle Aufnahmen müssen dieselbe Bildgröße haben')
        scale=s
        g=cv.cvtColor(cv.resize(im,(round(w*s),round(h*s)),interpolation=cv.INTER_AREA),cv.COLOR_BGR2GRAY)
        k,d=sift.detectAndCompute(g,None)
        if d is None or len(k)<200:raise ValueError(f'Zu wenige Bildmerkmale: {p.name}')
        kps.append(np.float64([x.pt for x in k]));dess.append(np.float32(d))
        log(f'  {p.name}: {len(k)} Merkmale');del im,g
    return kps,dess,sizes,scale

def grid_neighbours(n,cols,rows,order='serpentine'):
    """Index pairs the capture pattern says must overlap. Repetitive subjects such as
    pegboard match equally well a whole card-pitch away, so knowing how the frames were
    taken removes most chances to go wrong before any matching happens."""
    if cols<1 or rows<1 or cols*rows<n:raise ValueError(f'Raster {cols}x{rows} fasst {n} Aufnahmen nicht')
    if order not in ('serpentine','raster'):raise ValueError('Reihenfolge muss serpentine oder raster sein')
    place={}
    for k in range(n):
        r,c=divmod(k,cols)
        place[k]=(r,cols-1-c if order=='serpentine' and r%2 else c)
    return {(i,j) for i in range(n) for j in range(i+1,n)
            if max(abs(place[i][0]-place[j][0]),abs(place[i][1]-place[j][1]))<=1}

def pair_matches(kps,dess,ratio=.75,min_inliers=60,min_spread=25000,allowed=None):
    """Confirmed correspondences per overlapping pair, in registration pixels."""
    flann=cv.FlannBasedMatcher(dict(algorithm=1,trees=5),dict(checks=64));pairs={}
    for i in range(len(kps)):
        for j in range(i+1,len(kps)):
            if allowed is not None and (i,j) not in allowed:continue
            raw=flann.knnMatch(dess[i],dess[j],k=2)
            good=[a for a,b in (x for x in raw if len(x)==2) if a.distance<ratio*b.distance]
            if len(good)<min_inliers:continue
            a=np.float64([kps[i][m.queryIdx] for m in good]);b=np.float64([kps[j][m.trainIdx] for m in good])
            H,valid=cv.findHomography(a,b,cv.USAC_MAGSAC,3.,maxIters=20000,confidence=.9999)
            if H is None or valid is None:continue
            keep=valid.ravel()>0;a,b=a[keep],b[keep]
            if len(a)<min_inliers:continue
            # Repeated packaging artwork can match in a tight cluster; demand a real area.
            if min(np.ptp(a[:,0])*np.ptp(a[:,1]),np.ptp(b[:,0])*np.ptp(b[:,1]))<min_spread:
                log(f'  {i}-{j}: Übereinstimmungen zu eng beieinander, verworfen');continue
            pairs[(i,j)]=(a,b);log(f'  {i}-{j}: {len(a)} Zuordnungen bestätigt')
    return pairs

def connected(pairs,n,root=0):
    seen={root}
    while True:
        more={y for (i,j) in pairs for x,y in ((i,j),(j,i)) if x in seen}
        if more<=seen:return seen
        seen|=more

def chain(pairs,n):
    """Spanning tree from the best connected frame; strongest overlaps first."""
    weight=[0]*n
    for (i,j),(a,_) in pairs.items():weight[i]+=len(a);weight[j]+=len(a)
    ref=int(np.argmax(weight));H={ref:np.eye(3)}
    edges=sorted(pairs.items(),key=lambda kv:-len(kv[1][0]))
    changed=True
    while changed:
        changed=False
        for (i,j),(a,b) in edges:
            if (i in H)==(j in H):continue
            Hij,_=cv.findHomography(a,b,cv.USAC_MAGSAC,3.)
            if Hij is None:continue
            if i in H:H[j]=H[i]@np.linalg.inv(Hij)
            else:H[i]=H[j]@Hij
            changed=True
    if len(H)!=n:raise RuntimeError(f'Nicht alle Aufnahmen verbunden: {sorted(H)} von {n}. Zu wenig Überlappung.')
    return ref,[H[i]/H[i][2,2] for i in range(n)]

def refine(Hs,pairs,ref,n,rounds=3,max_pair_error=120.):
    """Global least squares over every correspondence. Pairs that already contradict the
    chained transforms are false matches, not fit error, so they go before the fit starts:
    once such a pair is inside the optimisation it drags every frame along and no longer
    stands out. The threshold has to clear ordinary chain drift, which stays near a percent
    of the working size, while a false match misses by a large fraction of the whole frame;
    mosaic() therefore scales it to the registration size. Nothing is dropped that would
    disconnect a frame."""
    ids=[i for i in range(n) if i!=ref]
    def expand(x):
        out=[None]*n;out[ref]=np.eye(3)
        for k,i in enumerate(ids):out[i]=np.append(x[8*k:8*k+8],1.).reshape(3,3)
        return out
    def spread(Hc,data):
        return {k:float(np.sqrt(np.mean(np.sum((project(Hc[k[0]],a)-project(Hc[k[1]],b))**2,axis=1)))) for k,(a,b) in data.items()}
    def without(use,bad,why):
        keep={k:v for k,v in use.items() if k not in bad}
        if len(connected(keep,n,ref))!=n:
            log('  abweichende Paare bleiben, sonst zerfällt die Verbindung');return use,[]
        log(f'  {why}: '+', '.join('%d-%d'%k for k in bad));return keep,[list(k) for k in bad]
    use=dict(pairs);dropped=[]
    chained=spread(Hs,use)
    log('  nach Verkettung; je Paar '+', '.join('%d-%d:%.1f'%(i,j,v) for (i,j),v in sorted(chained.items())))
    contradicting=[k for k,v in chained.items() if v>max_pair_error]
    if contradicting:
        use,gone=without(use,contradicting,'falsche Zuordnung verworfen');dropped+=gone
    x=np.concatenate([(Hs[i]/Hs[i][2,2]).ravel()[:8] for i in ids])
    before=float(np.sqrt(np.mean(np.concatenate([(project(Hs[i],a)-project(Hs[j],b)).ravel() for (i,j),(a,b) in use.items()])**2)))
    after=before
    for _ in range(rounds):
        data=dict(use)
        def residual(v,data=data):
            Hc=expand(v)
            return np.concatenate([(project(Hc[i],a)-project(Hc[j],b)).ravel() for (i,j),(a,b) in data.items()])
        fit=least_squares(residual,x,loss='huber',f_scale=1.5,method='trf',max_nfev=600,xtol=1e-12,ftol=1e-12)
        x=fit.x;after=float(np.sqrt(np.mean(fit.fun**2)));rms=spread(expand(x),use)
        log('  Ausgleich %.2f px; je Paar '%after+', '.join('%d-%d:%.1f'%(i,j,v) for (i,j),v in sorted(rms.items())))
        median=float(np.median(list(rms.values())))
        bad=[k for k,v in rms.items() if v>max(4*median,4.)]
        if not bad:break
        use,gone=without(use,bad,'verworfen')
        if not gone:break
        dropped+=gone
    return [h/h[2,2] for h in expand(x)],{'rms_before':before,'rms_after':after,'dropped_pairs':dropped,'used_pairs':[list(k) for k in use]}

# ---------------------------------------------------------------- composition
def boxes(Hs,sizes,s):
    """Per frame: homography and integer bounding box at output scale s."""
    out=[]
    for H,(w,h) in zip(Hs,sizes):
        Hs_=S(s)@H@S(1/s);q=project(Hs_,np.float64([[0,0],[w*s,0],[w*s,h*s],[0,h*s]]))
        lo=np.floor(q.min(0));hi=np.ceil(q.max(0))
        out.append((Hs_,int(lo[0]),int(lo[1]),int(hi[0]),int(hi[1])))
    return out

def largest_rect(cov,inset=2):
    """Largest axis-aligned rectangle that is fully covered, in pixels of cov."""
    m=cv.erode(cov,np.ones((3,3),np.uint8))>0
    hist=np.zeros(m.shape[1],int);best=(0,0,0,0,0)
    for row,vals in enumerate(m):
        hist=np.where(vals,hist+1,0);stack=[]
        for col,height in enumerate(list(hist)+[0]):
            left=col
            while stack and stack[-1][1]>height:
                start,tall=stack.pop();area=(col-start)*tall
                if area>best[0]:best=(area,start,row-tall+1,col-start,tall)
                left=start
            stack.append((left,height))
    _,x,y,w,h=best
    if not(w and h):return None
    return (x+inset,y+inset,max(1,w-2*inset),max(1,h-2*inset))

def warp(path,H,x0,y0,x1,y1,s):
    """One frame into its own window. Reflected borders keep the blender from darkening edges."""
    im=cv.imread(str(path),cv.IMREAD_COLOR)
    if s!=1.:im=cv.resize(im,(round(im.shape[1]*s),round(im.shape[0]*s)),interpolation=cv.INTER_AREA)
    M=T(-x0,-y0)@H;size=(x1-x0,y1-y0)
    warped=cv.warpPerspective(im,M,size,flags=cv.INTER_CUBIC,borderMode=cv.BORDER_REFLECT)
    mask=cv.warpPerspective(np.full(im.shape[:2],255,np.uint8),M,size,flags=cv.INTER_NEAREST,borderMode=cv.BORDER_CONSTANT,borderValue=0)
    del im;return warped,mask

def compose(paths,Hs,sizes,scale,bands,seam_mp,crop):
    """Native-resolution composite. Cropping before blending keeps peak memory near the
    delivered pixels instead of the much larger bounding canvas."""
    bb=boxes(Hs,sizes,scale)
    CX0=min(b[1] for b in bb);CY0=min(b[2] for b in bb);CX1=max(b[3] for b in bb);CY1=max(b[4] for b in bb)
    log(f'  volle Fläche {CX1-CX0} x {CY1-CY0} ({(CX1-CX0)*(CY1-CY0)/1e6:.1f} MP)')

    rel=min(1.,math.sqrt(seam_mp*1e6/max(1,max((b[3]-b[1])*(b[4]-b[2]) for b in bb))));ss=scale*rel
    sb=boxes(Hs,sizes,ss);small,masks,corners=[],[],[]
    for p,(H,x0,y0,x1,y1) in zip(paths,sb):
        w,m=warp(p,H,x0,y0,x1,y1,ss);small.append(w);masks.append(m);corners.append((x0,y0))
    sx0=min(b[1] for b in sb);sy0=min(b[2] for b in sb);sx1=max(b[3] for b in sb);sy1=max(b[4] for b in sb)
    cover=np.zeros((sy1-sy0,sx1-sx0),np.uint8)
    for m,(cx,cy) in zip(masks,corners):
        part=cover[cy-sy0:cy-sy0+m.shape[0],cx-sx0:cx-sx0+m.shape[1]];np.maximum(part,m,out=part)
    gains=cv.detail.ExposureCompensator_createDefault(cv.detail.ExposureCompensator_GAIN_BLOCKS)
    gains.feed(corners,small,masks)
    seams=[cv.UMat(m.copy()) for m in masks]
    cv.detail.GraphCutSeamFinder('COST_COLOR_GRAD').find([i.astype(np.float32) for i in small],corners,seams)
    seams=[s.get() for s in seams];del small,masks
    log('  Belichtung angeglichen, Nähte bestimmt')

    if crop:
        r=largest_rect(cover)
        if r is None:raise RuntimeError('Keine zusammenhängende Fläche gefunden')
        f=1/rel
        X0=max(int(math.ceil((sx0+r[0])*f)),CX0);Y0=max(int(math.ceil((sy0+r[1])*f)),CY0)
        X1=min(int((sx0+r[0]+r[2])*f),CX1);Y1=min(int((sy0+r[1]+r[3])*f),CY1)
    else:X0,Y0,X1,Y1=CX0,CY0,CX1,CY1
    W,H_=X1-X0,Y1-Y0
    log(f'  Ausgabe {W} x {H_} ({W*H_/1e6:.1f} MP)')

    blender=cv.detail.MultiBandBlender();blender.setNumBands(bands);blender.prepare((X0,Y0,W,H_))
    # Real source pixels stay available for rounding-sized gaps where seams meet.
    fallback=np.zeros((H_,W,3),np.uint8);known=np.zeros((H_,W),np.uint8)
    kernel=np.ones((2*max(1,int(math.ceil(1/rel)))+1,)*2,np.uint8);used=0
    for n,(p,(H,x0,y0,x1,y1)) in enumerate(zip(paths,bb)):
        ix0,iy0,ix1,iy1=max(x0,X0),max(y0,Y0),min(x1,X1),min(y1,Y1)
        if ix1<=ix0 or iy1<=iy0:log(f'  {p.name} liegt außerhalb des Zuschnitts');continue
        warped,mask=warp(p,H,ix0,iy0,ix1,iy1,scale);used+=1
        gains.apply(n,(ix0,iy0),warped,mask)
        full=cv.resize(seams[n],(x1-x0,y1-y0),interpolation=cv.INTER_NEAREST)
        seam=cv.bitwise_and(cv.dilate(full[iy0-y0:iy1-y0,ix0-x0:ix1-x0],kernel),mask);del full
        oy,ox=iy0-Y0,ix0-X0;hh,ww=mask.shape
        target=fallback[oy:oy+hh,ox:ox+ww];seen=known[oy:oy+hh,ox:ox+ww]
        take=(seen==0)&(mask>0);target[take]=warped[take];seen[mask>0]=255
        blender.feed(warped.astype(np.int16),seam,(ix0,iy0))
        del warped,mask,seam,take;log(f'  zusammengesetzt {n+1}/{len(paths)}')
    del seams
    result,covered=blender.blend(None,None);del blender
    out=np.empty((H_,W,3),np.uint8)
    for y in range(0,H_,4096):
        band=result[y:y+4096];np.clip(band,0,255,out=band);out[y:y+4096]=band.astype(np.uint8)
    del result
    holes=(covered==0)&(known>0);out[holes]=fallback[holes];out[known==0]=0
    gaps=int(holes.sum());del fallback,covered,holes
    log(f'  Nahtlücken mit Originalpixeln geschlossen: {gaps}')
    return out,{'width':W,'height':H_,'megapixels':round(W*H_/1e6,1),'cropped':bool(crop),
                'full_canvas':[CX1-CX0,CY1-CY0],'frames_used':used,'seam_gaps_filled':gaps,
                'uncovered_pixels':int((known==0).sum())}

def copy_metadata(source,target):
    """Best effort only; a missing exiftool must never fail a finished image."""
    if not shutil.which('exiftool'):return False
    tags=['-Make','-Model','-LensModel','-FocalLength','-FocalLengthIn35mmFormat','-FNumber','-ISO','-ExposureTime','-DateTimeOriginal']
    r=subprocess.run(['exiftool','-q','-m','-overwrite_original','-TagsFromFile',str(source)]+tags+[str(target)],capture_output=True)
    return r.returncode==0

def mosaic(inputs,out,scale=1.,crop=True,reg_max=2400,nfeat=12000,bands=3,seam_mp=1.5,quality=97,work=None,calibration=None,grid=None,order='serpentine'):
    paths=[Path(p) for p in inputs]
    for p in paths:
        if not p.exists():raise ValueError(f'Datei fehlt: {p}')
    if len(paths)<2:raise ValueError('Mindestens zwei überlappende Aufnahmen erforderlich')
    out=Path(out);start=time.monotonic()
    work=Path(work) if work else out.parent/'arbeitsdateien'
    log('Entwickeln ...');sources=develop(paths,work)
    cal=Path(calibration) if calibration else None
    if cal and cal.exists():
        saved=json.loads(cal.read_text())
        if saved['sources']!=[str(p) for p in sources]:raise ValueError('Kalibrierung passt nicht zu diesen Aufnahmen')
        Hs=[np.array(h,float) for h in saved['transforms']];sizes=[tuple(s) for s in saved['sizes']]
        # Carry the stored fit forward, or a reused run would report nothing about its own alignment.
        fit={k:v for k,v in saved.items() if k not in ('sources','sizes','transforms')};fit['reused']=str(cal)
    else:
        log('Merkmale suchen ...');kps,dess,sizes,s=features(sources,reg_max,nfeat)
        allowed=None
        if grid:
            cols,rows=grid
            allowed=grid_neighbours(len(sources),cols,rows,order)
            log(f'Aufnahmemuster {cols}x{rows} ({order}): nur {len(allowed)} benachbarte Paare statt {len(sources)*(len(sources)-1)//2}')
        log('Aufnahmen zuordnen ...');pairs=pair_matches(kps,dess,allowed=allowed)
        if not pairs:raise RuntimeError('Keine überlappenden Aufnahmen gefunden')
        ref,Hs=chain(pairs,len(sources));log(f'  Bezugsaufnahme: {sources[ref].name}')
        Hs,fit=refine(Hs,pairs,ref,len(sources),max_pair_error=.05*reg_max)
        Hs=[S(1/s)@H@S(s) for H in Hs]
        fit.update(reference=sources[ref].name,registration_scale=s,grid=list(grid) if grid else None,order=order if grid else None,
                   rms_before_native=fit['rms_before']/s,rms_after_native=fit['rms_after']/s)
        if cal:cal.write_text(json.dumps({'sources':[str(p) for p in sources],'sizes':[list(x) for x in sizes],
                                          'transforms':[h.tolist() for h in Hs],**fit},indent=1))
    log(f'Zusammensetzen bei Maßstab {scale} ...')
    image,layout=compose(sources,Hs,sizes,scale,bands,seam_mp,crop)
    out.parent.mkdir(parents=True,exist_ok=True)
    params=[cv.IMWRITE_JPEG_QUALITY,quality] if out.suffix.lower() in ('.jpg','.jpeg') else [cv.IMWRITE_PNG_COMPRESSION,3]
    if not cv.imwrite(str(out),image,params):raise RuntimeError('Ergebnis konnte nicht geschrieben werden')
    report={'file':str(out),'sources':[str(p) for p in paths],'developed':[str(p) for p in sources],
            'scale':scale,'bands':bands,'projection':'planar homography, native pixels, black outside source coverage',
            'metadata_copied':copy_metadata(paths[0],out),'seconds':round(time.monotonic()-start,1),**layout,'alignment':fit}
    out.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    log(f'fertig in {report["seconds"]:.0f}s -> {out}  {layout["width"]}x{layout["height"]} ({layout["megapixels"]} MP)')
    return report

def main():
    ap=argparse.ArgumentParser(description='Überlappende Aufnahmen einer flachen Fläche zu einem Bild zusammensetzen.')
    ap.add_argument('inputs',nargs='+',help='DNG, HEIC, PNG, JPEG oder TIFF')
    ap.add_argument('--out',required=True,help='Zieldatei (.jpg oder .png)')
    ap.add_argument('--scale',type=float,default=1.,help='1.0 = volle Auflösung; kleiner für schnelle Probeläufe')
    ap.add_argument('--full-canvas',action='store_true',help='ganze Fläche mit schwarzen Rändern statt größtem gefülltem Rechteck')
    ap.add_argument('--calibration',help='JSON-Datei; einmal berechnete Ausrichtung wiederverwenden')
    ap.add_argument('--work',help='Ordner für entwickelte Zwischenbilder')
    ap.add_argument('--grid',help='Aufnahmemuster als SPALTENxREIHEN, etwa 7x2; begrenzt die Suche auf benachbarte Aufnahmen')
    ap.add_argument('--order',default='serpentine',choices=['serpentine','raster'],help='serpentine: jede zweite Reihe rückwärts')
    ap.add_argument('--reg-max',type=int,default=2400,help='Arbeitsgröße der Merkmalssuche in Pixeln')
    ap.add_argument('--features',type=int,default=12000)
    ap.add_argument('--bands',type=int,default=3)
    ap.add_argument('--seam-megapixels',type=float,default=1.5)
    ap.add_argument('--quality',type=int,default=97)
    a=ap.parse_args()
    grid=tuple(int(v) for v in a.grid.lower().split('x')) if a.grid else None
    mosaic(a.inputs,a.out,scale=a.scale,crop=not a.full_canvas,reg_max=a.reg_max,nfeat=a.features,
           bands=a.bands,seam_mp=a.seam_megapixels,quality=a.quality,work=a.work,calibration=a.calibration,
           grid=grid,order=a.order)

if __name__=='__main__':main()
