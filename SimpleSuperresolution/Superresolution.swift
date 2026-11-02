import SwiftUI
import AppKit
import UniformTypeIdentifiers

@MainActor final class Model: ObservableObject {
    @Published var files:[URL]=[]
    @Published var busy=false
    @Published var status="Wähle mehrere Fotos desselben Motivs."
    @Published var output:URL?
    private var process:Process?
    private var pipe:Pipe?
    private var buffer=""
    let root=Bundle.main.bundleURL.deletingLastPathComponent()
    func choose(){
        let panel=NSOpenPanel();panel.allowsMultipleSelection=true;panel.canChooseDirectories=false
        panel.allowedContentTypes=[.jpeg,.png,.tiff,.heic,.heif];panel.message="Fotos derselben Ansicht auswählen – möglichst gleicher Fokus und gleiche Belichtung."
        if panel.runModal() == .OK {files=panel.urls;status="\(files.count) Bilder ausgewählt. Das erste Bild dient als Vergleich.";output=nil}
    }
    func start(){
        guard files.count>=2 && !busy else{return}
        let f=DateFormatter();f.dateFormat="yyyyMMdd-HHmmss-SSS"
        let folder=root.appendingPathComponent("Ergebnisse/"+f.string(from:Date()))
        busy=true;output=nil;status="Verarbeitung startet …";buffer=""
        let p=Process(),pipe=Pipe();self.process=p;self.pipe=pipe
        p.executableURL=URL(fileURLWithPath:ProcessInfo.processInfo.environment["PANORAMA_PYTHON"] ?? root.deletingLastPathComponent().appendingPathComponent(".venv/bin/python").path)
        p.arguments=["-u",root.appendingPathComponent("stack.py").path]+files.map(\.path)+["--output",folder.path]
        p.currentDirectoryURL=root;p.standardOutput=pipe;p.standardError=pipe
        pipe.fileHandleForReading.readabilityHandler={ [weak self] handle in
            let data=handle.availableData
            guard !data.isEmpty,let text=String(data:data,encoding:.utf8) else{return}
            Task{@MainActor in
                guard let self=self else{return};self.buffer += text
                let lines=self.buffer.split(separator:"\n",omittingEmptySubsequences:true)
                if let last=lines.last{self.status=String(last)}
            }
        }
        p.terminationHandler={ [weak self] finished in
            Task{@MainActor in
                guard let self=self else{return};self.busy=false;self.pipe?.fileHandleForReading.readabilityHandler=nil
                if finished.terminationStatus==0{self.output=folder;self.status="Fertig. Mittelwert, Median und Einzelbild sind gespeichert."}
                else if finished.terminationStatus==130 || finished.terminationReason == .uncaughtSignal {self.status="Abgebrochen. Deine Originale bleiben unverändert."}
                else{self.status="Verarbeitung fehlgeschlagen. Details stehen in Verarbeitung.log im Ergebnisordner.";self.output=folder}
                self.process=nil
            }
        }
        do{try p.run()}catch{busy=false;status=error.localizedDescription;self.process=nil}
    }
    func cancel(){status="Wird abgebrochen …";process?.terminate()}
}
@main struct SuperresolutionApp:App {
    @StateObject private var model=Model()
    var body:some Scene {
        WindowGroup("Superresolution") {
            VStack(alignment:.leading,spacing:18) {
                Text("Mehr Details aus mehreren Fotos").font(.title2.bold())
                Text("Doppelte Breite und Höhe · vierfache Pixelzahl").foregroundStyle(.secondary)
                Text("Bilder vergrößern, mit Hugin ausrichten und zusammenrechnen. Du erhältst Mittelwert und Median zum direkten Vergleich.")
                HStack{Button("Bilder auswählen …"){model.choose()}.disabled(model.busy);Text("\(model.files.count) ausgewählt").foregroundStyle(.secondary)}
                if !model.files.isEmpty {
                    ScrollView{VStack(alignment:.leading){ForEach(model.files,id:\.self){Text($0.lastPathComponent).font(.caption)}}}.frame(maxHeight:110)
                }
                Text("Am besten 8–20 kurz nacheinander aufgenommene Fotos mit gleichem Fokus. Unterschiedliche Fokuspunkte können beim Mitteln Schärfe verlieren.").font(.callout).foregroundStyle(.secondary)
                HStack{
                    Button("Berechnen"){model.start()}.buttonStyle(.borderedProminent).disabled(model.busy || model.files.count<2)
                    if model.busy{ProgressView().controlSize(.small);Button("Abbrechen"){model.cancel()}}
                    if let folder=model.output {
                        Button("Vergleich öffnen"){NSWorkspace.shared.open(folder.appendingPathComponent("Vergleich.html"))}
                        Button("Ergebnisordner"){NSWorkspace.shared.open(folder)}
                    }
                }
                Text(model.status).font(.callout).textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading)
                Text("Alles bleibt lokal. Originale werden nicht verändert. Zwischendateien werden nach dem Lauf entfernt.").font(.caption).foregroundStyle(.secondary)
            }.padding(28).frame(width:570)
            .onReceive(NotificationCenter.default.publisher(for:NSApplication.willTerminateNotification)){_ in model.cancel()}
        }.windowResizability(.contentSize)
    }
}
