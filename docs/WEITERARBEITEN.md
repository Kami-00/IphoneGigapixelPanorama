# Weiterarbeit am Mac

## 1. Vorhandenen Stand übernehmen

- [ ] Den bestehenden Projektordner sichern.
- [ ] Mac-Software und eigene iPhone-App gezielt in dieses Repository übernehmen.
- [ ] Sprachen, Frameworks, Build-/Startbefehle und unterstützte Betriebssysteme dokumentieren.
- [ ] Gimbalprotokoll, Kameraauslösung, Bildübertragung und vorhandene Bildverarbeitung beschreiben.
- [ ] Einen bisherigen Aufnahme-/Verarbeitungslauf als reproduzierbare Referenz erfassen.

## 2. Erster Nachweis: 360° aus 3×-Einzelbildern

- [ ] Vorhandenen Aufnahmeweg auf die echte 3×-Telekamera einstellen und die tatsächliche Kamera beziehungsweise Bildmetadaten prüfen.
- [ ] Zunächst einen horizontalen 360°-Ring auf einer Höhe mit ausreichender Überlappung planen; letzte und erste Aufnahme müssen ebenfalls überlappen.
- [ ] Vorhandene Autofokus-/Belichtungsfunktionen und ein bereits unterstütztes Fotoformat nutzen.
- [ ] Jede Position anfahren, Stillstand abwarten und im regulären Ablauf genau einmal auslösen.
- [ ] Alle Bilder mit eindeutiger Position und verfügbaren Winkeldaten vollständig am Mac speichern.
- [ ] Den vollständigen Umlauf am Mac zu einer durchgehenden 360°-Ansicht zusammensetzen.
- [ ] Abdeckungslücken, Horizont, Doppelkonturen, Übergänge und die Schließnaht prüfen.
- [ ] Bildzahl, Aufnahmezeit, Kamera-/Fotoformat, Ergebnisabmessungen und verbleibende Fehler dokumentieren.

Entrauschen ist dabei ausgeschaltet. OCR, LiDAR, HDR, Fokusreihen, 1×-Referenzfusion, ProRAW-Zwang und ein Gigapixel-Nachweis sind keine Voraussetzung. Erst wenn dieser einfache Ablauf funktioniert, folgen die optionalen Ausbaustufen unten.

## 3. Kamera und Metadaten verifizieren

- [ ] Verfügbare physische Kameras, RAW-Formate und Fotoabmessungen protokollieren.
- [ ] Eine echte 3×-Teleaufnahme mit 12 MP nachweisen; Hauptkamera-Ausschnitte erkennen.
- [ ] 1×-ProRAW-Auflösung anhand tatsächlich gelieferter Bilder prüfen.
- [ ] Art, Zeitbezug und Referenzsystem der bestehenden Winkeldaten dokumentieren.
- [ ] Aufnahme-IDs und Zuordnung zu Position, Kamera, Fokus, Belichtung und Wiederholung festlegen.

## 4. Adaptive Messpunkte ergänzen

- [ ] Fokus und Belichtungsmessung getrennt an Bildregionen steuern.
- [ ] Foto-/Vorschaukoordinaten einschließlich Drehung und Ausschnitt überprüfen.
- [ ] Einstellvorgänge mit Zeitlimit abwarten und das Ergebnis bildbasiert prüfen.
- [ ] Schärfe, Belichtungsqualität, Bewegung und Messunsicherheit getrennt bewerten.
- [ ] Fehlversuchsgrenzen und erneute Aufnahme nur bei erwartetem Detailgewinn einführen.

## 5. LiDAR speichern und nutzen

- [ ] Am ruhenden Haltepunkt Tiefe und synchrones Hauptkamerabild speichern.
- [ ] Verfügbare Kalibrierung, Orientierung, Filterzustand und gültige Werte mitführen.
- [ ] Mehrere bekannte Entfernungen bei unterschiedlicher Beleuchtung vergleichen.
- [ ] Überdeckungskante zwischen zwei Tiefen im Hauptkamera-/Tiefen-/Telebild prüfen.
- [ ] Zunächst große sichere Tiefenbereiche für Fokusvorschläge verwenden.

## 6. Optionale Rauschfusion vergleichen

- [ ] Zuerst Einzelbilder gegen Wiederholungsgruppen vergleichen; keine feste Viererpflicht voraussetzen.
- [ ] Bei aktiviertem Vergleich dieselben Originale am iPhone und am Mac verarbeiten und beurteilen.
- [ ] Registrierung und robuste Behandlung bewegter Bereiche ergänzen.
- [ ] Lineares Zwischenformat und Farbraum festlegen; Original-DNGs zunächst behalten.
- [ ] Speicher, Wärmeentwicklung, Aufnahmezeit und tatsächliche Übertragungsmenge messen.
- [ ] Für problematische Gruppen einen nachvollziehbaren Rückfall auf weniger Frames vorsehen.

## 7. HDR und Fokusfusion ausbauen

- [ ] Dichte Fokusreihe als Vergleich zur adaptiven Auswahl aufnehmen.
- [ ] Für Fensteransichten brauchbare Außen- und Innenraumdetails nachweisen.
- [ ] Tatsächliche ProRAW-Belichtungen und Bracket-Unterstützung prüfen.
- [ ] Mit 1/2/4/8 Wiederholungen den tatsächlichen Rauschgewinn und Detailerhalt vergleichen.
- [ ] Säume, Bewegung und Fehler der Ausrichtung an kritischen Ausschnitten beurteilen.

## 8. Referenzgestützte Tele-Panoramen

- [ ] 1×-Übersicht für den gesamten Zielausschnitt erzeugen.
- [ ] Überlappendes 3×-Raster planen.
- [ ] Tele-zu-Übersicht und Tele-zu-Tele gemeinsam prüfen.
- [ ] Zielauflösung anhand der Tele-Abtastung wählen.
- [ ] Abdeckung und lokale Qualität sichtbar machen.
- [ ] Erst danach LiDAR-gestützte Parallaxekorrektur und weitere iPhone-Verarbeitung bewerten.

## Einstieg für die nächste Arbeitssitzung

> Lies README.md, docs/KONZEPT.md und diesen Arbeitsplan. Untersuche zuerst den vorhandenen Mac- und iPhone-Code. Dokumentiere, wie Gimbal, Kamera, Winkeldaten, Bildübertragung und Verarbeitung bereits funktionieren. Baue darauf auf und priorisiere zunächst den einfachen 360°-Durchlauf aus 3×-Einzelbildern mit genau einer Aufnahme pro Position. Optionale Rauschfusion und die übrigen Ausbaustufen folgen erst danach. Trenne bestätigte Funktionen, geplante Änderungen und offene Hardwarefragen.
