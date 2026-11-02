from pathlib import Path
import sys,json,numpy as np,cv2 as cv
from PIL import Image,ImageDraw
# Historical comparison helper; requires the matching three-shot dataset.
if len(sys.argv)!=3:raise SystemExit('Aufruf: compare_previous.py NEUER_ERGEBNISORDNER ALTER_ERGEBNISORDNER')
out=Path(sys.argv[1]);oldroot=Path(sys.argv[2])
meta=json.loads((oldroot/'bericht.json').read_text());H=np.array(meta['alignment'][1]['reference_to_source_2x'])
# Previous result is in view A. New Hugin reference is view C, cropped by (39,23).
# Apply the recorded A->C registration to compare matching content; old output
# necessarily receives one extra cubic resampling, documented in the caption.
old=cv.imread(str(oldroot/'Stack-3-2x.png'));arrays=[cv.imread(str(out/(s+'.png'))) for s in ['Einzelbild','Mittelwert','Median']]
for name,x,y in [('Schrift',2350,2920),('Suits',1200,2650)]:
 w,h=650,600;T=np.array([[1.,0,x+39],[0,1.,y+23],[0,0,1.]])
 prev=cv.warpPerspective(old,np.linalg.inv(H)@T,(w,h),flags=cv.INTER_CUBIC|cv.WARP_INVERSE_MAP)
 ims=[arrays[0][y:y+h,x:x+w],prev,arrays[1][y:y+h,x:x+w],arrays[2][y:y+h,x:x+w]]
 sheet=Image.new('RGB',(4*w,h+65),'#eeeeee');d=ImageDraw.Draw(sheet)
 for i,(a,label) in enumerate(zip(ims,['Einzelbild C','Bisheriger Stack (geometrisch angepasst)','Hugin: Mittelwert','Hugin: Median'])):
  sheet.paste(Image.fromarray(cv.cvtColor(a,cv.COLOR_BGR2RGB)),(i*w,65));d.text((i*w+12,12),label,fill='black')
 sheet.save(out/('Bisher-vs-Hugin-'+name+'.jpg'),quality=97,subsampling=0)
p=out/'Vergleich.html';s=p.read_text().replace('<h2>Details:', '<h2>Vergleich zum bisherigen Test</h2><p>Links das Einzelbild C, daneben der bisherige Stack, dann die beiden neuen Ergebnisse. Der alte Stack wurde für denselben Bildausschnitt einmal zusätzlich bikubisch ausgerichtet. Keine Nachschärfung.</p><a href="Bisher-vs-Hugin-Schrift.jpg"><img class="detail" src="Bisher-vs-Hugin-Schrift.jpg"></a><a href="Bisher-vs-Hugin-Suits.jpg"><img class="detail" src="Bisher-vs-Hugin-Suits.jpg"></a><h2>Details:');p.write_text(s)
