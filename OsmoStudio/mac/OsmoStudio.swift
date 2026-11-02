import SwiftUI
import AppKit
import Darwin
import CoreImage.CIFilterBuiltins

let project = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : Bundle.main.bundleURL.deletingLastPathComponent().path)
@MainActor final class Studio: ObservableObject {
    @Published var ready=false
    @Published var busy=false
    @Published var gimbal=""
    @Published var phone=""
    @Published var resolution=""
    @Published var message="Lokaler Dienst wird gestartet …"
    @Published var pairing=""
    @Published var manualFocus=false
    @Published var lockExposure=false
    @Published var focus=0.5
    @Published var running=false
    @Published var rawReady=false
    @Published var motionFresh=false
    @Published var roll=0.0
    @Published var heading=0.0
    @Published var elevation=0.0
    @Published var done=0
    @Published var total=0
    @Published var panorama=false
    @Published var twoPass=false
    @Published var awaitingTurn=false
    @Published var passIndex=1
    @Published var focusCount=1
    @Published var repeats=1
    @Published var halfSpan=30.0
    @Published var pitchSpan=0.0
    var shotCount:Int {(twoPass ? 2 : 1)*(panorama ? (Int(ceil(2*halfSpan/(twoPass ? 40 : 30)))+1)*(pitchSpan>0 ? 3 : 1) : 1)*focusCount*repeats}
    func sequence(){action("/sequence",["mode":panorama ? "panorama" : "focus","half_span":halfSpan,"step":twoPass && panorama ? 40 : 30,"pitch_span":pitchSpan,"focus_count":focusCount,"focus_near":0.35,"focus_far":0.95,"repeat":repeats,"lock_exposure":lockExposure,"two_pass":twoPass && panorama])}
    private var token="", port=48763
    private var process:Process?, timer:Timer?
    private var started=false
    func attach() async -> Bool {
        guard let data=try? Data(contentsOf:project.appendingPathComponent("session.json")),
              let session=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],
              let savedToken=session["token"] as? String else{return false}
        token=savedToken;port=session["port"] as? Int ?? 48763
        do{_ = try await request("/state")}catch{return false}
        ready=true
        var c=URLComponents();c.scheme="osmostudio";c.host="connect"
        c.queryItems=[URLQueryItem(name:"host",value:localIP()),URLQueryItem(name:"port",value:String(port)),URLQueryItem(name:"token",value:token)]
        pairing=c.string ?? ""
        timer?.invalidate()
        let t=Timer(timeInterval:1,repeats:true){[weak self] _ in Task{@MainActor in await self?.refresh()}}
        RunLoop.main.add(t,forMode:.common);timer=t
        await refresh();return true
    }
    func start() {
        guard !started else{return};started=true
        Task {
            if await attach(){return}
            let p=Process();p.executableURL=URL(fileURLWithPath:ProcessInfo.processInfo.environment["PANORAMA_PYTHON"] ?? project.deletingLastPathComponent().appendingPathComponent(".venv/bin/python").path)
            p.arguments=[project.appendingPathComponent("server.py").path];p.currentDirectoryURL=project
            let log=project.appendingPathComponent("server.log");FileManager.default.createFile(atPath:log.path,contents:nil)
            if let f=try? FileHandle(forWritingTo:log){p.standardOutput=f;p.standardError=f}
            do{try p.run();process=p}catch{message=error.localizedDescription;started=false;return}
            for _ in 0..<30 {
                try? await Task.sleep(nanoseconds:200_000_000)
                if await attach(){return}
                if !p.isRunning{break}
            }
            message="Verbindung zum lokalen Dienst fehlgeschlagen. Erneut verbinden versuchen.";started=false
        }
    }
    func localIP()->String {
        var addresses:UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&addresses)==0 else{return ProcessInfo.processInfo.hostName}
        defer{freeifaddrs(addresses)}
        var current=addresses
        while let entry=current {
            defer{current=entry.pointee.ifa_next}
            guard let addr=entry.pointee.ifa_addr,addr.pointee.sa_family==UInt8(AF_INET),String(cString:entry.pointee.ifa_name).hasPrefix("en") else{continue}
            var host=[CChar](repeating:0,count:Int(NI_MAXHOST))
            if getnameinfo(addr,socklen_t(addr.pointee.sa_len),&host,socklen_t(host.count),nil,0,NI_NUMERICHOST)==0{return String(cString:host)}
        }
        return ProcessInfo.processInfo.hostName
    }
    func request(_ path:String,_ body:[String:Any]?=nil) async throws->[String:Any] {
        var r=URLRequest(url:URL(string:"http://127.0.0.1:\(port)\(path)")!);r.timeoutInterval=path=="/state" ? 3 : 25;r.setValue("Bearer "+token,forHTTPHeaderField:"Authorization")
        if let body=body{r.httpMethod="POST";r.setValue("application/json",forHTTPHeaderField:"Content-Type");r.httpBody=try JSONSerialization.data(withJSONObject:body)}
        let (data,response)=try await URLSession.shared.data(for:r);let obj=(try JSONSerialization.jsonObject(with:data)) as? [String:Any] ?? [:]
        if (response as? HTTPURLResponse)?.statusCode != 200 {throw NSError(domain:"Studio",code:1,userInfo:[NSLocalizedDescriptionKey:obj["error"] as? String ?? "Verbindungsfehler"])}
        return obj
    }
    func refresh() async {
        guard ready else{return}
        do {
            let s=try await request("/state")
            gimbal=s["gimbal"] as? String ?? "";phone=s["phone"] as? String ?? ""
            resolution=s["resolution"] as? String ?? "";rawReady=s["proraw48"] as? Bool ?? false
            motionFresh=s["motion_fresh"] as? Bool ?? false
            let m=s["motion"] as? [String:Any] ?? [:]
            roll=m["roll"] as? Double ?? 0;heading=m["heading"] as? Double ?? 0;elevation=m["elevation"] as? Double ?? 0
            let r=s["run"] as? [String:Any] ?? [:];running=r["active"] as? Bool ?? false
            awaitingTurn=r["awaiting_turn"] as? Bool ?? false;passIndex=r["pass_index"] as? Int ?? 1
            done=r["done"] as? Int ?? 0;total=r["total"] as? Int ?? 0
            if !busy{message=running ? (r["message"] as? String ?? "") : (s["event"] as? String ?? "")}
            if let d=try? JSONSerialization.data(withJSONObject:["ready":ready,"phoneConnected":!phone.isEmpty,"gimbalConnected":!gimbal.isEmpty,"proraw48":rawReady,"motionFresh":motionFresh,"running":running]){try? d.write(to:project.appendingPathComponent("ui-status.json"),options:.atomic)}
        }catch{motionFresh=false;message=error.localizedDescription}
    }
    func action(_ path:String,_ body:[String:Any]=[:]) {busy=true;Task{do{_ = try await request(path,body);if path=="/capture"{message="Aufnahme angefordert …"}}catch{message=error.localizedDescription};busy=false}}
    func move(_ axis:String,_ amount:Double){guard !running && !busy else{return};action("/move",["axis":axis,"degrees":amount])}
    func capture(){action("/capture",["focus":manualFocus ? focus : -1,"lock_exposure":lockExposure])}
    func stop(){action("/stop")}
    func quit(){timer?.invalidate();process?.terminate()}
    func qr()->NSImage?{let filter=CIFilter.qrCodeGenerator();filter.message=Data(pairing.utf8);guard let out=filter.outputImage?.transformed(by:CGAffineTransform(scaleX:6,y:6)),let cg=CIContext().createCGImage(out,from:out.extent) else{return nil};return NSImage(cgImage:cg,size:NSSize(width:200,height:200))}
}
struct Content:View {
    @ObservedObject var model:Studio
    var body:some View {
        ScrollView { VStack(alignment:.leading,spacing:18){
            HStack{VStack(alignment:.leading){Text("Osmo Studio").font(.largeTitle.bold());Text("Gimbal bewegen. Echte iPhone-Fotos aufnehmen.").foregroundStyle(.secondary)};Spacer();Button("Verbindung prüfen"){model.start();Task{await model.refresh()}};Text(model.ready ? "VERBUNDEN" : "VERBINDET …").font(.caption.bold()).padding(8).background(.green.opacity(0.15),in:Capsule())}
            HStack(alignment:.top,spacing:24){
                GroupBox("1 · Gimbal") {VStack(spacing:14){Text(model.gimbal.isEmpty ? "Nicht verbunden" : model.gimbal).foregroundStyle(model.gimbal.isEmpty ? .secondary : .primary)
                    Button("OM3 verbinden"){model.action("/connect")}.disabled(!model.ready || model.busy)
                    VStack(spacing:8){Button("↑  5°"){model.move("pitch",5)};HStack{Button("←  5°"){model.move("yaw",-5)};Button("STOPP"){model.stop()}.tint(.red);Button("5°  →"){model.move("yaw",5)}};Button("↓  5°"){model.move("pitch",-5)}}.disabled(model.gimbal.isEmpty)
                    HStack{Button("Neigung −1°"){model.move("roll",-1)};Button("+1°"){model.move("roll",1)}}.disabled(model.running || model.busy)
                    Button("Motorische Geradestellung testen"){model.action("/level")}.disabled(!model.motionFresh || model.running || model.busy)
                    Text(model.motionFresh ? String(format:"Neigung %.1f° · Richtung %.1f° · Höhe %.1f°",model.roll,model.heading,model.elevation) : "Warte auf aktuelle iPhone-Sensordaten").font(.caption).foregroundStyle(.secondary)
                }.padding().frame(width:280)}
                GroupBox("2 · iPhone") {VStack(alignment:.leading,spacing:12){Text(model.phone.isEmpty ? "Begleit-App noch nicht verbunden" : model.phone).font(.headline)
                    if model.phone.isEmpty {HStack{if let qr=model.qr(){Image(nsImage:qr).resizable().interpolation(.none).frame(width:140,height:140)};VStack(alignment:.leading,spacing:10){Text("Osmo Camera auf dem iPhone installieren. Danach QR-Code mit der iPhone-Kamera öffnen oder Verbindungslink in der App einfügen.").font(.callout);Button("Verbindungslink kopieren"){NSPasteboard.general.clearContents();NSPasteboard.general.setString(model.pairing,forType:.string)}.disabled(!model.ready)}}}
                    else{Text(model.resolution).foregroundStyle(.secondary)}
                    Text("Beide Geräte im gleichen WLAN. Die iPhone-App muss geöffnet und das iPhone entsperrt bleiben.").font(.caption).foregroundStyle(.secondary)
                }.padding().frame(maxWidth:.infinity)}
            }
            GroupBox("3 · Foto") {VStack(alignment:.leading,spacing:12){HStack{Toggle("Manueller Fokus",isOn:$model.manualFocus);Spacer();Toggle("Belichtung für Aufnahme sperren",isOn:$model.lockExposure)}
                if model.manualFocus{HStack{Text("Nah");Slider(value:$model.focus,in:0...1);Text("Fern");Text(String(format:"%.2f",model.focus)).monospacedDigit()};Text("Die Fokusposition wird beim Auslösen eingestellt; keine Entfernungsmessung.").font(.caption).foregroundStyle(.secondary)}
                HStack{Button("Foto aufnehmen"){model.capture()}.buttonStyle(.borderedProminent).disabled(model.phone.isEmpty || model.busy || model.running || !model.rawReady);Button("Letztes Panorama berechnen"){model.action("/process")}.disabled(model.running || model.busy);Button("Fotoordner öffnen"){NSWorkspace.shared.open(project.appendingPathComponent("photos"))};Spacer();Text("48 MP · Apple ProRAW · DNG + Sensordaten").foregroundStyle(.secondary)}
            }.padding()}
            GroupBox("4 · Automatische Aufnahmereihe") {
                VStack(alignment:.leading,spacing:10){
                    HStack{Toggle("Panorama mit mehreren Blickrichtungen",isOn:$model.panorama);Spacer();Stepper("Fokuspositionen: \(model.focusCount)",value:$model.focusCount,in:1...7);Stepper("Jeweils \(model.repeats)×",value:$model.repeats,in:1...3)}.disabled(model.running)
                    if model.panorama {Toggle("Zwei Durchgänge mit manueller 180°-Drehung",isOn:$model.twoPass).disabled(model.running || model.awaitingTurn).onChange(of:model.twoPass){enabled in if enabled{model.halfSpan=100;model.pitchSpan=0;model.focusCount=1;model.repeats=1}}}
                    if model.twoPass {Text("Vor Start Gimbal zentrieren. Beide Durchgänge ergeben einen Rundumblick; direkt oben und unten fehlen weiterhin Aufnahmen.").font(.caption).foregroundStyle(.secondary)}
                    if model.awaitingTurn {Text("Durchgang 1 gespeichert. Griff am selben Standort um 180° drehen; iPhone-App geöffnet lassen.").foregroundStyle(.orange);Button("Gedreht – Durchgang 2 starten"){model.action("/continue")}.buttonStyle(.borderedProminent).disabled(model.busy || !model.motionFresh)}
                    if model.panorama {HStack{Text("Schwenk ±\(Int(model.halfSpan))°");Slider(value:$model.halfSpan,in:10...100,step:10);Text("Oben/unten ±\(Int(model.pitchSpan))°");Slider(value:$model.pitchSpan,in:0...30,step:5)}.disabled(model.running)}
                    Text("\(model.shotCount) Fotos · ca. \(String(format:"%.1f",Double(model.shotCount)*0.13)) GB Reserve. 1 Fokusposition = Autofokus; mehrere = Nah–Fern-Reihe. Danach automatisch zusammensetzen. Teilpanorama, solange nicht der ganze Raum erfasst wurde.").font(.caption).foregroundStyle(.secondary)
                    HStack{Button("Aufnahmereihe starten"){model.sequence()}.buttonStyle(.borderedProminent).disabled(model.running || model.busy || !model.rawReady || !model.motionFresh || model.gimbal.isEmpty || model.awaitingTurn || model.shotCount>300);Button("STOPP"){model.stop()}.tint(.red);Spacer();Text("Durchgang \(model.passIndex) · \(model.done) / \(model.total) gespeichert")}
                    Button("Großes 360°-Bild aufnehmen – fehlende Bereiche schwarz"){model.action("/wide")}.disabled(model.running || model.busy || model.awaitingTurn || !model.rawReady || !model.motionFresh || model.gimbal.isEmpty)
                    Text("Erfasst die erreichbaren Schwenk- und Höhenwinkel. Anschließend automatische 360°-Berechnung in voller Auflösung.").font(.caption).foregroundStyle(.secondary)
                    if model.running {if model.total>0{ProgressView(value:Double(model.done),total:Double(model.total))}else{ProgressView()}}
                }.padding()
            }
            Text(model.message).font(.callout).textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading).padding().background(.quaternary,in:RoundedRectangle(cornerRadius:10))
            Spacer(minLength:0)
        }.padding(24) }.frame(minWidth:850,minHeight:680).onAppear{model.start()}
    }
}
@main struct OsmoStudioApp:App {
    @StateObject var model=Studio()
    var body:some Scene{WindowGroup{Content(model:model).onReceive(NotificationCenter.default.publisher(for:NSApplication.willTerminateNotification)){_ in model.quit()}}.windowResizability(.contentMinSize)}
}
