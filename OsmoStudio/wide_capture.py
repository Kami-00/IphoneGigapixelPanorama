"""Feedback-driven wide capture: retain successful shots at reachable limits."""
import asyncio,time,math,json
from automation import delta
class WideCapture:
 def __init__(self,api):
  self.a=api;self.task=None;self.last=None;self.yaw=0.;self.session=None;self.gains={'yaw':-1.,'pitch':-1.};self.cancelled=False;self.shots=[];self.events=[]
 def abort(self):
  self.cancelled=True
  if self.task:self.task.cancel()
 def sample(self):
  m=self.a.motion_snapshot()
  if time.monotonic()-m.get('received',0)>2:raise RuntimeError('iPhone-Sensordaten fehlen – Bewegung gestoppt')
  if self.session and self.session!=m.get('sensor_session'):raise RuntimeError('Sensorbezug hat sich geändert')
  if self.last is not None:self.yaw+=delta(m['heading'],self.last)
  self.last=m['heading'];m['unwrapped_yaw']=self.yaw
  if abs(m['roll'])>25:raise RuntimeError('iPhone mehr als 25° seitlich geneigt – angehalten')
  return m
 async def stable(self):
  for _ in range(180):
   m=self.sample()
   if m.get('stable') and m['rate_dps']<.7:return m
   await asyncio.sleep(.1)
  raise RuntimeError('Aufnahme nicht ruhig genug')
 async def move(self,axis,command):
  before=await self.stable();await self.a.move(axis,command)
  await asyncio.sleep(.2);after=await self.stable()
  key='unwrapped_yaw' if axis=='yaw' else 'elevation';change=after[key]-before[key]
  if abs(change)>.5 and abs(command)>1:
   gain=change/command
   if .3<abs(gain)<2:self.gains[axis]=gain
  self.events.append({'axis':axis,'command':command,'measured_change':change,'motion':after})
  return before,after,change
 async def target(self,axis,target):
  key='unwrapped_yaw' if axis=='yaw' else 'elevation'
  for _ in range(48):
   m=await self.stable();error=target-m[key]
   if abs(error)<1.5:return True
   limit=18 if axis=='yaw' else 8
   command=max(-limit,min(limit,error/self.gains[axis]))
   before,after,change=await self.move(axis,command)
   if abs(change)<.35:
    self.events.append({'limit':axis,'requested':target,'reached':after[key]});return False
  return False
 async def capture(self,row):
  m=await self.stable();shot={'yaw':round(m['unwrapped_yaw'],3),'pitch':round(m['elevation'],3),'focus':-1,'repeat':0,'row':row}
  self.a.run_status(f'Großer Rundblick: Foto {len(self.shots)+1}, Höhenreihe {row+1}',len(self.shots),0)
  await self.a.capture_wait(shot,{'lock_exposure':False})
  self.shots.append(shot);self.save();self.a.run_status(f'{len(self.shots)} Originalfotos gespeichert',len(self.shots),0)
 def save(self):
  if self.a.RUN_DIR:(self.a.RUN_DIR/'aufnahmeprotokoll.json').write_text(json.dumps({'shots':self.shots,'events':self.events,'sensor_session':self.session},ensure_ascii=False,indent=2))
 async def run(self):
  success=False
  try:
   base=await self.stable();self.session=base['sensor_session'];base_pitch=base['elevation']
   self.a.run_status('Linken erreichbaren Schwenkrand bestimmen',0,0)
   # Stop immediately on the first ineffective step, never repeatedly push a limit.
   for _ in range(17):
    _,m,change=await self.move('yaw',-20)
    if abs(change)<.8:break
   left=self.yaw
   await self.target('yaw',left-4);left=self.yaw
   await self.capture(0);last_capture=self.yaw
   self.a.run_status('Horizontalen Rundblick aufnehmen',len(self.shots),0)
   for _ in range(18):
    _,m,change=await self.move('yaw',20)
    if abs(self.yaw-last_capture)>=34:
     await self.capture(0);last_capture=self.yaw
    if abs(change)<.8:break
   right=self.yaw
   await self.target('yaw',right+4);right=self.yaw
   if abs(self.yaw-last_capture)>12:await self.capture(0)
   centre=(left+right)/2
   steps=max(1,math.ceil((left-right)/35));positions=[right+(left-right)*i/steps for i in range(steps+1)]
   for row,offset in [(1,50),(2,-50)]:
    self.a.run_status(f'Höhenreihe {row+1} vorbereiten',len(self.shots),0)
    await self.target('yaw',centre)
    await self.target('pitch',max(-75,min(75,base_pitch+offset)))
    pitch=(await self.stable())['elevation']
    if abs(pitch-base_pitch)<12:
     self.events.append({'row_skipped':row,'reason':'Höhenbewegung zu klein','pitch':pitch});continue
    for yaw in (positions if row==1 else list(reversed(positions))):
     await self.target('yaw',yaw)
     await self.target('pitch',pitch)
     # Each pose is recorded with actual sensor angles, never assumed target angles.
     await self.capture(row)
   self.a.run_status('Zur Ausgangsrichtung zurückkehren',len(self.shots),len(self.shots))
   await self.target('yaw',0);await self.target('pitch',base_pitch)
   self.a.run_status('Aufnahmen fertig – 360°-Berechnung vorbereitet',len(self.shots),len(self.shots));success=True
  except asyncio.CancelledError:self.a.run_status('Aufnahme abgebrochen; Originale gespeichert',len(self.shots),len(self.shots))
  except Exception as exc:self.a.run_status(str(exc)+'; Originale gespeichert',len(self.shots),len(self.shots))
  finally:
   self.save()
   if self.a.CLIENT and self.a.CLIENT.is_connected:await self.a.stop()
   if success:
    try:await self.a.export_wide(self.a.RUN_DIR)
    except asyncio.CancelledError:self.a.run_status('Berechnung abgebrochen; Originale gespeichert',None,None)
    except Exception as exc:self.a.run_status(str(exc),None,None)
   self.a.RUN['active']=False;self.a.EVENT=self.a.RUN['message']
   if self.a.RUN_DIR:(self.a.RUN_DIR/'reihe.json').write_text(json.dumps(self.a.RUN,ensure_ascii=False,indent=2))
   self.a.RUN_DIR=None
