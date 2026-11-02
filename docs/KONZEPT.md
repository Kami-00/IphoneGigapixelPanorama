# Technisches Konzept

**Aktuelle Priorität:** Zuerst ein einfacher 360°-Durchlauf aus 3×-Einzelbildern, genau ein Bild pro Position. Entrauschen ist optional und zunächst ausgeschaltet. Die nachfolgenden weiterführenden Verfahren sind spätere Ausbaustufen; maßgeblich sind [README](../README.md) und [Arbeitsplan](WEITERARBEITEN.md).

## 1. Bestehende Lösung als Grundlage

Bereits vorhanden laut Projektinhaber: Mac-Steuerung des DJI Osmo Mobile 3, eigene iPhone-App, Kameraauslösung, Speicherung aller Bilder auf dem Mac, Verarbeitung am Mac und Abfrage der iPhone-Winkeldaten. Welche Fokus-, HDR- oder Rauschverfahren die aktuelle Verarbeitung bereits enthält, ist noch unbekannt.

Zuerst werden vorhandene Schnittstellen und Datenformate dokumentiert. Ein neuer Technologiestack oder eine vollständige Neuentwicklung wird nicht vorausgesetzt.

## 2. Aufnahmegruppen

Eine Aufnahme erhält eine eindeutige Zuordnung zu:

- Sitzung und Panorama-Position
- Physischer Kamera und tatsächlichem Bildformat
- Fokusstellung beziehungsweise Autofokus-Zielregion
- Belichtungsgruppe
- Wiederholungsnummer innerhalb der Gruppe; im ersten 360°-Lauf eine Aufnahme pro Position, Wiederholungsgruppen nur als späterer optionaler Vergleich

Zusätzlich speichern: Zeitstempel, Orientierung mit Bezugssystem, verfügbare Bewegungsdaten, angeforderte und tatsächlich gemeldete Belichtungswerte, Bildabmessungen, verfügbare Kalibrierdaten und Qualitätsbewertungen. Verfügbarkeit und Bedeutung der Metadaten werden im bestehenden Aufnahmeweg geprüft.

Winkeldaten unterstützen Zielkontrolle, Stillstandserkennung und eine erste Bildausrichtung. Sie ersetzen die Prüfung der optischen Bildregistrierung nicht. Rohe Gyro-Drehraten und bereits berechnete Geräteorientierung sind zu unterscheiden.

## 3. Adaptive Wahl von Fokus und Belichtung

Pro Region werden Schärfe, Belichtung und Verlässlichkeit der Bewertung getrennt erfasst.

| Beobachtung | Geplante Reaktion |
|---|---|
| Gut belichtet, aber unscharf | Auf eine strukturierte Stelle derselben Region fokussieren |
| Scharf, aber Details durch Über-/Unterbelichtung verloren | Fokus halten und weitere Belichtung erfassen |
| Struktur wegen Belichtung kaum sichtbar | Zuerst Belichtung verbessern, dann Fokus prüfen |
| Keine ausreichende Struktur | Als unsicher markieren; keine unbegrenzten Versuche |
| Bewegung oder misslungene Registrierung | Gruppe erneut prüfen oder auf weniger Aufnahmen zurückfallen |

Fokuspunkt und Belichtungsmesspunkt lassen sich per AVFoundation getrennt setzen. Das Setzen eines Punkts allein startet die jeweilige Automatik noch nicht. Unterstützte Betriebsarten prüfen, Anpassung auslösen, den Einstellvorgang abwarten und das Ergebnis anhand des Bildes bewerten. Foto-, Vorschau- und Kamerakoordinaten müssen korrekt umgerechnet werden.

Beide Einstellungen beeinflussen das gesamte Foto. Die regionale Kombination entsteht erst bei der Fusion. Weiße, schwarze oder spiegelnde Flächen dürfen nicht allein aufgrund ihrer Helligkeit als fehlerhaft gelten.

Pro Region wird eine Schärfekurve über die getesteten Fokusstellungen aufgebaut. Zusätzliche Aufnahmen sind sinnvoll, wenn ein verlässliches Maximum fehlt oder am Rand des bisher untersuchten Fokusbereichs liegt. Ähnliche Fokusstellungen werden zusammengefasst. Bildzahl, Zeit und erfolglose Versuche erhalten Grenzen.

## 4. LiDAR als Startschätzung

An einem ruhenden Gimbal-Haltepunkt werden zunächst LiDAR-Tiefe und das zugehörige Hauptkamerabild erfasst. Die Apple-Pipeline erzeugt eine dichte Karte aus LiDAR- und Bildinformationen; Filter können Lücken füllen. Für die Planung sind Messgültigkeit und zeitliche Stabilität wichtig.

AVFoundation und ARKit unterscheiden sich in ihren Qualitätsdaten. Eine ARKit-confidenceMap wird nicht pauschal für AVDepthData vorausgesetzt. Ungefilterte AVFoundation-Tiefe schließt laut Apple Punkte geringer Konfidenz aus.

Große, verlässliche Tiefenbereiche dienen als Vorschläge für Fokuslagen. In unsicheren Bereichen, an Glas, an feinen Objektkanten und außerhalb brauchbarer Tiefenerfassung entscheidet die bildbasierte Suche.

### Hauptkamera zu Telekamera

Bloßes Zuschneiden und Skalieren reicht bei nahen Motiven nicht zuverlässig aus. Die Kameras stehen an unterschiedlichen Positionen und können andere Flächen sehen.

Der spätere geometrische Weg ist:

1. Tiefenwerte und Bildgeometrie anhand verfügbarer Kalibrierung entzerren.
2. Punkte in 3D zurückrechnen.
3. Mit der relativen Hauptkamera-/Tele-Geometrie transformieren.
4. In das Telebild projizieren.
5. Unsichere oder verdeckte Bereiche markieren und mit Bildregistrierung kontrollieren.

AVCaptureDevice.extrinsicMatrix(from:to:) kann für physische Kameras Werkskalibrierung liefern; der Wert ist optional. Rückseitige RAW-Aufnahmen liefern laut Apple derzeit keine entsprechende AVCameraCalibrationData pro Foto. Eine exakt passende Momentankalibrierung der Tele-ProRAW-Datei wird daher nicht vorausgesetzt.

Für den ersten Prototyp genügt eine konservative Zuordnung großer Tiefenregionen. Eine pixelgenaue Tele-Tiefenmaske ist ein eigener späterer Entwicklungsschritt.

## 5. Verarbeitung auf dem iPhone

Optionaler späterer Vergleich: mehrere Bilder mit derselben Kamera, Fokusstellung und Belichtung aufnehmen, registrieren und robust entrauschen. Im ersten 360°-Lauf wird ein Einzelbild pro Position verwendet. Bewegte oder schlecht ausgerichtete Bereiche dürfen nicht blind gemittelt werden. Qualitätswerte, kleine Vorschauen und Masken unterstützen schnelle Folgeentscheidungen.

Core Image, Metal und Accelerate bieten dafür Bausteine; eine fertige Viererfusion oder gemessene Geschwindigkeit wird nicht vorausgesetzt.

### Speicherplanung

Eigene Beispielrechnung für vollständig entwickelte RGBA16F-Puffer, keine Messung:

| Auflösung | Ein Puffer, 8 Byte je Pixel | Vier Eingangspuffer |
|---|---:|---:|
| 12 MP | ca. 96 MB | ca. 384 MB |
| 48 MP | ca. 384 MB | ca. 1,54 GB |

Decoder, Ausgabe, Bildpyramiden und Ausrichtungsdaten kommen hinzu. Deshalb sequenzielle oder kachelweise Verarbeitung, Wiederverwendung von Puffern und begrenzte Warteschlangen vorsehen. Aufnahmegeschwindigkeit, Speicher und Wärmeentwicklung am Gerät messen.

Rauschfusion soll die Bildqualität bei gleicher Pixelzahl verbessern; ihr tatsächlicher Nutzen ist erst zu messen. Eine zusätzliche Super-Resolution-Auswertung kleiner Verschiebungen wäre ein eigenes Verfahren.

Das Ergebnis wird als neues, möglichst lineares Zwischenbild mit ausreichender Farbtiefe und dokumentierten Metadaten gespeichert. Es ist nicht automatisch wieder eine originale Apple-ProRAW-Datei. Original-DNGs zunächst erhalten. Weniger Dateien garantieren keine proportional kleinere Datenmenge; Ausgabeformat und Kompression sind mitzubeurteilen.

## 6. HDR, Fokusfusion und ProRAW

Ausgangsentwurf für die Mac-Pipeline:

~~~text
Rauschfusion je Kamera/Fokus/Belichtung
    → Registrierung und HDR-Fusion je Fokusstellung
    → Registrierung und Fokusfusion
    → globale Panorama-/Detailfusion
    → gemeinsame abschließende Tonwertdarstellung
~~~

Die Reihenfolge ist ein zu vergleichender Ausgangspunkt. HDR- und Fokusfusion können später ebenfalls aufs iPhone verlagert werden, wenn Qualität und Gesamtzeit davon profitieren und ausreichende Korrekturmöglichkeiten erhalten bleiben.

ProRAW kann bereits Mehrbildverarbeitung enthalten. Apple beschreibt es als auf die Szene bezogen und linearisierbar, garantiert aber keine streng belichtungsproportionalen Werte über Aufnahmen. Gemeinsame Entwicklung, Belichtungs-/Farbanpassung und reale Qualitätsmessungen sind erforderlich.

Die automatische RAW-Bracket-Dokumentation bezieht sich auf Bayer RAW; ProRAW-Kompatibilität nicht pauschal voraussetzen. Bei den für hochauflösendes ProRAW relevanten Qualitätsmodi können manuell angeforderte ISO-/Zeitwerte überschrieben werden. Tatsächliche Metadaten und erhaltene Lichter/Schatten prüfen.

Fensteransichten benötigen häufig unterschiedliche Fokus- und Belichtungsgruppen für Raum und Außenansicht. Glas und Spiegelungen können die Tiefenmessung und Bildfusion beeinflussen. Weißabgleich innerhalb einer Serie konsistent behandeln. Bewegte Bereiche benötigen Referenzwahl beziehungsweise robuste Ausnahmen.

## 7. 1×-Referenz und 3×-Details

Ein 1×-Bild liefert eine Übersicht des gewünschten Ausschnitts. Für größere Bildwinkel wird zunächst ein 1×-Übersichtspanorama aufgebaut. Bei hohem Kontrast kann auch die Übersicht mehrere Belichtungen benötigen.

Die Teleaufnahmen werden zunächst anhand dieser Übersicht und der Winkeldaten grob zugeordnet und anschließend anhand ihrer überlappenden Nachbarn genauer registriert. Farben und Belichtung werden angeglichen; nur verlässliche Detailinformation wird übernommen.

Das Zielraster muss die höhere Tele-Abtastung erhalten. Die Übersicht darf die Ausgabe nicht auf ihre ursprünglichen 48 MP begrenzen. Eine Abdeckungskarte zeigt, wo bereits gute Tele-Details vorliegen. Wo keine brauchbare Teleaufnahme vorhanden ist, bleibt die Detailauflösung der Übersicht.

Progressive Refinement Imaging ist eine passende Forschungsgrundlage. Die ursprüngliche Methode setzt weitgehend ebene oder weit entfernte Szenen ohne starke Parallaxe voraus. Eine spätere tiefengestützte Erweiterung ist konzeptionell relevant, aber kein fertiger iPhone-ProRAW-Workflow.

## 8. Nachweis der Verbesserung

Als Referenz zuerst den bisherigen Ablauf reproduzieren. Danach einzelne Änderungen vergleichen: echte 3×-Kamera, dichte Fokusreihe, adaptive Fokuswahl, zusätzliche Belichtungen und Viererfusion.

Bewertet werden lokale Details, Rauschen, erhaltene Lichter/Schatten, Registrierungsfehler, Säume an Tiefenkanten, Geisterbilder, Bildränder, Aufnahmezeit, Rechenzeit und Datenmenge. Universelle Schärfeschwellen oder pauschale LiDAR-Genauigkeit werden nicht behauptet.
