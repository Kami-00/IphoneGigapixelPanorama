#!/usr/bin/env python3
"""Local, non-generative focus fusion. Original inputs are never modified."""
from pathlib import Path
import argparse,json,subprocess,time,html
import cv2 as cv
import numpy as np
from PIL import Image,ImageOps,ImageDraw
cv.setNumThreads(4)

def log(s): print(s,flush=True)
def read_image(path,cache):
    if path.suffix.lower() in ('.heic','.heif'):
        target=cache/(path.stem+'.png')
        subprocess.run(['sips','-s','format','png',str(path),'--out',str(target)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        path=target
    with Image.open(path) as im:return np.array(ImageOps.exif_transpose(im).convert('RGB'))
def gray(a):return cv.cvtColor(a,cv.COLOR_RGB2GRAY).astype(np.float32)/255

def focus_score(a):
    """Smoothed multiscale detail energy; suppress pixel noise before scoring."""
    g=gray(a) if a.ndim==3 else a.astype(np.float32)
    b=cv.GaussianBlur(g,(0,0),.9)
    fine=np.abs(b-cv.GaussianBlur(g,(0,0),1.8))
    coarse=np.abs(cv.GaussianBlur(g,(0,0),1.5)-cv.GaussianBlur(g,(0,0),3.0))
    return cv.GaussianBlur(fine+.35*coarse,(0,0),4)

def global_alignment(ref,mov):
    h,w=ref.shape[:2];scale=min(1,1700/max(h,w))
    r=cv.resize(ref,None,fx=scale,fy=scale,interpolation=cv.INTER_AREA)
    m=cv.resize(mov,None,fx=scale,fy=scale,interpolation=cv.INTER_AREA)
    rg=cv.cvtColor(r,cv.COLOR_RGB2GRAY);mg=cv.cvtColor(m,cv.COLOR_RGB2GRAY)
    sift=cv.SIFT_create(nfeatures=16000,contrastThreshold=.018)
    kr,dr=sift.detectAndCompute(rg,None);km,dm=sift.detectAndCompute(mg,None)
    if dr is None or dm is None:raise ValueError('Zu wenige Bildmerkmale für die Ausrichtung')
    matches=[a for pair in cv.BFMatcher().knnMatch(dr,dm,k=2) if len(pair)==2 for a,b in [pair] if a.distance<.72*b.distance]
    if len(matches)<30:raise ValueError('Zu wenige eindeutige Übereinstimmungen')
    aa=np.float32([kr[x.queryIdx].pt for x in matches]);bb=np.float32([km[x.trainIdx].pt for x in matches])
    H,mask=cv.findHomography(aa,bb,cv.USAC_MAGSAC,1.7,maxIters=10000,confidence=.999)
    if H is None or mask.sum()<30:raise ValueError('Geometrische Ausrichtung nicht verlässlich')
    n=int(mask.sum());before=H.copy();ecc=None
    try:
        ecc,H=cv.findTransformECC(rg.astype(np.float32)/255,mg.astype(np.float32)/255,H.astype(np.float32),cv.MOTION_HOMOGRAPHY,(cv.TERM_CRITERIA_COUNT|cv.TERM_CRITERIA_EPS,60,1e-6),None,5)
        if not np.isfinite(H).all():H=before
    except cv.error:H=before
    S=np.diag([scale,scale,1.]);H=np.linalg.inv(S)@H@S
    corners=np.float32([[[0,0],[w-1,0],[w-1,h-1],[0,h-1]]])
    pts=cv.perspectiveTransform(corners,H)
    area=abs(cv.contourArea(pts[0]))/(w*h)
    if not .65<area<1.5:raise ValueError('Unplausible Größenänderung; Bild ausgelassen')
    return H,{'matches':len(matches),'inliers':n,'ecc':None if ecc is None else float(ecc)}

def color_match(ref,mov,mask):
    size=(420,560);r=cv.resize(ref,size).astype(np.float32);m=cv.resize(mov,size).astype(np.float32)
    valid=cv.resize(mask.astype(np.uint8),size,interpolation=cv.INTER_NEAREST)>0;out=mov.astype(np.float32);coeff=[]
    for c in range(3):
        x=m[:,:,c].ravel();y=r[:,:,c].ravel();keep=valid.ravel()&(x>15)&(x<240)&(y>15)&(y<240)
        for _ in range(3):
            if keep.sum()<100:raise ValueError('Zu wenig gemeinsame Fläche für Farbabgleich')
            coef=np.linalg.lstsq(np.stack([x[keep],np.ones(keep.sum())],1),y[keep],rcond=None)[0]
            residual=abs(x*coef[0]+coef[1]-y);keep&=residual<max(3,float(np.quantile(residual[keep],.8)))
        gain=float(np.clip(coef[0],.7,1.4));bias=float(np.clip(coef[1],-35,35));out[:,:,c]=out[:,:,c]*gain+bias;coeff.append([gain,bias])
    return np.uint8(np.clip(out+.5,0,255)),coeff

def local_alignment(ref,mov,valid,max_shift=12):
    """Smooth, bounded residual flow with forward/backward consistency gating."""
    h,w=ref.shape[:2];scale=min(.5,1400/max(h,w));sw,sh=round(w*scale),round(h*scale)
    a=cv.resize(cv.cvtColor(ref,cv.COLOR_RGB2GRAY),(sw,sh),interpolation=cv.INTER_AREA)
    b=cv.resize(cv.cvtColor(mov,cv.COLOR_RGB2GRAY),(sw,sh),interpolation=cv.INTER_AREA)
    # Blurring keeps registration from chasing individual noise or sharpening halos.
    a=cv.GaussianBlur(a,(0,0),.7);b=cv.GaussianBlur(b,(0,0),.7)
    dis=cv.DISOpticalFlow_create(cv.DISOPTICAL_FLOW_PRESET_MEDIUM)
    f=dis.calc(a,b,None);back=dis.calc(b,a,None)
    yy,xx=np.mgrid[:sh,:sw].astype(np.float32)
    rev=cv.remap(back,xx+f[:,:,0],yy+f[:,:,1],cv.INTER_LINEAR,borderMode=cv.BORDER_REFLECT101)
    consistent=(np.linalg.norm(f+rev,axis=2)<.8)&(np.linalg.norm(f,axis=2)<max_shift*scale)
    support=cv.GaussianBlur(consistent.astype(np.float32),(0,0),3)
    for c in range(2):f[:,:,c]=cv.GaussianBlur(f[:,:,c]*consistent,(0,0),3)/np.maximum(support,.01)
    f*=np.clip((support-.25)/.5,0,1)[:,:,None]
    flow=cv.resize(f,(w,h),interpolation=cv.INTER_LINEAR)/scale
    mag=np.linalg.norm(flow,axis=2);flow*=np.minimum(1,max_shift/np.maximum(mag,1e-6))[:,:,None]
    yy,xx=np.mgrid[:h,:w].astype(np.float32);mx=xx+flow[:,:,0];my=yy+flow[:,:,1]
    result=cv.remap(mov,mx,my,cv.INTER_CUBIC,borderMode=cv.BORDER_REFLECT101)
    mask=cv.remap(valid.astype(np.uint8),mx,my,cv.INTER_NEAREST,borderMode=cv.BORDER_CONSTANT)>0
    confidence=cv.resize(consistent.astype(np.float32),(w,h),interpolation=cv.INTER_LINEAR)
    return result,mask,confidence,{'median_residual_shift_px':float(np.median(mag)),'p95_residual_shift_px':float(np.quantile(mag,.95)),'consistent_fraction':float(consistent.mean())}

def selection(scores,valid,refidx):
    s=np.stack(scores);v=np.stack(valid)
    s=np.where(v,s,-1);winner=s.argmax(0).astype(np.uint8)
    best=s.max(0);ref=s[refidx]
    # A small, uncertain improvement should not replace the reference.
    winner[(best<.0012)|(best<ref*1.08)]=refidx
    votes=np.stack([cv.boxFilter((winner==j).astype(np.float32),-1,(9,9)) for j in range(len(scores))])
    winner=votes.argmax(0).astype(np.uint8)
    winner[(best<.0012)|(best<ref*1.08)]=refidx
    # Categorical majority cleanup must never pick an invalid source.
    yy,xx=np.indices(winner.shape);bad=~v[winner,yy,xx];winner[bad]=refidx
    return winner

def pyramid_fuse(paths,masks,shape,levels=5):
    """Laplacian multiband fusion, streaming sources to limit RAM."""
    h,w=shape;acc=[];weights=[];sizes=[];hh,ww=h,w
    for level in range(levels+1):
        acc.append(np.zeros((hh,ww,3),np.float32));weights.append(np.zeros((hh,ww),np.float32));sizes.append((ww,hh));hh=(hh+1)//2;ww=(ww+1)//2
    for path,mask in zip(paths,masks):
        a=cv.imread(str(path));a=cv.cvtColor(a,cv.COLOR_BGR2RGB).astype(np.float32)/255
        gp=[a];mp=[mask.astype(np.float32)]
        for _ in range(levels):gp.append(cv.pyrDown(gp[-1]));mp.append(cv.pyrDown(mp[-1]))
        for j in range(levels+1):
            band=gp[j] if j==levels else gp[j]-cv.pyrUp(gp[j+1],dstsize=sizes[j])
            acc[j]+=band*mp[j][:,:,None];weights[j]+=mp[j]
    out=acc[-1]/np.maximum(weights[-1][:,:,None],1e-7)
    for j in range(levels-1,-1,-1):out=cv.pyrUp(out,dstsize=sizes[j])+acc[j]/np.maximum(weights[j][:,:,None],1e-7)
    return np.uint8(np.clip(out*255+.5,0,255))

def save_jpg(path,a):Image.fromarray(a).save(path,quality=97,subsampling=0)
def preview(path,a,width=1500):
    im=Image.fromarray(a);im.thumbnail((width,width));im.save(path,quality=93)

def main():
    ap=argparse.ArgumentParser(description='Lokales Focus Stacking: analysieren, ausrichten, scharfe Bereiche verschmelzen')
    ap.add_argument('input',type=Path);ap.add_argument('--output',type=Path);ap.add_argument('--reference',help='Optionaler Dateiname, z.B. IMG_7195.HEIC');ap.add_argument('--no-local',action='store_true',help='Lokale Bewegungskorrektur deaktivieren')
    args=ap.parse_args();folder=args.input.expanduser().resolve();out=(args.output or folder/('FocusStack-'+time.strftime('%Y%m%d-%H%M%S'))).resolve()
    files=sorted(p for p in folder.iterdir() if p.suffix.lower() in ('.heic','.heif','.jpg','.jpeg','.png','.tif','.tiff'))
    if len(files)<2:ap.error('Mindestens zwei Bilder im Eingabeordner erforderlich')
    if len(files)>50:ap.error('Bitte höchstens 50 Bilder pro Serie verwenden')
    out.mkdir(parents=True,exist_ok=True);cache=out/'arbeitsdateien';cache.mkdir(exist_ok=True)
    log(f'{len(files)} Bilder; Ausgabe: {out}')
    paths=[];analysis=[];base_shape=None
    for f in files:
        a=read_image(f,cache)
        if base_shape is None:base_shape=a.shape
        if a.shape!=base_shape:raise ValueError('Alle Bilder müssen dieselbe ausgerichtete Bildgröße besitzen')
        dest=cache/(f.stem+'-rgb.png');Image.fromarray(a).save(dest);paths.append(dest)
        g=gray(a);score=focus_score(g)
        # Robust central-detail score, not a measurement of optical resolution.
        central=score[a.shape[0]//8:-a.shape[0]//8,a.shape[1]//8:-a.shape[1]//8]
        rank=float(np.quantile(central,.9));analysis.append({'file':f.name,'detail_indicator':rank,'median_brightness':float(np.median(g))})
        log(f'Gelesen: {f.name}, Detailindikator {rank:.5f}')
    refidx=next((i for i,f in enumerate(files) if f.name==args.reference),-1) if args.reference else int(np.argmax([x['detail_indicator'] for x in analysis]))
    if refidx<0:ap.error('Referenzdatei nicht gefunden')
    ref=np.array(Image.open(paths[refidx]));h,w=ref.shape[:2];log('Referenz: '+files[refidx].name)
    aligned=[];small_scores=[];small_valid=[];full_valid=[];kept=[];average=np.zeros_like(ref,dtype=np.float32);counts=np.zeros((h,w),np.float32)
    for i,path in enumerate(paths):
        a=np.array(Image.open(path));entry=analysis[i]
        try:
            if i==refidx:im=ref;valid=np.ones((h,w),bool);conf=np.ones((h,w),np.float32);entry['reference']=True
            else:
                H,info=global_alignment(ref,a);entry.update(info);entry['homography_reference_to_source']=H.tolist()
                im=cv.warpPerspective(a,H,(w,h),flags=cv.INTER_CUBIC|cv.WARP_INVERSE_MAP,borderMode=cv.BORDER_REFLECT101)
                valid=cv.warpPerspective(np.ones((h,w),np.uint8),H,(w,h),flags=cv.INTER_NEAREST|cv.WARP_INVERSE_MAP)>0
                im,coeff=color_match(ref,im,valid);entry['color_gain_bias']=coeff
                preview(cache/(path.stem+'-global.jpg'),im,1200)
                if not args.no_local:im,valid,conf,info=local_alignment(ref,im,valid);entry['local_alignment']=info
                else:conf=valid.astype(np.float32)
            dest=cache/(files[i].stem+'-aligned.png');Image.fromarray(im).save(dest);aligned.append(dest);kept.append(i)
            score=focus_score(im)
            # Invalid borders and uncertain local correspondences cannot win selection.
            reliable=cv.erode(valid.astype(np.uint8),np.ones((7,7),np.uint8))>0
            if i!=refidx:reliable&=conf>.35
            small_scores.append(cv.resize(score,(w//2,h//2),interpolation=cv.INTER_AREA))
            small_valid.append(cv.resize(reliable.astype(np.uint8),(w//2,h//2),interpolation=cv.INTER_NEAREST)>0);full_valid.append(reliable)
            average+=im*valid[:,:,None];counts+=valid
            log('Ausgerichtet: '+files[i].name)
        except (ValueError,cv.error) as exc:
            entry['excluded']=str(exc);log('Ausgelassen: '+files[i].name+' / '+str(exc))
    if len(kept)<2:raise ValueError('Weniger als zwei zuverlässig ausgerichtete Bilder')
    ri=kept.index(refidx);labels=selection(small_scores,small_valid,ri)
    masks=[];shares=[]
    for j,i in enumerate(kept):
        m=cv.resize((labels==j).astype(np.float32),(w,h),interpolation=cv.INTER_LINEAR);m=cv.GaussianBlur(m,(0,0),2)*full_valid[j]
        masks.append(m);shares.append(float((labels==j).mean()));analysis[i]['selected_area_fraction']=shares[-1]
    total=sum(masks);masks[ri]+=np.clip(1-total,0,1)
    log('Focus-Fusion mit lokal ausgewählten Schärfebereichen …')
    result=pyramid_fuse(aligned,masks,(h,w));mean=np.uint8(np.clip(average/np.maximum(counts[:,:,None],1)+.5,0,255))
    Image.fromarray(result).save(out/'Focus-Stack.png');save_jpg(out/'Focus-Stack.jpg',result);save_jpg(out/'Referenz.jpg',ref);save_jpg(out/'Mittelwert.jpg',mean)
    preview(out/'focus-vorschau.jpg',result);preview(out/'referenz-vorschau.jpg',ref)
    palette=np.array([[230,70,70],[70,170,240],[60,190,100],[240,190,40],[180,90,230],[30,200,200],[230,100,180],[170,140,70],[130,170,210],[230,140,40]]*5,np.uint8)
    mapim=palette[labels];preview(out/'Schaerfeauswahl.jpg',mapim,1500)
    # Pick detail patches distributed across the actual image; include decoration and edges.
    regions=[('Dekoration',(.55,.18,.38,.25)),('Linke-Kante',(.2,.37,.32,.25)),('Unten',(.38,.70,.38,.25))]
    links=[]
    for name,(xf,yf,wf,hf) in regions:
        x,y,ww,hh=round(w*xf),round(h*yf),min(900,round(w*wf)),min(850,round(h*hf));ww=min(ww,w-x);hh=min(hh,h-y)
        sheet=Image.new('RGB',(ww*3,hh+45),'#eeeeee');d=ImageDraw.Draw(sheet)
        for j,(im,title) in enumerate([(ref,'Referenz '+files[refidx].stem),(mean,'Gleichgewichteter Mittelwert'),(result,'Focus Stack')]):sheet.paste(Image.fromarray(im[y:y+hh,x:x+ww]),(j*ww,45));d.text((j*ww+12,14),title,fill='black')
        sheet.save(out/f'Vergleich-{name}.jpg',quality=96,subsampling=0);links.append(f'Vergleich-{name}.jpg')
    report={'input':str(folder),'output':str(out),'reference':files[refidx].name,'size':[w,h],'used_images':len(kept),'local_alignment':not args.no_local,'method':'8-bit SDR RGB; SIFT+ECC homography, bounded consistent DIS residual flow, multiscale detail selection, reference fallback, Laplacian pyramid fusion; no generative pixels','images':analysis,'limitations':['Detailindikator ist keine optische Auflösungsmessung und kann kamerainterne Schärfung/Rauschen erfassen.','Lokale Verformung ist auf 12 Pixel begrenzt; schwierige Tiefenkanten können verbleibende Fehler zeigen.','Bereits unscharfe Details werden nicht rekonstruiert; HEIC wird als SDR dekodiert.','Farben der Auswahlkarte zeigen die dominante Quelle vor weichen Übergängen.']}
    (out/'bericht.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    rows=''.join(f'<tr><td><span style="color:rgb{tuple(int(x) for x in palette[j])}">●</span> {html.escape(files[i].name)}</td><td>{shares[j]*100:.1f} %</td></tr>' for j,i in enumerate(kept))
    comparisons=''.join(f'<p><a href="{link}">{link}</a></p><img class="detail" src="{link}">' for link in links)
    page='''<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Focus Stack – lokaler Vergleich</title><style>body{max-width:1200px;margin:35px auto;padding:0 20px;background:#15191e;color:#e9edf2;font:16px system-ui}a{color:#8fc8ff}h1{font-size:30px}.viewer{position:relative;max-width:740px;margin:auto}.viewer img{display:block;width:100%}.overlay{position:absolute;inset:0;width:100%;height:100%;clip-path:inset(0 50% 0 0)}input{width:100%;margin:18px 0}.detail{max-width:100%}td{padding:5px 20px 5px 0}.note{color:#bac4cf}</style><h1>Focus Stack</h1><p>Links: Focus Stack · Rechts: Referenz. Mit dem Regler vergleichen.</p><div class="viewer"><img src="referenz-vorschau.jpg"><img id="overlay" class="overlay" src="focus-vorschau.jpg"></div><input aria-label="Vergleichsgrenze" type="range" min="0" max="100" value="50" oninput="document.getElementById('overlay').style.clipPath='inset(0 '+(100-this.value)+'% 0 0)'"><p><a href="Focus-Stack.png">Verlustfreies Ergebnis (PNG)</a> · <a href="Focus-Stack.jpg">JPG</a> · <a href="Referenz.jpg">Referenz in voller Größe</a> · <a href="bericht.json">Analysebericht</a></p>'''
    page+=f'<p>{len(kept)} Aufnahmen · {w} × {h} Pixel · Referenz: {html.escape(files[refidx].name)}</p><p class="note">Originalauflösung, keine generativen Details. Bildprüfung bleibt nötig: unterschiedliche Schärfung und lokale Ausrichtungsfehler können die Auswahl beeinflussen.</p><h2>Detailvergleich</h2>'+comparisons+'<h2>Welche Aufnahme liefert welchen Bereich?</h2><img class="detail" src="Schaerfeauswahl.jpg"><table>'+rows+'</table></html>'
    (out/'Vergleich.html').write_text(page)
    log('FERTIG: '+str(out/'Vergleich.html'))

if __name__=='__main__':main()
