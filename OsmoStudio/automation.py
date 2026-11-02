"""Bounded closed-loop capture controller. No motion without fresh iPhone data."""
import asyncio,math,time

def delta(a,b):return (a-b+180)%360-180

def plan(config):
    mode=config.get('mode','focus')
    half=float(config.get('half_span',30));step=float(config.get('step',20));pitch=float(config.get('pitch_span',15));count=int(config.get('focus_count',3));lo=float(config.get('focus_near',.35));hi=float(config.get('focus_far',.9));repeat=int(config.get('repeat',1))
    if mode not in ('focus','panorama'):raise ValueError('Unbekannter Modus')
    if not all(math.isfinite(x) for x in [half,step,pitch,lo,hi]) or not (0<=half<=100 and 10<=step<=40 and 0<=pitch<=30 and 1<=count<=7 and 0<=lo<=hi<=1 and 1<=repeat<=3):raise ValueError('Ungültige Aufnahmeparameter')
    focuses=[-1] if count==1 else [lo+(hi-lo)*i/(count-1) for i in range(count)]
    if mode=='focus':positions=[(0.,0.)]
    else:
        columns=max(1,math.ceil(2*half/step));ys=[-half+2*half*i/columns for i in range(columns+1)] if half else [0.]
        ps=[0.,pitch,-pitch] if pitch else [0.]
        positions=[(y,p) for k,p in enumerate(ps) for y in (ys if k%2==0 else list(reversed(ys)))]
    shots=[{'yaw':y,'pitch':p,'focus':f,'repeat':r} for y,p in positions for f in focuses for r in range(repeat)]
    if len(shots)>300:raise ValueError('Maximal 300 Aufnahmen pro Reihe')
    return shots

class Controller:
    def __init__(self,snapshot,send,capture,status,finish):
        self.snapshot=snapshot;self.send=send;self.capture=capture;self.status=status;self.finish=finish;self.gains={};self.session=None;self.task=None;self.cancelled=False
    def sample(self):
        m=self.snapshot()
        if time.monotonic()-m.get('received',0)>1.5:raise RuntimeError('Gyrodaten fehlen/zu alt – gestoppt')
        if not all(isinstance(m.get(k),(int,float)) and math.isfinite(m[k]) for k in ('heading','roll','elevation','rate_dps','acceleration_g')):raise RuntimeError('Ungültige Gyrodaten')
        if self.session is not None and m.get('sensor_session')!=self.session:raise RuntimeError('iPhone-Sensor neu gestartet – neue Startposition nötig')
        if self.cancelled:raise RuntimeError('Abgebrochen')
        return m
    async def stable(self):
        for _ in range(120):
            m=self.sample()
            if m.get('stable') and m['rate_dps']<.7 and m['acceleration_g']<.025:return m
            await asyncio.sleep(.1)
        raise RuntimeError('Gimbal kommt nicht zur Ruhe – gestoppt')
    async def pulse(self,axis,degrees):
        self.sample()
        limit=3 if axis=='roll' else 10
        if not math.isfinite(degrees) or abs(degrees)>limit:raise RuntimeError('Korrekturschritt zu groß')
        await self.send(axis,degrees)
        # A commanded relative step is short, then explicitly stop; never drive into a stop.
        for _ in range(2):await asyncio.sleep(.1);self.sample()
        return await self.stable()
    async def calibrate(self,axis,key):
        before=(await self.stable())[key]
        after=(await self.pulse(axis,2))[key];change=delta(after,before)
        if not .35<abs(change)<6:raise RuntimeError(f'{axis}: keine verlässliche Reaktion auf 2°-Test; gestoppt')
        self.gains[axis]=change/2
        await self.target(axis,key,before,tolerance=.7,max_steps=4)
    async def target(self,axis,key,value,tolerance=1.0,max_steps=20):
        previous=None;bad=0
        for _ in range(max_steps):
            m=await self.stable();error=delta(value,m[key])
            if abs(error)<=tolerance:return
            if previous is not None and abs(error)>previous-.15:bad+=1
            else:bad=0
            if bad>=2:raise RuntimeError(f'{axis}: Ziel nicht erreichbar / mechanische Grenze – gestoppt')
            previous=abs(error)
            limit=2 if axis=='roll' else 8
            command=max(-limit,min(limit,error/self.gains[axis]))
            await self.pulse(axis,command)
        raise RuntimeError(f'{axis}: Ziel innerhalb der begrenzten Schritte nicht erreicht')
    async def level(self,strict=False):
        m=await self.stable()
        if not strict:
            if abs(m['roll'])<=5:return
            raise RuntimeError('iPhone mehr als 5° schräg. Halterung etwas gerader stellen; kleine Neigungen werden im Panorama ausgeglichen.')
        if abs(m['roll'])<=1:return
        if abs(m['roll'])>12:raise RuntimeError('iPhone mehr als 12° schräg. Halterung zuerst aufrecht ausrichten.')
        if 'roll' not in self.gains:await self.calibrate('roll','roll')
        await self.target('roll','roll',0,tolerance=1,max_steps=8)
    async def run(self,config,shots):
        self.cancelled=False;self.gains={};base=None
        try:
            m=await self.stable();self.session=m.get('sensor_session');base=dict(m)
            self.status('Ausrichten und Sensorreaktion prüfen',0,len(shots))
            await self.level(strict=config.get('mode')=='level')
            if config.get('mode')=='level':
                self.status('Gerade: weniger als 1° Neigung',0,0);return
            if config.get('mode')=='panorama':
                await self.calibrate('yaw','heading')
                if config.get('pitch_span',15):await self.calibrate('pitch','elevation')
            base=dict(await self.stable());last=None
            for i,shot in enumerate(shots):
                self.status(f'Aufnahme {i+1}/{len(shots)} vorbereiten',i,len(shots))
                position=(shot['yaw'],shot['pitch'])
                if config.get('mode')=='panorama' and position!=last:
                    await self.target('yaw','heading',base['heading']+shot['yaw'])
                    if 'pitch' in self.gains:await self.target('pitch','elevation',base['elevation']+shot['pitch'])
                    await self.level();last=position
                await self.stable()
                await self.capture(shot,config)
                self.status(f'{i+1}/{len(shots)} ProRAW-Fotos gespeichert',i+1,len(shots))
            if config.get('mode')=='panorama':
                self.status('Zur gemessenen Startposition zurückkehren',len(shots),len(shots))
                await self.target('yaw','heading',base['heading'])
                if 'pitch' in self.gains:await self.target('pitch','elevation',base['elevation'])
                await self.level()
            self.status('Fertig',len(shots),len(shots))
        except asyncio.CancelledError:self.status('Abgebrochen – laufende Fotodatei kann noch ankommen',None,None)
        except Exception as exc:self.status(str(exc),None,None)
        finally:
            await self.finish();self.session=None
    def abort(self):
        self.cancelled=True
        if self.task:self.task.cancel()
