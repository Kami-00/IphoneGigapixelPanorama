# Text als primäres Qualitätsziel

Stand: 2. November 2026. Neue Nutzerpriorität: Text soll scharf und lesbar erfasst werden; andere Bildbereiche sind für die gezielte Qualitätsverbesserung nachrangig. Dieses Ziel konkretisiert die regionalen Qualitätsziele aus [KONZEPT.md](KONZEPT.md) und [ENTWURF_AUFNAHMESTEUERUNG.md](ENTWURF_AUFNAHMESTEUERUNG.md).

Priorisierte Motive sind **Schilder, Etiketten und Gerätebeschriftungen**. Zahlen, Typbezeichnungen und technische Kennzeichnungen brauchen besondere Aufmerksamkeit; ein plausibles Wort allein genügt dort nicht als Nachweis.

Die folgende Erweiterung ist ein Entwurf für die vorhandene eigene iPhone-App und Mac-Software. Es wurde noch kein OCR-Aufnahmelauf implementiert oder am Gerät geprüft.

## 1. Konsequenz für die Aufnahmeplanung

Die App sucht Textflächen und erfasst sie gezielt mit geeigneter Kamera, Fokusstellung, Belichtung und Viererfusion. Nichttextbereiche dienen weiterhin als Übersicht, geometrische Orientierung und Bildübergänge. Ihr Schärfe- oder Rauschwert allein löst keine zusätzlichen Qualitätsaufnahmen aus.

Zusätzliche Aufnahmen werden nach dem erwarteten Gewinn an lesbaren Textdetails priorisiert. Ein gutes Übersichtsbild genügt für andere Flächen, soweit sie die Orientierung und das Zusammensetzen ermöglichen.

## 2. Text finden, Text lesen und Schärfe prüfen sind drei Aufgaben

Apple Vision bietet passende Bausteine:

- VNRecognizeTextRequest findet und erkennt Text und liefert Textbeobachtungen beziehungsweise Erkennungskandidaten.
- VNDetectTextRectanglesRequest kann sichtbare Textregionen ohne bereits erfolgreiche Transkription lokalisieren.
- Erkennung kann Geschwindigkeit oder Genauigkeit priorisieren. Unterstützte Sprachen und Funktionen werden passend zur eingesetzten API-Version abgefragt.

Diese Bausteine liefern keine Garantie, alle vorhandenen Texte zu entdecken. Ein bereits unscharfes, überbelichtetes oder zu kleines Wort kann gerade deshalb zunächst fehlen. Ein Planer, der ausschließlich auf erfolgreich gelesene Wörter reagiert, würde solche Stellen übersehen.

Der Suchlauf umfasst deshalb je nach Zielbereich:

1. Eine 1×-Übersicht und überlappende Ausschnitte daraus.
2. Mehrere sinnvolle Fokus-/Belichtungszustände für die Textsuche, soweit die erste Ansicht keine ausreichenden Details liefert.
3. Zusätzliche 3×-Suchabdeckung auch in Bereichen ohne bisherigen OCR-Treffer, wenn kleine Schrift dort relevant sein könnte.
4. Eine fortlaufend ergänzte Textkarte während der Detailaufnahme.

Die Mindesttexthöhe der OCR-Anfrage ist bewusst festzulegen. Bei der etablierten VN-API ist sie relativ zur Bildhöhe; Apple dokumentiert standardmäßig 1/32. Ein hoher Mindestwert oder eine stark verkleinerte Übersicht kann kleine Beschriftungen ausschließen. Überlappende höher aufgelöste Ausschnitte helfen gegen solche konfigurationsbedingten Auslassungen. Sie ersetzen keine fehlenden optischen Details.

Ein Suchbereich kann unter dokumentierten Bedingungen abgearbeitet sein. Ausbleibende OCR-Treffer beweisen trotzdem nicht, dass dort kein Text existiert. Unsicherheit und verbleibende Grenzen werden angezeigt.

## 3. Textziele räumlich verfolgen

Ein Textziel erhält eine räumliche Identität, unabhängig von seiner bisher erkannten Zeichenfolge. Identische Wörter an verschiedenen Stellen bleiben verschiedene Ziele. Ein OCR-Fehler darf dasselbe Schild nicht bei jedem Frame zu einem neuen Ziel machen.

Gespeichert werden beispielsweise Zielregion, Aufnahme-/Kamerabezug, vermutete Tiefe, Erkennungskandidaten, Detailgröße in echten Bildpixeln und die bisher besten Quellaufnahmen. Übersicht, lokale Hauptkamera-Brückenbilder, Tele-Nachbarn und Winkeldaten helfen bei der Zuordnung.

Vision-Koordinaten, Bilddrehung, Ausschnitt und Kamerafokus-Koordinaten müssen korrekt umgerechnet werden. Apple beschreibt Zeichen-Bounding-Boxes als nicht immer exakt. Sie werden daher als großzügige Zielregion verwendet, nicht als pixelgenaue Zeichenmaske.

## 4. Auf Textflächen fokussieren

Eine passende Fokusstellung kann viele Wörter derselben Ebene zugleich verbessern. Es ist nicht nötig, jedes einzelne Wort mit einer eigenen Fokusaufnahme abzuarbeiten.

Der Planer wählt eine strukturierte Stelle innerhalb der Textregion und löst dort den Autofokus aus. Bei schrägen, gebogenen oder verschieden weit entfernten Beschriftungen werden mehrere Teilflächen geprüft. LiDAR kann Tiefengruppen vorschlagen; die tatsächlich abgebildeten Textstriche entscheiden über die Schärfe.

| Befund | Geplante Reaktion |
|---|---|
| Schrift sichtbar und brauchbar belichtet, aber unscharf | Passenden Fokus suchen und Ergebnis kontrollieren |
| Schrift scharf, Details aber abgeschnitten oder zu dunkel | Fokus halten, Belichtung ändern |
| Schrift für die gewünschte Lesbarkeit zu klein | Echte 3×-Detailaufnahme planen |
| Text vermutet, Struktur kaum sichtbar | Suchbelichtung beziehungsweise Fokusvariante prüfen |
| Bewegung oder schlechte Ausrichtung | Gruppe prüfen, Referenz wählen oder neu aufnehmen |
| Keine Verbesserung oder unsichere Bewertung | Begrenzte Versuche, Restproblem dokumentieren |

Vier Wiederholungen je ausgewählter finaler Kamera-/Fokus-/Belichtungsgruppe bleiben Standard. Suchvorschauen und Diagnoseansichten werden davon getrennt betrachtet. Bei Displays beziehungsweise wechselndem Inhalt ist zu prüfen, ob die Frames überhaupt zusammenpassen.

## 5. OCR-Vertrauen ergänzt die optische Prüfung

Ein hoher OCR-Konfidenzwert bedeutet Vertrauen in das Erkennungsergebnis. Er beweist keine optische Schärfe und keine fehlerfreie Transkription. Auch übereinstimmende Erkennungen mehrerer Bilder können denselben Fehler enthalten.

Die Qualitätsbewertung kombiniert deshalb:

- erhaltene Textstriche und lokale Schärfe bei einheitlicher Vergleichsskalierung;
- ausreichende reale Zeichengröße im Bild;
- Belichtung und fehlende beziehungsweise abgeschnittene Zeichen;
- verlässliche Bildausrichtung und geeignete Beiträge der Viererfusion;
- OCR-Ergebnis und dessen Verlässlichkeit als ergänzende Hinweise.

Für technische Kennzeichnungen, Zahlen und ungewöhnliche Wörter werden Varianten mit und ohne Sprachkorrektur verglichen. Ein plausibel korrigiertes Wort kann einzelne schlecht abgebildete Zeichen verdecken. Häufig verwechselte Zeichen wie O/0, I/l/1 oder B/8 gehören in die Vergleichsaufnahmen.

OCR-Transkription und fotografierte Beschriftung bleiben getrennte Ergebnisse. Für das Bild zählen tatsächlich aufgenommene Strichdetails.

## 6. Text auch nach dem Zusammensetzen prüfen

Eine gute Einzelaufnahme garantiert noch kein gut lesbares Panorama. Fokusfusion, Ausrichtung, Beschnitt und Nahtübergänge können Zeichen beschädigen.

Wo möglich, werden Übergänge zwischen Textflächen gelegt. Wörter oder Zeilen sollten möglichst zusammenhängend aus geeigneten Quellen übernommen werden. Lange oder über mehrere Tiefen verlaufende Beschriftungen brauchen trotzdem eine passende Teilflächenfusion.

Im endgültigen Panorama werden die Textregionen erneut in ausreichender Auflösung geprüft und mit ihren besten Quellausschnitten verglichen. Neue Zeichenfehler, Doppelkonturen oder verlorene Randzeichen können eine andere Quellenwahl beziehungsweise erneute Fusion auslösen. Das erfordert nicht immer eine weitere Kameraaufnahme.

## 7. Eine ehrliche Text-Abdeckungskarte

Die Karte zeigt pro Ziel beispielsweise:

- Text vermutet;
- Textregion gefunden, Inhalt noch unsicher;
- Detailaufnahme vorhanden;
- Schärfe und Lesbarkeit ausreichend geprüft;
- Problem in Belichtung, Auflösung, Bewegung oder Fusion;
- unter den aktuellen Bedingungen nicht zuverlässig lesbar.

Suchabdeckung und bestätigte Textqualität bleiben getrennt. Unsichtbare, verdeckte oder optisch nicht ausreichend aufgelöste Schrift lässt sich durch OCR allein nicht vollständig nachweisen.

## 8. Kleiner erster Versuch

Eine bekannte Testszene mit Beschriftungen verschiedener Größe auf zwei bis drei Entfernungen vorbereiten. Den tatsächlichen Wortlaut und die Positionen vorab manuell dokumentieren, einschließlich Zahlen-/Zeichencodes sowie heller, dunkler und schräger Schrift. Glänzende Etiketten und ein Display als eigene schwierigere Varianten prüfen.

Zuerst zwei Fragen getrennt messen:

1. Welche vorhandenen Textregionen findet die erste Übersicht, welche erst die ergänzende Suche, und welche bleiben unentdeckt?
2. Wie vollständig und korrekt sind die Zeichen im besten Quellbild und im fertigen Panorama?

Zusätzlich vergleichen: Detailgewinn durch Fokus/Tele/HDR, Rauschen, Nahtfehler und benötigte Aufnahmegruppen. Eine bloß höhere OCR-Konfidenz gilt nicht allein als Erfolg.

## Quellen

- [Apple: Texterkennung](https://developer.apple.com/documentation/vision/vnrecognizetextrequest)
- [Apple: Textregionen finden](https://developer.apple.com/documentation/vision/vndetecttextrectanglesrequest)
- [Apple: Mindesttexthöhe](https://developer.apple.com/documentation/vision/vnrecognizetextrequest/minimumtextheight)
- [Apple: Erkennungsergebnis und Konfidenz](https://developer.apple.com/documentation/vision/vnrecognizedtext)
- [Apple: Grenzen der Zeichen-Bounding-Boxes](https://developer.apple.com/documentation/vision/vnrecognizedtext/boundingbox%28for%3A%29)
- [Apple: Sprachkorrektur](https://developer.apple.com/documentation/vision/vnrecognizetextrequest/useslanguagecorrection)

Die vorgeschlagene Suchfolge, Zielverfolgung und Qualitätsentscheidung sind eigene technische Ableitungen. Die APIs belegen die verfügbaren Bausteine, keine bereits getestete vollständige Textaufnahme.
