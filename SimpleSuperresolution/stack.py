"""Simple resize -> Hugin alignment -> mean/median, inspired by Isaac Ullah (2017).
No generative enhancement, exposure matching, optical flow or focus fusion.
"""
from pathlib import Path
import argparse, json, os, signal, subprocess, sys, tempfile, time, shutil, html
import numpy as np
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS=None
ROOT=Path(__file__).resolve().parent
MAGICK='/opt/homebrew/bin/magick'
EXT={'.jpg','.jpeg','.heic','.heif','.png','.tif','.tiff'}
child=None

def stop(signum,frame):
    if child and child.poll() is None: child.terminate()
    raise KeyboardInterrupt

def run(cmd,log):
    global child
    env=dict(os.environ,OMP_NUM_THREADS='4',MAGICK_THREAD_LIMIT='4')
    with log.open('a') as f:
        f.write('\n'+repr([str(x) for x in cmd])+'\n');f.flush()
        child=subprocess.Popen([str(x) for x in cmd],stdout=f,stderr=subprocess.STDOUT,env=env)
        try:code=child.wait()
        finally:
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:child.kill();child.wait()
        child=None
    if code:raise RuntimeError(f'Verarbeitung fehlgeschlagen ({Path(str(cmd[0])).name}). Details: {log}')

def combine(arrays,output):
    """Equal-weight encoded-RGB mean/median, bounded working memory."""
    h,w=arrays[0].shape[:2]
    mean=np.lib.format.open_memmap(output/'mean.npy',mode='w+',dtype=np.uint8,shape=(h,w,3))
    median=np.lib.format.open_memmap(output/'median.npy',mode='w+',dtype=np.uint8,shape=(h,w,3))
    for y in range(0,h,64):
        block=np.stack([a[y:y+64,:,:3] for a in arrays])
        mean[y:y+64]=np.floor(block.mean(axis=0,dtype=np.float32)+.5).astype(np.uint8)
        median[y:y+64]=np.floor(np.median(block,axis=0)+.5).astype(np.uint8)
    mean.flush();median.flush()
    return mean,median

def write_comparison(out,arrays,labels):
    # Same geometry, same pixels and no sharpening in all three columns.
    h,w=arrays[0].shape[:2];thumbs=[]
    for a,name in zip(arrays,labels):
        im=Image.fromarray(np.asarray(a[:,:,:3]));im.thumbnail((1600,1600));im.save(out/(name+'-Vorschau.jpg'),quality=95,subsampling=0)
    for title,fx,fy in [('Mitte',.5,.5),('Links',.3,.5),('Rechts',.7,.5)]:
        cw=min(750,w);ch=min(650,h);x=max(0,min(w-cw,int(w*fx-cw/2)));y=max(0,min(h-ch,int(h*fy-ch/2)))
        sheet=Image.new('RGB',(cw*3,ch+45),'#eeeeee');draw=ImageDraw.Draw(sheet)
        for k,(a,label) in enumerate(zip(arrays,labels)):
            sheet.paste(Image.fromarray(np.asarray(a[y:y+ch,x:x+cw,:3])),(k*cw,45));draw.text((k*cw+12,15),label,fill='black')
        sheet.save(out/('Detail-'+title+'.jpg'),quality=97,subsampling=0)
    page='''<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Superresolution – Vergleich</title><style>body{font:16px system-ui;background:#16181d;color:#eee;margin:24px}a{color:#9cd8ff}select{font:inherit;padding:8px}#picture{max-width:100%;display:block;margin-top:15px}.detail{width:100%}p{max-width:900px}</style><h1>Superresolution – Vergleich</h1><p>Alle Varianten zeigen denselben Bildausschnitt. Keine Nachschärfung. Die Übersicht ist verkleinert; darunter stehen Detailausschnitte mit einem Bildpixel pro Dateipixel.</p><select id="choice"><option value="Einzelbild">Einzelbild – nur vergrößert und ausgerichtet</option><option value="Mittelwert" selected>Mittelwert</option><option value="Median">Median</option></select> <a id="full" href="Mittelwert.png">Volle Auflösung öffnen</a><img id="picture" src="Mittelwert-Vorschau.jpg"><h2>Details: Einzelbild | Mittelwert | Median</h2>'''
    for t in ['Mitte','Links','Rechts']:page+=f'<p>{t}</p><a href="Detail-{t}.jpg"><img class="detail" src="Detail-{t}.jpg"></a>'
    page+='''<script>document.getElementById('choice').onchange=e=>{document.getElementById('picture').src=e.target.value+'-Vorschau.jpg';document.getElementById('full').href=e.target.value+'.png'}</script></html>'''
    (out/'Vergleich.html').write_text(page)

def process(files,out,keep=False):
    start=time.monotonic();files=[p.resolve() for p in files]
    if len(files)<2:raise ValueError('Mindestens zwei Bilder desselben Motivs auswählen.')
    if len(set(files))!=len(files):raise ValueError('Ein Bild wurde doppelt ausgewählt.')
    if any(not p.is_file() or p.suffix.lower() not in EXT for p in files):raise ValueError('Unterstützt: JPEG, HEIC, PNG und TIFF.')
    binary=next(iter((ROOT/'tools').rglob('align_image_stack')),None)
    if binary is None:raise RuntimeError('Hugin-Werkzeug fehlt.')
    if out.exists():raise ValueError('Ergebnisordner existiert bereits. Bitte neuen Namen wählen.')
    out.mkdir(parents=True);log=out/'Verarbeitung.log'
    work=Path(tempfile.mkdtemp(prefix='arbeitsdateien-',dir=out))
    report={'sources':[str(p) for p in files],'scale_per_axis':2,'pixel_count_factor':4,'method':'ImageMagick default resize 200%, Hugin align_image_stack, equal RGB mean and median; no sharpening or brightness adjustment','status':'running'}
    try:
        sizes=[];resized=[]
        for i,p in enumerate(files):
            print(f'Bild {i+1}/{len(files)}: vergrößern …',flush=True)
            target=work/f'input-{i:03}.tif'
            run([MAGICK,'-limit','memory','512MiB','-limit','map','1GiB',p,'-auto-orient','-colorspace','sRGB','-alpha','off','-resize','200%','-depth','8','-compress','none',target],log)
            with Image.open(target) as im:sizes.append(im.size)
            resized.append(target)
        if len(set(sizes))!=1:raise ValueError('Die ausgewählten Bilder haben unterschiedliche Abmessungen.')
        print('Hugin richtet die vergrößerten Bilder aus …',flush=True)
        run([binary,'--align-to-first','-C','-m','-c','30','-g','5','-t','1','--corr=0.9','-s','1','-p',out/'Ausrichtung.pto','-a',str(work/'aligned-'),*resized],log)
        aligned=sorted(work.glob('aligned-*.tif'))
        if len(aligned)!=len(files):raise RuntimeError('Hugin hat nicht alle Bilder ausgegeben.')
        arrays=[];common=None
        for i,p in enumerate(aligned):
            with Image.open(p) as im:
                rgba=np.asarray(im.convert('RGBA'))
                valid=rgba[:,:,3]==255
                common=valid.copy() if common is None else common & valid
                np.save(work/f'aligned-{i}.npy',rgba[:,:,:3])
            arrays.append(np.load(work/f'aligned-{i}.npy',mmap_mode='r'))
        if len({a.shape for a in arrays})!=1:raise RuntimeError('Ausgerichtete Bildgrößen passen nicht zusammen.')
        ys,xs=np.where(common)
        if not len(xs):raise RuntimeError('Kein gemeinsamer Bildbereich.')
        x0,x1=int(xs.min()),int(xs.max())+1;y0,y1=int(ys.min()),int(ys.max())+1
        for _ in range(128):
            if common[y0:y1,x0:x1].all():break
            x0+=1;x1-=1;y0+=1;y1-=1
        else:raise RuntimeError('Kein sauberer gemeinsamer Ausschnitt. Bilder passen nicht ausreichend zusammen.')
        arrays=[a[y0:y1,x0:x1] for a in arrays]
        report['crop_xyxy']=[x0,y0,x1,y1]
        h,w=arrays[0].shape[:2]
        if w*h<.5*sizes[0][0]*sizes[0][1]:raise RuntimeError('Zu wenig gemeinsame Bildfläche. Bitte gleiche Blickrichtung verwenden.')
        print(f'Mittelwert und Median berechnen: {w} × {h} Pixel …',flush=True)
        mean,median=combine(arrays,work)
        for a,label in zip([arrays[0],mean,median],['Einzelbild','Mittelwert','Median']):
            im=Image.fromarray(np.asarray(a));im.save(out/(label+'.png'));im.save(out/(label+'.jpg'),quality=97,subsampling=0)
        write_comparison(out,[arrays[0],mean,median],['Einzelbild','Mittelwert','Median'])
        report.update(status='complete',width=w,height=h,megapixels=w*h/1e6,seconds=round(time.monotonic()-start,1),reference=str(files[0]))
        print(f'Fertig in {report["seconds"]:.0f} Sekunden. Ergebnis: {out}',flush=True)
    except BaseException as exc:
        report.update(status='cancelled' if isinstance(exc,KeyboardInterrupt) else 'failed',error=str(exc));raise
    finally:
        (out/'Bericht.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        if not keep:shutil.rmtree(work)
    return report

if __name__=='__main__':
    signal.signal(signal.SIGTERM,stop)
    parser=argparse.ArgumentParser();parser.add_argument('images',nargs='+',type=Path);parser.add_argument('--output',type=Path);parser.add_argument('--keep-work',action='store_true');args=parser.parse_args()
    files=args.images
    if len(files)==1 and files[0].is_dir():files=sorted(p for p in files[0].iterdir() if p.suffix.lower() in EXT)
    out=args.output or ROOT/'Ergebnisse'/time.strftime('%Y%m%d-%H%M%S')
    try:process(files,out,args.keep_work)
    except KeyboardInterrupt:print('Abgebrochen. Originale unverändert.',flush=True);sys.exit(130)
    except Exception as e:print('Fehler: '+str(e),flush=True);sys.exit(1)
