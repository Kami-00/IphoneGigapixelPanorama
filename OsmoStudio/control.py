"""Local diagnostic client; credentials never printed."""
import json,urllib.request,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def request(path,body=None):
 s=json.loads((ROOT/'session.json').read_text());r=urllib.request.Request('http://127.0.0.1:'+str(s['port'])+path,data=None if body is None else json.dumps(body).encode(),headers={'Authorization':'Bearer '+s['token'],'Content-Type':'application/json'})
 try:return json.load(urllib.request.urlopen(r,timeout=30))
 except urllib.error.HTTPError as e:raise RuntimeError(e.read().decode()) from None
if __name__=='__main__':
 d=request(sys.argv[1] if len(sys.argv)>1 else '/state',json.loads(sys.argv[2]) if len(sys.argv)>2 else None)
 print(json.dumps(d,ensure_ascii=False,indent=2))
