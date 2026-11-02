"""User-requested bounded end-position test, using live phone feedback."""
import time,json
from pathlib import Path
from control import request
from automation import delta
out=Path('photos/Endpositionen-Test');out.mkdir(exist_ok=True)
def sample():
 s=request('/state')
 if not s['motion_fresh']:raise RuntimeError('Keine aktuellen Sensordaten')
 if s['run']['active']:raise RuntimeError('Andere Reihe läuft')
 return s['motion']
def stable():
 for _ in range(50):
  m=sample()
  if m['stable']:return m
  time.sleep(.1)
 raise RuntimeError('Nicht ruhig')
def photo(label):
 prev=request('/state')['latest'];m=stable();job=request('/capture',{})
 for _ in range(180):
  s=request('/state')
  if s['latest']!=prev:
   result={'label':label,'photo':s['latest'],'motion':m};print(json.dumps(result),flush=True);return result
  if s['event'].startswith('iPhone:'):raise RuntimeError(s['event'])
  time.sleep(.5)
 raise RuntimeError('Foto fehlt')
start=stable();records=[]
try:
 for label,sign in [('links',-1),('rechts',1)]:
  travelled=0
  for i in range(18):
   before=stable();request('/move',{'axis':'yaw','degrees':sign*20});after=stable();change=delta(after['heading'],before['heading']);travelled+=change
   print(label,i+1,'Änderung',round(change,2),'gesamt',round(travelled,2),flush=True)
   if abs(change)<.8:break
  request('/stop',{});records.append(photo(label));(out/'test.json').write_text(json.dumps({'start':start,'positions':records},indent=2))
 # Shortest measured return, bounded and stop on first ineffective command.
 for _ in range(18):
  m=stable();error=delta(start['heading'],m['heading'])
  if abs(error)<1:break
  request('/move',{'axis':'yaw','degrees':-max(-20,min(20,error))});after=stable()
  if abs(delta(after['heading'],m['heading']))<.5:break
finally:request('/stop',{})
