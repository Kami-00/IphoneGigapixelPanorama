import SwiftUI
import AVFoundation
import UIKit
import CoreMotion

struct CapturedPhoto { let data:Data; var metadata:[String:Any] }
final class MotionSensor {
    let manager=CMMotionManager(), queue=OperationQueue(), lock=NSLock()
    private var history:[[String:Any]]=[]
    private var quietSince:Double?
    init(){queue.maxConcurrentOperationCount=1}
    func start(){
        guard manager.isDeviceMotionAvailable,!manager.isDeviceMotionActive else{return}
        manager.deviceMotionUpdateInterval=0.02
        manager.startDeviceMotionUpdates(using:.xArbitraryZVertical,to:queue){[weak self] motion,error in
            guard let self=self,let m=motion else{return}
            let g=m.gravity,r=m.rotationRate,a=m.userAcceleration,q=m.attitude.quaternion,v=m.attitude.rotationMatrix
            let speed=sqrt(r.x*r.x+r.y*r.y+r.z*r.z)*180/Double.pi
            let acceleration=sqrt(a.x*a.x+a.y*a.y+a.z*a.z)
            self.lock.lock();defer{self.lock.unlock()}
            if speed<0.7 && acceleration<0.025 {if self.quietSince==nil{self.quietSince=m.timestamp}}else{self.quietSince=nil}
            let sample:[String:Any]=["timestamp":m.timestamp,"wall_time":Date().timeIntervalSince1970,"roll":atan2(g.x,-g.y)*180/Double.pi,
                "heading":atan2(-v.m31,-v.m32)*180/Double.pi,"elevation":asin(min(1,max(-1,g.z)))*180/Double.pi,
                "rate_dps":speed,"acceleration_g":acceleration,"stable":m.timestamp-(self.quietSince ?? m.timestamp)>=0.6,
                "gravity":[g.x,g.y,g.z],"rotation_rate":[r.x,r.y,r.z],"user_acceleration":[a.x,a.y,a.z],"quaternion":[q.x,q.y,q.z,q.w],
                "reference_frame":"xArbitraryZVertical","orientation":"portrait","sensor_session":self.sessionID]
            self.history.append(sample);if self.history.count>1500{self.history.removeFirst(self.history.count-1500)}
        }
    }
    let sessionID=UUID().uuidString
    func snapshot()->[String:Any]{lock.lock();defer{lock.unlock()};return history.last ?? [:]}
    func around(_ timestamp:Double)->[[String:Any]]{lock.lock();defer{lock.unlock()};return history.filter{abs(($0["timestamp"] as? Double ?? 0)-timestamp)<0.6}}
    func stable() async throws {
        for _ in 0..<120 {
            try Task.checkCancellation()
            let s=snapshot()
            if s["stable"] as? Bool==true,Date().timeIntervalSince1970-(s["wall_time"] as? Double ?? 0)<0.5{return}
            try await Task.sleep(nanoseconds:100_000_000)
        }
        throw NSError(domain:"Motion",code:1,userInfo:[NSLocalizedDescriptionKey:"Kein stabiler Stillstand / keine aktuellen Gyrodaten. Aufnahme abgebrochen."])
    }
}
final class PhotoReceiver:NSObject,AVCapturePhotoCaptureDelegate {
    let done:(Result<CapturedPhoto,Error>)->Void
    let motion:MotionSensor
    let minimumPixels:Int64
    var result:CapturedPhoto?,failure:Error?,atShutter:[String:Any]=[:]
    init(motion:MotionSensor,minimumPixels:Int64=48_000_000,_ done:@escaping(Result<CapturedPhoto,Error>)->Void){self.motion=motion;self.minimumPixels=minimumPixels;self.done=done}
    func photoOutput(_ output:AVCapturePhotoOutput,willCapturePhotoFor resolvedSettings:AVCaptureResolvedPhotoSettings){atShutter=motion.snapshot()}
    func photoOutput(_ output:AVCapturePhotoOutput,didFinishProcessingPhoto photo:AVCapturePhoto,error:Error?){
        if let error=error{failure=error;return}
        guard let data=photo.fileDataRepresentation(),photo.isRawPhoto else{failure=NSError(domain:"Camera",code:1,userInfo:[NSLocalizedDescriptionKey:"Kein ProRAW-DNG geliefert"]);return}
        let d=photo.resolvedSettings.rawPhotoDimensions
        guard Int64(d.width)*Int64(d.height)>=minimumPixels else{failure=NSError(domain:"Camera",code:2,userInfo:[NSLocalizedDescriptionKey:"Kamera lieferte nur \(d.width) × \(d.height) RAW-Pixel; die erwartete Auflösung fehlt."]);return}
        let timestamp=CMTimeGetSeconds(photo.timestamp)
        var meta:[String:Any]=["format":"Apple ProRAW DNG","width":d.width,"height":d.height,"shutter_motion":atShutter,"motion_samples":motion.around(timestamp),"sensor_frame":"portrait device; arbitrary vertical reference; heading relative, not compass"]
        if timestamp.isFinite{meta["camera_timestamp"]=timestamp}
        result=CapturedPhoto(data:data,metadata:meta)
    }
    func photoOutput(_ output:AVCapturePhotoOutput,didFinishCaptureFor resolvedSettings:AVCaptureResolvedPhotoSettings,error:Error?){
        if let error=error ?? failure{done(.failure(error))}else if let result=result{done(.success(result))}else{done(.failure(NSError(domain:"Camera",code:3,userInfo:[NSLocalizedDescriptionKey:"RAW-Aufnahme fehlgeschlagen"])))}
    }
}
final class Camera:NSObject,ObservableObject {
    let session=AVCaptureSession(), output=AVCapturePhotoOutput()
    let motion=MotionSensor()
    @Published var proRAW48=false
    let queue=DispatchQueue(label:"OsmoCamera.capture")
    private var device:AVCaptureDevice?, delegate:PhotoReceiver?
    @Published var ready=false
    @Published var info="Kamera wird vorbereitet …"
    func prepare(){
        guard !session.isRunning else{return}
        motion.start()
        AVCaptureDevice.requestAccess(for:.video){allowed in
            guard allowed else{DispatchQueue.main.async{self.info="Bitte Kamerazugriff in den Einstellungen erlauben."};return}
            self.queue.async{
                do{
                    self.session.beginConfiguration();self.session.sessionPreset = .photo
                    guard let d=AVCaptureDevice.default(.builtInWideAngleCamera,for:.video,position:.back) else{throw NSError(domain:"Camera",code:1,userInfo:[NSLocalizedDescriptionKey:"Hauptkamera nicht verfügbar"])}
                    self.device=d;let input=try AVCaptureDeviceInput(device:d)
                    guard self.session.canAddInput(input),self.session.canAddOutput(self.output) else{throw NSError(domain:"Camera",code:2,userInfo:[NSLocalizedDescriptionKey:"Kamerasitzung nicht verfügbar"])}
                    self.session.addInput(input);self.session.addOutput(self.output)
                    // Choose a photo-capable format exposing the largest genuine photo dimensions.
                    if let format=d.formats.filter({$0.isHighestPhotoQualitySupported && !$0.supportedMaxPhotoDimensions.isEmpty}).max(by:{a,b in
                        (a.supportedMaxPhotoDimensions.map{Int64($0.width)*Int64($0.height)}.max() ?? 0) < (b.supportedMaxPhotoDimensions.map{Int64($0.width)*Int64($0.height)}.max() ?? 0)
                    }) {try d.lockForConfiguration();d.activeFormat=format;d.unlockForConfiguration()}
                    if let dimensions=d.activeFormat.supportedMaxPhotoDimensions.max(by:{Int64($0.width)*Int64($0.height)<Int64($1.width)*Int64($1.height)}) {self.output.maxPhotoDimensions=dimensions}
                    self.output.maxPhotoQualityPrioritization = .quality
                    self.output.isAppleProRAWEnabled=self.output.isAppleProRAWSupported
                    self.session.commitConfiguration();self.session.startRunning()
                    let size=self.output.maxPhotoDimensions
                    let supported=self.output.isAppleProRAWEnabled && self.output.availableRawPhotoPixelFormatTypes.contains(where:AVCapturePhotoOutput.isAppleProRAWPixelFormat) && Int64(size.width)*Int64(size.height)>=48_000_000
                    DispatchQueue.main.async{self.ready=true;self.proRAW48=supported;self.info=supported ? "48 MP Apple ProRAW · \(size.width) × \(size.height)" : "48-MP-ProRAW in dieser Konfiguration nicht verfügbar"}
                }catch{self.session.commitConfiguration();DispatchQueue.main.async{self.info=error.localizedDescription}}
            }
        }
    }
    private var tele=false
    func cameraState() -> [String:Any] {
        guard let d=device else{return [:]}
        let size=output.maxPhotoDimensions
        let v=Double(d.activeFormat.videoFieldOfView)
        let h=2*atan(tan(v*Double.pi/360)*Double(min(size.width,size.height))/Double(max(size.width,size.height)))*180/Double.pi
        return ["camera":tele ? "tele" : "wide", "physical_camera":d.deviceType.rawValue, "zoom_factor":Double(d.videoZoomFactor), "raw_ready":output.isAppleProRAWEnabled && output.availableRawPhotoPixelFormatTypes.contains(where:AVCapturePhotoOutput.isAppleProRAWPixelFormat), "photo_width":size.width, "photo_height":size.height, "portrait_hfov":h, "portrait_vfov":v]
    }
    func selectCamera(_ name:String) async throws -> [String:Any] {
        guard name=="tele" || name=="wide" else{throw NSError(domain:"Camera",code:8,userInfo:[NSLocalizedDescriptionKey:"Unbekannte Kamera"])}
        return try await withCheckedThrowingContinuation { continuation in
            queue.async {
                guard self.delegate==nil else{continuation.resume(throwing:NSError(domain:"Camera",code:8,userInfo:[NSLocalizedDescriptionKey:"Eine Aufnahme läuft"]));return}
                let oldInputs=self.session.inputs
                self.session.stopRunning();self.session.beginConfiguration()
                do {
                    guard let d=AVCaptureDevice.default(name=="tele" ? .builtInTelephotoCamera : .builtInWideAngleCamera,for:.video,position:.back) else{throw NSError(domain:"Camera",code:8,userInfo:[NSLocalizedDescriptionKey:"Physische Kamera fehlt"])}
                    for input in oldInputs{self.session.removeInput(input)}
                    let input=try AVCaptureDeviceInput(device:d)
                    guard self.session.canAddInput(input) else{throw NSError(domain:"Camera",code:8,userInfo:[NSLocalizedDescriptionKey:"Kamerawechsel nicht möglich"])}
                    self.session.addInput(input)
                    if let format=d.formats.filter({$0.isHighestPhotoQualitySupported && !$0.supportedMaxPhotoDimensions.isEmpty}).max(by:{a,b in
                        (a.supportedMaxPhotoDimensions.map{Int64($0.width)*Int64($0.height)}.max() ?? 0) < (b.supportedMaxPhotoDimensions.map{Int64($0.width)*Int64($0.height)}.max() ?? 0)
                    }) {try d.lockForConfiguration();d.activeFormat=format;d.videoZoomFactor=1;d.unlockForConfiguration()}
                    if let size=d.activeFormat.supportedMaxPhotoDimensions.max(by:{Int64($0.width)*Int64($0.height)<Int64($1.width)*Int64($1.height)}) {self.output.maxPhotoDimensions=size}
                    self.output.isAppleProRAWEnabled=self.output.isAppleProRAWSupported
                    self.device=d;self.tele=name=="tele"
                    self.session.commitConfiguration();self.session.startRunning()
                    let state=self.cameraState(),size=self.output.maxPhotoDimensions
                    DispatchQueue.main.async{self.proRAW48 = !self.tele && Int64(size.width)*Int64(size.height)>=48_000_000;self.info="\(self.tele ? "3× Tele" : "1× Hauptkamera") · ProRAW · \(size.width) × \(size.height)"}
                    continuation.resume(returning:state)
                } catch {
                    for input in self.session.inputs{self.session.removeInput(input)}
                    for input in oldInputs where self.session.canAddInput(input){self.session.addInput(input)}
                    self.session.commitConfiguration();self.session.startRunning();continuation.resume(throwing:error)
                }
            }
        }
    }
    func capture(focus:Float,lockExposure:Bool) async throws->CapturedPhoto {
        try await motion.stable()
        return try await withCheckedThrowingContinuation{continuation in
            queue.async {
                do{
                    guard let d=self.device,self.session.isRunning,self.delegate==nil else{throw NSError(domain:"Camera",code:3,userInfo:[NSLocalizedDescriptionKey:"Kamera noch nicht bereit oder beschäftigt"])}
                    try d.lockForConfiguration()
                    if focus>=0,d.isFocusModeSupported(.locked){d.setFocusModeLocked(lensPosition:min(1,max(0,focus)),completionHandler:nil)}
                    else if d.isFocusModeSupported(.continuousAutoFocus){d.focusMode = .continuousAutoFocus}
                    if lockExposure,d.isExposureModeSupported(.locked){d.exposureMode = .locked}
                    else if d.isExposureModeSupported(.continuousAutoExposure){d.exposureMode = .continuousAutoExposure}
                    d.unlockForConfiguration()
                    self.queue.asyncAfter(deadline:.now()+0.7){
                        guard let raw=self.output.availableRawPhotoPixelFormatTypes.first(where:AVCapturePhotoOutput.isAppleProRAWPixelFormat),Int64(self.output.maxPhotoDimensions.width)*Int64(self.output.maxPhotoDimensions.height)>=(self.tele ? 12_000_000 : 48_000_000) else{continuation.resume(throwing:NSError(domain:"Camera",code:4,userInfo:[NSLocalizedDescriptionKey:"ProRAW in der gewählten Kameraauflösung nicht verfügbar"]));return}
                        let sample=self.motion.snapshot()
                        guard sample["stable"] as? Bool==true,Date().timeIntervalSince1970-(sample["wall_time"] as? Double ?? 0)<0.5 else{continuation.resume(throwing:NSError(domain:"Motion",code:2,userInfo:[NSLocalizedDescriptionKey:"Bewegung während der Aufnahmevorbereitung – abgebrochen"]));return}
                        let settings=AVCapturePhotoSettings(rawPixelFormatType:raw);settings.maxPhotoDimensions=self.output.maxPhotoDimensions;settings.photoQualityPrioritization = .quality
                        if self.output.supportedFlashModes.contains(.off){settings.flashMode = .off}
                        let receiver=PhotoReceiver(motion:self.motion,minimumPixels:self.tele ? 12_000_000 : 48_000_000){result in self.queue.async{self.delegate=nil};continuation.resume(with:result.map{photo in var p=photo;p.metadata.merge(self.cameraState(),uniquingKeysWith: { _,new in new });p.metadata["lens_position"]=d.lensPosition;p.metadata["iso"]=d.iso;p.metadata["exposure_seconds"]=CMTimeGetSeconds(d.exposureDuration);return p})}
                        self.delegate=receiver;self.output.capturePhoto(with:settings,delegate:receiver)
                    }
                }catch{continuation.resume(throwing:error)}
            }
        }
    }
}
struct Preview:UIViewRepresentable {
    let session:AVCaptureSession
    final class View:UIView {override class var layerClass:AnyClass{AVCaptureVideoPreviewLayer.self};var preview:AVCaptureVideoPreviewLayer{layer as! AVCaptureVideoPreviewLayer}}
    func makeUIView(context:Context)->View{let v=View();v.preview.session=session;v.preview.videoGravity = .resizeAspectFill;return v}
    func updateUIView(_ v:View,context:Context){}
}
@MainActor final class Connection:ObservableObject {
    @Published var link=""
    @Published var status="Verbindungslink vom Mac einfügen oder QR-Code öffnen."
    @Published var connected=false
    @Published var lastPhoto:UIImage?
    private var task:Task<Void,Never>?,telemetryTask:Task<Void,Never>?,base:URL?,token=""
    let camera:Camera
    init(camera:Camera){self.camera=camera;self.link=UserDefaults.standard.string(forKey:"connectionLink") ?? ""}
    func configure(_ url:URL){link=url.absoluteString;connect()}
    func connect(){
        guard camera.ready else{status="Kamera noch nicht bereit. Danach erneut Verbinden antippen.";return}
        guard let c=URLComponents(string:link.trimmingCharacters(in:.whitespacesAndNewlines)),c.scheme=="osmostudio",c.host=="connect" else{status="Ungültiger Verbindungslink";return}
        let items=c.queryItems ?? [];let host=items.first{$0.name=="host"}?.value ?? "";let port=items.first{$0.name=="port"}?.value ?? "";let t=items.first{$0.name=="token"}?.value ?? ""
        guard !host.isEmpty,let pn=Int(port),(1024...65535).contains(pn),t.count>=32 else{status="Verbindungslink unvollständig";return}
        var url=URLComponents();url.scheme="http";url.host=host;url.port=pn
        guard let b=url.url else{return};disconnect();base=b;token=t
        UserDefaults.standard.set(link,forKey:"connectionLink");task=Task{await loop()}
    }
    func disconnect(){task?.cancel();task=nil;telemetryTask?.cancel();telemetryTask=nil;connected=false;UIApplication.shared.isIdleTimerDisabled=false}
    func request(_ path:String,json:[String:Any]?=nil,data:Data?=nil,id:String?=nil) async throws->[String:Any]{
        guard let base=base else{throw URLError(.badURL)}
        var req=URLRequest(url:base.appendingPathComponent(path));req.timeoutInterval=180;req.setValue("Bearer "+token,forHTTPHeaderField:"Authorization")
        if let json=json{req.httpMethod="POST";req.httpBody=try JSONSerialization.data(withJSONObject:json);req.setValue("application/json",forHTTPHeaderField:"Content-Type")}
        if let data=data{req.httpMethod="POST";req.httpBody=data;req.setValue("image/dng",forHTTPHeaderField:"Content-Type");req.setValue(id,forHTTPHeaderField:"X-Capture-ID")}
        let (bytes,response)=try await URLSession.shared.data(for:req)
        let result=(try JSONSerialization.jsonObject(with:bytes)) as? [String:Any] ?? [:]
        guard (response as? HTTPURLResponse)?.statusCode==200 else{throw NSError(domain:"Connection",code:1,userInfo:[NSLocalizedDescriptionKey:result["error"] as? String ?? "Mac antwortet mit Fehler"])}
        return result
    }
    func loop() async {
        do{
            _ = try await request("phone/hello",json:["name":UIDevice.current.name,"resolution":camera.info,"proraw48":camera.proRAW48,"protocol_version":3]);connected=true;UIApplication.shared.isIdleTimerDisabled=true;status=camera.proRAW48 ? "Verbunden. 48-MP-ProRAW bereit." : "Verbunden, aber 48-MP-ProRAW nicht verfügbar."
            telemetryTask=Task{while !Task.isCancelled{var sample=camera.motion.snapshot();sample["proraw48"]=camera.proRAW48;_ = try? await request("phone/motion",json:sample);try? await Task.sleep(nanoseconds:150_000_000)}}
            while !Task.isCancelled {
                let job=try await request("phone/next")
                if let id=job["id"] as? String,job["kind"] as? String=="camera" {
                    do {
                        status="Kamera wird umgestellt …"
                        var state=try await camera.selectCamera(job["camera"] as? String ?? "wide")
                        state["id"]=id
                        _ = try await request("phone/configured",json:state)
                        status="Kamera bereit."
                    } catch {_ = try? await request("phone/error",json:["id":id,"error":error.localizedDescription])}
                } else if let id=job["id"] as? String,job["kind"] as? String=="capture" {
                    do{
                        status="Foto wird aufgenommen …"
                        let photo=try await camera.capture(focus:(job["focus"] as? NSNumber)?.floatValue ?? -1,lockExposure:job["lock_exposure"] as? Bool ?? false)
                        let folder=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("Aufnahmen",isDirectory:true)
                        try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
                        try photo.data.write(to:folder.appendingPathComponent(id+".dng"),options:.atomic)
                        let metadata=try JSONSerialization.data(withJSONObject:photo.metadata,options:[.prettyPrinted,.sortedKeys]);try metadata.write(to:folder.appendingPathComponent(id+".json"),options:.atomic)
                        _ = try await request("phone/metadata",json:["id":id,"metadata":photo.metadata])
                        var uploadError:Error?
                        for _ in 0..<3 {
                            do{_ = try await request("phone/photo",data:photo.data,id:id);uploadError=nil;break}catch{uploadError=error;try await Task.sleep(nanoseconds:500_000_000)}
                        }
                        if let error=uploadError{throw error}
                        status="Originalfoto auf dem Mac gespeichert."
                    }catch{
                        status="Aufnahme/Übertragung: "+error.localizedDescription
                        _ = try? await request("phone/error",json:["id":id,"error":error.localizedDescription])
                    }
                }
                try await Task.sleep(nanoseconds:600_000_000)
            }
        }catch{if !Task.isCancelled{status=error.localizedDescription+" – erneut verbinden."}}
        telemetryTask?.cancel();telemetryTask=nil;connected=false;UIApplication.shared.isIdleTimerDisabled=false
    }
}
struct CameraView:View {
    @ObservedObject var camera:Camera
    @ObservedObject var connection:Connection
    var body:some View {
        VStack(spacing:12){
            HStack{Text("Osmo Camera").font(.title.bold());Spacer();Circle().fill(connection.connected ? .green : .gray).frame(width:12,height:12)}
            Preview(session:camera.session).clipShape(RoundedRectangle(cornerRadius:18)).overlay(alignment:.bottom){Text(camera.info).font(.caption).padding(8).background(.black.opacity(0.65),in:Capsule()).foregroundStyle(.white).padding()}
            if !connection.connected{TextField("Verbindungslink vom Mac",text:$connection.link).textInputAutocapitalization(.never).autocorrectionDisabled().textFieldStyle(.roundedBorder);Button("Mit Mac verbinden"){connection.connect()}.buttonStyle(.borderedProminent).disabled(!camera.ready)}
            else{Button("Verbindung trennen"){connection.disconnect()}}
            Text(connection.status).font(.callout).frame(maxWidth:.infinity,alignment:.leading)
            Text("App geöffnet lassen. Originale bleiben zusätzlich unter Dateien → Auf meinem iPhone → Osmo Camera → Aufnahmen.").font(.caption).foregroundStyle(.secondary)
        }.padding().onAppear{camera.prepare()}.onChange(of:camera.ready){ready in if ready && !connection.link.isEmpty && !connection.connected{connection.connect()}}.onOpenURL{connection.configure($0)}
    }
}
@main struct OsmoCameraApp:App {
    @StateObject private var camera:Camera
    @StateObject private var connection:Connection
    init(){let c=Camera();_camera=StateObject(wrappedValue:c);_connection=StateObject(wrappedValue:Connection(camera:c))}
    var body:some Scene{WindowGroup{CameraView(camera:camera,connection:connection)}}
}
