"""Local Mac/iPhone bridge; no cloud, no movement on startup."""
import asyncio,threading,json,secrets,time,uuid,struct,sys,io,os,argparse,signal,math,shutil,subprocess
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'deps'))
TOKEN=secrets.token_urlsafe(32);LOCK=threading.RLock();JOBS={};PHONE={'seen':0,'name':'','resolution':''};LATEST='';DEVICE='';EVENT='Bereit';CLIENT=None;LOOP=None;MOVING=False
UPLOAD_LOCK=threading.Lock()
MOTION={};RUN={'active':False,'done':0,'total':0,'message':'Bereit'};CONTROLLER=None;RUN_DIR=None
PHOTOS=ROOT/'photos';PHOTOS.mkdir(exist_ok=True)
WRITE='0000fff5-0000-1000-8000-00805f9b34fb'
def packet(yaw=0,pitch=0,mode=4,duration=10,roll=0):
    if not(-200<=yaw<=200 and -100<=pitch<=100 and -30<=roll<=30):raise ValueError('Schritt zu groß')
    body=bytes([2,4,1,0,0,4,12 if mode==128 else 20])+struct.pack('<hhhBB',yaw,roll,pitch,mode,duration)
    crc=0xdf0c
    for b in body:
        crc^=b
        for _ in range(8):crc=(crc>>1)^0x8408 if crc&1 else crc>>1
    return bytes.fromhex('551504a9')+body+struct.pack('<H',crc)
async def connect_gimbal():
    global CLIENT,DEVICE,EVENT
    if CLIENT and CLIENT.is_connected:return
    from bleak import BleakClient,BleakScanner
    from bleak.backends.device import BLEDevice
    from bleak.backends.corebluetooth.CentralManagerDelegate import CentralManagerDelegate
    from CoreBluetooth import CBUUID
    manager=CentralManagerDelegate();await manager.wait_until_ready()
    ps=manager.central_manager.retrieveConnectedPeripheralsWithServices_([CBUUID.UUIDWithString_('FFF0')])
    choices=[BLEDevice(str(p.identifier().UUIDString()),str(p.name()),(p,manager)) for p in ps if str(p.name()).startswith('OM3')]
    if not choices:
        ds=await BleakScanner.discover(timeout=5);choices=[d for d in ds if (d.name or '').startswith('OM3')]
    if len(choices)!=1:raise ValueError('Kein eindeutiger OM3 gefunden. Einschalten und mit dem Mac verbinden.')
    client=BleakClient(choices[0],timeout=12);await client.connect()
    if not client.services.get_characteristic(WRITE):
        await client.disconnect();raise ValueError('OM3-Steuerungsschnittstelle fehlt')
    CLIENT=client;DEVICE=choices[0].name;EVENT='Gimbal verbunden; Winkel sind noch nicht kalibriert'
async def send(yaw=0,pitch=0,mode=4,duration=10,roll=0):
    if not CLIENT or not CLIENT.is_connected:raise ValueError('Gimbal nicht verbunden')
    data=packet(yaw,pitch,mode,duration,roll)
    for i in range(0,len(data),20):await CLIENT.write_gatt_char(WRITE,data[i:i+20],response=False)
async def move(axis,degrees):
    global MOVING,EVENT
    if MOVING:raise ValueError('Eine Bewegung läuft bereits')
    if axis not in ('yaw','pitch','roll') or not isinstance(degrees,(float,int)) or not 0<abs(degrees)<= (20 if axis=='yaw' else (3 if axis=='roll' else 10)):raise ValueError('Ungültiger Bewegungsschritt')
    MOVING=True
    try:
        await send(round(degrees*10) if axis=='yaw' else 0,round(degrees*10) if axis=='pitch' else 0,duration=15,roll=round(degrees*10) if axis=='roll' else 0)
        EVENT=f'Bewegungsbefehl {degrees:g}° gesendet (Istwinkel unbestätigt)'
        await asyncio.sleep(1.7)
    finally:
        try:await send(mode=128,duration=1)
        finally:MOVING=False
async def stop():
    global EVENT
    await send(mode=128,duration=1);EVENT='Stoppbefehl gesendet'
def ble_run(coro):return asyncio.run_coroutine_threadsafe(coro,LOOP).result(timeout=22)
def enqueue_capture(focus=-1,lock_exposure=False,context=None):
    if not isinstance(focus,(int,float)) or not (focus==-1 or 0<=focus<=1):raise ValueError('Ungültiger Fokus')
    with LOCK:
        if time.time()-PHONE['seen']>5:raise ValueError('iPhone-App ist nicht verbunden oder nicht im Vordergrund')
        if any(j['status'] in ('pending','delivered') and time.time()<j['expires'] for j in JOBS.values()):raise ValueError('Eine Aufnahme läuft bereits')
        tele=(context or {}).get('camera')=='tele'
        if tele:
            if PHONE.get('camera')!='tele' or not PHONE.get('raw_ready'):raise ValueError('3×-Telekamera nicht bereit')
        elif not PHONE.get('proraw48'):raise ValueError('iPhone meldet kein 48-MP-ProRAW')
        ident=uuid.uuid4().hex;JOBS[ident]={'id':ident,'kind':'capture','focus':focus,'lock_exposure':bool(lock_exposure),'status':'pending','expires':time.time()+180,'format':'proraw12tele' if tele else 'proraw48','context':context or {},'folder':str(RUN_DIR or PHOTOS)}
        return ident
def next_job():
    with LOCK:
        PHONE['seen']=time.time()
        for j in JOBS.values():
            if time.time()>j['expires'] and j['status'] in ('pending','delivered'):j['status']='expired'
            if j['status']=='pending':j['status']='delivered';return dict(j)
    return {}
def store_photo(ident,data):
    global LATEST,EVENT
    with UPLOAD_LOCK:
        job=JOBS.get(ident)
        if not job:raise ValueError('Unbekannte Aufnahme')
        if job['status']=='complete':return job['file']
        if job['status']!='delivered':raise ValueError('Aufnahme ist nicht mehr aktiv')
        if data[:4] not in (b'II\x2a\x00',b'MM\x00\x2a'):raise ValueError('Echte DNG-Datei erwartet')
        if not job.get('metadata'):raise ValueError('Aufnahmemetadaten fehlen')
        folder=Path(job['folder']);folder.mkdir(exist_ok=True,parents=True)
        if shutil.disk_usage(folder).free<len(data)+500_000_000:raise ValueError('Zu wenig freier Speicherplatz')
        name=time.strftime('%Y%m%d-%H%M%S')+'-'+ident[:8]+'.dng';dest=folder/name;tmp=dest.with_suffix('.tmp');tmp.write_bytes(data)
        try:
            result=subprocess.run(['/opt/homebrew/bin/exiftool','-j','-G1','-a','-DNGVersion','-ImageWidth','-ImageHeight',str(tmp)],capture_output=True,text=True,timeout=20,check=True)
            tags=json.loads(result.stdout)[0]
            if not any(k.endswith(':DNGVersion') for k in tags):raise ValueError('Keine gültige DNG-Datei')
            dims=[(int(v),int(tags.get(k.replace('ImageWidth','ImageHeight'),0))) for k,v in tags.items() if k.endswith(':ImageWidth')]
            w,h=max(dims,key=lambda d:d[0]*d[1],default=(0,0))
            minimum=12_000_000 if job['format']=='proraw12tele' else 48_000_000
            if w*h<minimum:raise ValueError(f'DNG hat nur {w} × {h} Pixel; {minimum//1_000_000} MP erforderlich')
            if job['format']=='proraw12tele':
                meta=job['metadata']
                if meta.get('camera')!='tele' or meta.get('physical_camera')!='AVCaptureDeviceTypeBuiltInTelephotoCamera' or meta.get('zoom_factor')!=1:raise ValueError('Echte Telekamera ohne Digitalzoom nicht nachgewiesen')
            tmp.replace(dest)
            meta=dict(job['metadata']);meta.update({'capture_id':ident,'verified_dng_dimensions':[w,h],'request':job['context'],'requested_focus':job['focus'],'stored_at':time.time()})
            dest.with_suffix('.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2,allow_nan=False))
            job.update(status='complete',file=str(dest),width=w,height=h);LATEST=str(dest);EVENT=f'ProRAW gespeichert: {w} × {h} Pixel';return str(dest)
        finally:tmp.unlink(missing_ok=True)

async def automation_send(axis,degrees):
    await move(axis,degrees)
def motion_snapshot():
    with LOCK:return dict(MOTION)
def run_status(message,done,total):
    global EVENT
    with LOCK:
        RUN['message']=message;EVENT=message
        if done is not None:RUN['done']=done
        if total is not None:RUN['total']=total
async def capture_wait(shot,config):
    ident=enqueue_capture(shot['focus'],config.get('lock_exposure',True),dict(shot,pass_index=RUN.get('pass_index',1),camera=config.get('camera','wide')))
    for _ in range(1800):
        if time.monotonic()-MOTION.get('received',0)>3:raise RuntimeError('iPhone-Verbindung während Aufnahme unterbrochen')
        j=JOBS[ident]
        if j['status']=='complete':return
        if j['status'] in ('failed','expired'):raise RuntimeError(j.get('error','Aufnahme fehlgeschlagen'))
        await asyncio.sleep(.1)
    raise RuntimeError('Fotoübertragung dauert zu lange; Reihe gestoppt')
async def process_run_folder(folder):
    from processing import process
    run_status('RAW entwickeln und Panorama zusammensetzen …',None,None)
    result=await asyncio.to_thread(process,folder)
    RUN['panorama']=result['file'];RUN['complete_360']=False
    run_status('Panorama fertig (Teilansicht)',None,None)
async def finish_run():
    global RUN_DIR,EVENT
    folder=RUN_DIR
    try:
        if CLIENT and CLIENT.is_connected:await stop()
        if folder and RUN.get('config',{}).get('two_pass') and RUN.get('pass_index')==1 and RUN['message']=='Fertig':
            RUN['awaiting_turn']=True
            RUN['turn_heading']=motion_snapshot().get('heading')
            RUN['sensor_session']=motion_snapshot().get('sensor_session')
            run_status('Durchgang 1 fertig. Gimbal samt Griff am gleichen Standort um 180° drehen, dann Durchgang 2 starten.',None,None)
        elif folder and RUN.get('config',{}).get('mode')=='panorama' and RUN['message']=='Fertig':
            try:await process_run_folder(folder)
            except Exception as exc:run_status('Fotos gespeichert; Panorama: '+str(exc),None,None)
    finally:
        with LOCK:
            RUN['active']=False;EVENT=RUN['message']
            for j in JOBS.values():
                if j['status']=='pending':j['status']='expired'
            if folder:(folder/'reihe.json').write_text(json.dumps(RUN,ensure_ascii=False,indent=2))
            RUN_DIR=None
async def process_latest():
    if RUN['active'] or MOVING:raise ValueError('Laufende Reihe zuerst beenden')
    folders=sorted(PHOTOS.glob('Reihe-*'),reverse=True)
    folder=next((p for p in folders if (p/'reihe.json').exists() and json.loads((p/'reihe.json').read_text()).get('config',{}).get('mode')=='panorama'),None)
    if not folder:raise ValueError('Noch keine Panorama-Reihe vorhanden')
    RUN.update(active=True,folder=str(folder),message='Panorama wird berechnet')
    async def work():
        global EVENT
        try:await process_run_folder(folder)
        except Exception as exc:run_status(str(exc),None,None)
        finally:RUN['active']=False;EVENT=RUN['message']
    asyncio.create_task(work())
async def start_run(config,resume=False):
    global CONTROLLER,RUN_DIR
    from automation import Controller,plan
    if RUN['active'] or MOVING:raise ValueError('Eine Bewegung oder Reihe läuft bereits')
    if any(j['status'] in ('pending','delivered') and j['expires']>time.time() for j in JOBS.values()):raise ValueError('Fotoaufnahme läuft bereits')
    if not CLIENT or not CLIENT.is_connected:raise ValueError('Gimbal zuerst verbinden')
    shots=[] if config.get('mode')=='level' else plan(config)
    if shots:
        if config.get('camera')=='tele':
            if PHONE.get('camera')!='tele' or not PHONE.get('raw_ready'):raise ValueError('3×-Telekamera noch nicht bereit')
        elif not PHONE.get('proraw48'):raise ValueError('48-MP-ProRAW noch nicht bereit')
    if shutil.disk_usage(PHOTOS).free<len(shots)*130_000_000+1_000_000_000:raise ValueError('Nicht genug Speicher für diese Reihe (Planung mit 130 MB je Foto)')
    controller=Controller(motion_snapshot,automation_send,capture_wait,run_status,finish_run);controller.sample()
    if resume:
        RUN_DIR=Path(RUN['folder']);RUN.update(awaiting_turn=False,pass_index=2)
    else:
        if RUN.get('awaiting_turn'):raise ValueError('Durchgang 2 fortsetzen oder die wartende Reihe mit STOPP beenden')
        RUN_DIR=PHOTOS/('Reihe-'+time.strftime('%Y%m%d-%H%M%S'));RUN_DIR.mkdir(exist_ok=True)
        RUN.clear();RUN.update(pass_index=1,awaiting_turn=False)
    RUN.update(active=True,done=0,total=len(shots),message='Start',config=config,folder=str(RUN_DIR));CONTROLLER=controller
    controller.task=asyncio.create_task(controller.run(config,shots))
def tele_grid_config(phone,overlap=.25):
    if phone.get('camera')!='tele' or phone.get('physical_camera')!='AVCaptureDeviceTypeBuiltInTelephotoCamera' or phone.get('zoom_factor')!=1 or not phone.get('raw_ready'):
        raise ValueError('Physische 3×-Telekamera nicht bestätigt')
    h=phone.get('portrait_hfov',0);v=phone.get('portrait_vfov',0)
    if not all(isinstance(x,(float,int)) and math.isfinite(x) for x in (h,v,overlap)) or not (10<h<40 and h<v<50 and .2<=overlap<=.4):raise ValueError('Unplausibler Tele-Bildwinkel')
    # Fraction of angular field, with 25% as the initial requested low-overlap setting.
    step=h*(1-overlap);pitch=v*(1-overlap)
    if step<10 or pitch>30:raise ValueError('Bildwinkel außerhalb des geprüften 3×3-Bereichs')
    return dict(mode='panorama',camera='tele',half_span=step,step=step,pitch_span=pitch,focus_count=1,repeat=1,lock_exposure=False,two_pass=False,overlap=overlap,source_hfov=h,source_vfov=v)

async def configure_camera(name):
    if name not in ('wide','tele'):raise ValueError('Unbekannte Kamera')
    if RUN.get('active') or RUN.get('awaiting_turn') or MOVING:raise ValueError('Laufende Reihe zuerst beenden')
    if time.time()-PHONE['seen']>5:raise ValueError('iPhone im neuen WLAN verbinden')
    if PHONE.get('protocol_version',0)<3:raise ValueError('Neue iPhone-App für 3× installieren')
    if any(j['status'] in ('pending','delivered') and j['expires']>time.time() for j in JOBS.values()):raise ValueError('Kameraauftrag läuft bereits')
    ident=uuid.uuid4().hex;JOBS[ident]=dict(id=ident,kind='camera',camera=name,status='pending',expires=time.time()+18)
    RUN['active']=True;run_status('Physische Kamera umstellen …',None,None)
    try:
        for _ in range(170):
            job=JOBS[ident]
            if job['status']=='complete':return
            if job['status'] in ('failed','expired'):raise RuntimeError(job.get('error','Kamerawechsel abgebrochen'))
            await asyncio.sleep(.1)
        raise RuntimeError('iPhone bestätigt Kamerawechsel nicht')
    finally:
        if JOBS[ident]['status'] in ('pending','delivered'):JOBS[ident]['status']='expired'
        RUN['active']=False

async def start_tele_grid():
    if not CLIENT or not CLIENT.is_connected:raise ValueError('Gimbal zuerst verbinden')
    await configure_camera('tele')
    await start_run(tele_grid_config(PHONE))

async def export_wide(folder):
    run_status('360°-Bild in voller Auflösung berechnen; fehlende Bereiche bleiben schwarz …',None,None)
    log_path=folder/'360-Berechnung.log'
    with log_path.open('wb') as log:
        args=[sys.executable,str(ROOT/'spherical_export.py'),str(folder)]
        if (folder/'360-Kalibrierung.json').exists():args.append('--resume')
        process=await asyncio.create_subprocess_exec(*args,stdout=log,stderr=log)
        try:
            code=await process.wait()
        except asyncio.CancelledError:
            process.terminate();await process.wait();raise
    if code:raise RuntimeError('360°-Berechnung fehlgeschlagen; Details in 360-Berechnung.log. Originale sind gespeichert.')
    result=json.loads((folder/'360-Ergebnis.json').read_text())
    viewer=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'make_360_viewer.py'),str(folder),stdout=asyncio.subprocess.DEVNULL)
    await viewer.wait()
    RUN['panorama']=result['jpg'];RUN['viewer']=str(folder/'360-Ansicht.html');RUN['complete_360']=False;RUN['full_sphere_canvas']=True;RUN['black_unseen_percent']=result['black_unseen_percent']
    run_status(f"360° fertig: {result['width']} × {result['height']} Pixel; nicht fotografierte Bereiche schwarz",None,None)
async def start_wide():
    global CONTROLLER,RUN_DIR
    from wide_capture import WideCapture
    if RUN.get('active') or MOVING:raise ValueError('Eine Reihe läuft bereits')
    if any(j['status'] in ('pending','delivered') and j['expires']>time.time() for j in JOBS.values()):raise ValueError('Fotoaufnahme läuft bereits')
    if not CLIENT or not CLIENT.is_connected:raise ValueError('Gimbal fehlt')
    if not PHONE.get('proraw48') or time.time()-PHONE['seen']>5:raise ValueError('iPhone fehlt')
    if shutil.disk_usage(PHOTOS).free<12_000_000_000:raise ValueError('Mindestens 12 GB freier Speicher benötigt')
    controller=WideCapture(sys.modules[__name__]);controller.sample()
    RUN_DIR=PHOTOS/('Rundblick-'+time.strftime('%Y%m%d-%H%M%S'));RUN_DIR.mkdir()
    RUN.clear();RUN.update(active=True,done=0,total=0,message='Großer Rundblick beginnt',config={'mode':'wide'},folder=str(RUN_DIR),pass_index=1)
    CONTROLLER=controller;controller.task=asyncio.create_task(controller.run())
async def continue_run():
    from automation import delta
    if not RUN.get('awaiting_turn'):raise ValueError('Kein zweiter Durchgang wartet')
    m=motion_snapshot()
    if time.monotonic()-m.get('received',0)>1.5:raise ValueError('Aktuelle Sensordaten fehlen')
    if m.get('sensor_session')!=RUN.get('sensor_session'):raise ValueError('iPhone-Sensor wurde neu gestartet. Rundumreihe bitte neu beginnen.')
    angle=abs(delta(m['heading'],RUN['turn_heading']))
    if angle<155:raise ValueError(f'Erst den Griff um etwa 180° drehen; bisher sind es {angle:.0f}°')
    await start_run(dict(RUN['config']),resume=True)
async def abort_run():
    for job in JOBS.values():
        if job.get('kind')=='camera' and job['status'] in ('pending','delivered'):
            job['status']='expired';run_status('Kamerawechsel abgebrochen',None,None)
    if RUN.get('awaiting_turn'):
        RUN['awaiting_turn']=False;run_status('Rundumreihe beendet; bisherige Fotos bleiben gespeichert',None,None)
    if CONTROLLER:CONTROLLER.abort()
    if CLIENT and CLIENT.is_connected:await stop()

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self,code,data):
        raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def handle_request(self):
        global EVENT
        path=urlsplit(self.path).path
        if not secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+TOKEN):return self.respond(401,{'error':'Nicht autorisiert'})
        if not path.startswith('/phone/') and self.client_address[0] not in ('127.0.0.1','::1'):return self.respond(403,{'error':'Nur auf diesem Mac verfügbar'})
        try:
            length=int(self.headers.get('Content-Length',0))
            if length<0 or length>180_000_000:raise ValueError('Anfrage zu groß')
            if path=='/phone/photo' and self.command=='POST':
                return self.respond(200,{'file':store_photo(self.headers.get('X-Capture-ID',''),self.rfile.read(length))})
            if length>150_000:raise ValueError('Anfrage zu groß')
            body=json.loads(self.rfile.read(length)) if length else {}
            if path=='/phone/motion' and self.command=='POST':
                if any(not isinstance(body.get(k),(int,float)) or not math.isfinite(body[k]) for k in ('timestamp','heading','roll','elevation','rate_dps','acceleration_g')):raise ValueError('Ungültige Sensordaten')
                with LOCK:
                    if body.get('sensor_session')==MOTION.get('sensor_session') and body['timestamp']<=MOTION.get('timestamp',-1):raise ValueError('Veraltetes Sensorpaket')
                    MOTION.clear();MOTION.update(body,received=time.monotonic());PHONE['seen']=time.time()
                return self.respond(200,{'ok':True})
            if path=='/phone/metadata' and self.command=='POST':
                with LOCK:
                    j=JOBS.get(body.get('id'))
                    if not j or j['status']!='delivered':raise ValueError('Unbekannte Aufnahme')
                    meta=body.get('metadata')
                    if not isinstance(meta,dict):raise ValueError('Ungültige Metadaten')
                    json.dumps(meta,allow_nan=False);j['metadata']=meta
                return self.respond(200,{'ok':True})
            if path=='/phone/configured' and self.command=='POST':
                with LOCK:
                    job=JOBS.get(body.get('id'))
                    if not job or job.get('kind')!='camera' or job['status']!='delivered':raise ValueError('Kein aktiver Kamerawechsel')
                    if body.get('camera')!=job['camera']:raise ValueError('Falsche Kamera bestätigt')
                    PHONE.update({k:body.get(k) for k in ('camera','physical_camera','zoom_factor','raw_ready','photo_width','photo_height','portrait_hfov','portrait_vfov')})
                    PHONE.update(proraw48=body.get('camera')=='wide' and body.get('raw_ready') is True and body.get('photo_width',0)*body.get('photo_height',0)>=48_000_000,resolution=f"{body.get('camera')} · ProRAW · {body.get('photo_width')} × {body.get('photo_height')}",seen=time.time())
                    job['status']='complete'
                return self.respond(200,{'ok':True})
            if path=='/phone/next' and self.command=='GET':return self.respond(200,next_job())
            if path=='/phone/hello' and self.command=='POST':
                with LOCK:PHONE.update(seen=time.time(),name=str(body.get('name','iPhone'))[:80],resolution=str(body.get('resolution',''))[:80],proraw48=body.get('proraw48') is True,protocol_version=body.get('protocol_version',1))
                return self.respond(200,{'ok':True})
            if path=='/phone/error' and self.command=='POST':
                with LOCK:
                    if body.get('id') in JOBS:JOBS[body['id']].update(status='failed',error=str(body.get('error','Aufnahme fehlgeschlagen'))[:300])
                    EVENT='iPhone: '+str(body.get('error','Unbekannter Fehler'))[:300]
                return self.respond(200,{'ok':True})
            if path=='/state' and self.command=='GET':
                return self.respond(200,{'gimbal':DEVICE if CLIENT and CLIENT.is_connected else '', 'phone':PHONE['name'] if time.time()-PHONE['seen']<5 else '', 'resolution':PHONE['resolution'],'event':EVENT,'moving':MOVING,'latest':LATEST,'photos':str(PHOTOS),'camera_state':{k:PHONE.get(k) for k in ('camera','physical_camera','zoom_factor','raw_ready','photo_width','photo_height','portrait_hfov','portrait_vfov')},'motion':dict(MOTION),'motion_fresh':time.monotonic()-MOTION.get('received',0)<1.5,'run':dict(RUN),'proraw48':PHONE.get('proraw48',False)})
            if self.command!='POST':return self.respond(404,{'error':'Nicht gefunden'})
            if path=='/connect':ble_run(connect_gimbal())
            elif path=='/move':
                if RUN['active']:raise ValueError('Automatische Reihe zuerst stoppen')
                ble_run(move(body.get('axis'),body.get('degrees')))
            elif path=='/stop':ble_run(abort_run())
            elif path=='/sequence':ble_run(start_run(body))
            elif path=='/process':ble_run(process_latest())
            elif path=='/continue':ble_run(continue_run())
            elif path=='/wide':ble_run(start_wide())
            elif path=='/tele-grid':ble_run(start_tele_grid())
            elif path=='/camera':ble_run(configure_camera(body.get('camera')))
            elif path=='/level':ble_run(start_run({'mode':'level'}))
            elif path=='/capture':
                if RUN['active']:raise ValueError('Automatische Reihe läuft')
                return self.respond(200,{'id':enqueue_capture(body.get('focus',-1),body.get('lock_exposure',False))})
            else:return self.respond(404,{'error':'Nicht gefunden'})
            self.respond(200,{'ok':True})
        except Exception as exc:self.respond(400,{'error':str(exc)})
    do_GET=handle_request;do_POST=handle_request

def main():
    global LOOP
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=48763);args=parser.parse_args()
    global TOKEN
    credential=ROOT/'pairing-token.txt'
    if credential.exists():TOKEN=credential.read_text().strip()
    else:
        old=ROOT/'session.json'
        if old.exists():
            try:TOKEN=json.loads(old.read_text())['token']
            except Exception:pass
        credential.write_text(TOKEN);credential.chmod(0o600)
    LOOP=asyncio.new_event_loop();threading.Thread(target=LOOP.run_forever,daemon=True).start()
    server=ThreadingHTTPServer(('0.0.0.0',args.port),Handler)
    signal.signal(signal.SIGTERM,lambda *_:threading.Thread(target=server.shutdown,daemon=True).start())
    session=ROOT/'session.json';session.write_text(json.dumps({'token':TOKEN,'port':args.port,'pid':os.getpid()}));session.chmod(0o600)
    try:server.serve_forever()
    finally:
        if CLIENT and CLIENT.is_connected:
            try:ble_run(abort_run());ble_run(CLIENT.disconnect())
            except Exception:pass
        server.server_close();session.unlink(missing_ok=True)
if __name__=='__main__':main()
