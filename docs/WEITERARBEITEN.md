# Weiterarbeit am Mac

## 1. Vorhandenen Stand übernehmen

- [ ] Den bestehenden Projektordner sichern.
- [ ] Mac-Software und eigene iPhone-App gezielt in dieses Repository übernehmen.
- [ ] Sprachen, Frameworks, Build-/Startbefehle und unterstützte Betriebssysteme dokumentieren.
- [ ] Gimbalprotokoll, Kameraauslösung, Bildübertragung und vorhandene Bildverarbeitung beschreiben.
- [ ] Einen bisherigen Aufnahme-/Verarbeitungslauf als reproduzierbare Referenz erfassen.

## 2. Kamera und Metadaten verifizieren

- [ ] Verfügbare physische Kameras, RAW-Formate und Fotoabmessungen protokollieren.
- [ ] Eine echte 3×-Teleaufnahme mit 12 MP nachweisen; Hauptkamera-Ausschnitte erkennen.
- [ ] 1×-ProRAW-Auflösung anhand tatsächlich gelieferter Bilder prüfen.
- [ ] Art, Zeitbezug und Referenzsystem der bestehenden Winkeldaten dokumentieren.
- [ ] Aufnahme-IDs und Zuordnung zu Position, Kamera, Fokus, Belichtung und Wiederholung festlegen.

## 3. Adaptive Messpunkte ergänzen

- [ ] Fokus und Belichtungsmessung getrennt an Bildregionen steuern.
- [ ] Foto-/Vorschaukoordinaten einschließlich Drehung und Ausschnitt überprüfen.
- [ ] Einstellvorgänge mit Zeitlimit abwarten und das Ergebnis bildbasiert prüfen.
- [ ] Schärfe, Belichtungsqualität, Bewegung und Messunsicherheit getrennt bewerten.
- [ ] Fehlversuchsgrenzen und erneute Aufnahme nur bei erwartetem Detailgewinn einführen.

## 4. LiDAR speichern und nutzen

- [ ] Am ruhenden Haltepunkt Tiefe und synchrones Hauptkamerabild speichern.
- [ ] Verfügbare Kalibrierung, Orientierung, Filterzustand und gültige Werte mitführen.
- [ ] Mehrere bekannte Entfernungen bei unterschiedlicher Beleuchtung vergleichen.
- [ ] Überdeckungskante zwischen zwei Tiefen im Hauptkamera-/Tiefen-/Telebild prüfen.
- [ ] Zunächst große sichere Tiefenbereiche für Fokusvorschläge verwenden.

## 5. Viererfusion auf dem iPhone

- [ ] Dieselben vier Originale am iPhone und am Mac verarbeiten und vergleichen.
- [ ] Registrierung und robuste Behandlung bewegter Bereiche ergänzen.
- [ ] Lineares Zwischenformat und Farbraum festlegen; Original-DNGs zunächst behalten.
- [ ] Speicher, Wärmeentwicklung, Aufnahmezeit und tatsächliche Übertragungsmenge messen.
- [ ] Für problematische Gruppen einen nachvollziehbaren Rückfall auf weniger Frames vorsehen.

## 6. HDR und Fokusfusion ausbauen

- [ ] Dichte Fokusreihe als Vergleich zur adaptiven Auswahl aufnehmen.
- [ ] Für Fensteransichten brauchbare Außen- und Innenraumdetails nachweisen.
- [ ] Tatsächliche ProRAW-Belichtungen und Bracket-Unterstützung prüfen.
- [ ] Mit 1/2/4/8 Wiederholungen den tatsächlichen Rauschgewinn und Detailerhalt vergleichen.
- [ ] Säume, Bewegung und Fehler der Ausrichtung an kritischen Ausschnitten beurteilen.

## 7. Referenzgestützte Tele-Panoramen

- [ ] 1×-Übersicht für den gesamten Zielausschnitt erzeugen.
- [ ] Überlappendes 3×-Raster planen.
- [ ] Tele-zu-Übersicht und Tele-zu-Tele gemeinsam prüfen.
- [ ] Zielauflösung anhand der Tele-Abtastung wählen.
- [ ] Abdeckung und lokale Qualität sichtbar machen.
- [ ] Erst danach LiDAR-gestützte Parallaxekorrektur und weitere iPhone-Verarbeitung bewerten.

## Einstieg für die nächste Arbeitssitzung

> Lies README.md, docs/KONZEPT.md und diesen Arbeitsplan. Untersuche zuerst den vorhandenen Mac- und iPhone-Code. Dokumentiere, wie Gimbal, Kamera, Winkeldaten, Bildübertragung und Verarbeitung bereits funktionieren. Baue darauf schrittweise auf und wähle die erste überprüfbare Erweiterung anhand des realen Codes. Trenne bestätigte Funktionen, geplante Änderungen und offene Hardwarefragen.
