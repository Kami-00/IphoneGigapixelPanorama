from pathlib import Path
import subprocess,time,json,sys
from control import request
root=Path(__file__).resolve().parent
folder=Path(sys.argv[1]);dest=folder/'Entwickelt';dest.mkdir(exist_ok=True)
while True:
 for src in sorted(folder.glob('*.dng')):
  out=dest/(src.stem+'.png')
  if not out.exists():
   tmp=dest/(src.stem+'.tmp.png');subprocess.run([str(root/'tools/render_raw'),str(src),str(tmp)],check=True,timeout=180,capture_output=True);tmp.replace(out);print('Entwickelt',src.name,flush=True)
 state=request('/state')
 if not state['run'].get('active') and len(list(dest.glob('20*.png')))==len(list(folder.glob('*.dng'))):break
 time.sleep(2)
