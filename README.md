# iPhoneGigapixelPanorama

Mac-gesteuerte iPhone-Fotografie mit geplanten Erweiterungen für LiDAR, adaptive Fokus- und Belichtungsreihen, Rauschreduzierung und hochauflösende Tele-Panoramen.

## Ausgangspunkt

Nach Angaben des Projektinhabers existiert bereits eine Lösung aus **Mac-Software und eigener iPhone-App**, die den DJI Osmo Mobile 3 steuert, die iPhone-Kamera auslöst, alle Bilder auf dem Mac speichert und dort verarbeitet. Die Winkeldaten des iPhone werden ebenfalls bereits abgefragt.

Der vorhandene Quellcode liegt derzeit auf dem Mac und wurde für dieses Repository noch nicht eingesehen. Dieses Repository enthält zunächst **Konzept, Forschungsgrundlagen und einen Arbeitsplan**. Es enthält noch keine lauffähige Kamera-App oder implementierten neuen Funktionen.

## Zielhardware

- iPhone 14 Pro Max mit LiDAR
- Hauptkamera: 1×, bis zu 48 MP Apple ProRAW
- Eigene Telekamera: 3×, 12 MP
- DJI Osmo Mobile 3 mit bereits vorhandener Steuerung
- Mac für Aufnahmeplanung, Bildspeicherung und globale Verarbeitung

Unterstützte Kombinationen aus Kamera, Auflösung, Fokussteuerung und Ausgabeformat werden am Gerät abgefragt und überprüft. Der Projektname beschreibt das Ziel großer Detailpanoramen; ein Gigapixel-Ergebnis wurde noch nicht nachgewiesen.

## Geplante Erweiterungen

1. **Adaptive Fokus- und Belichtungsmesspunkte:** Ein Bild auswerten, fehlende Details lokalisieren, gezielt neu fokussieren beziehungsweise belichten und die Verbesserung prüfen. Fokus und Belichtung werden getrennt gesteuert.
2. **LiDAR als Planungshilfe:** Relevante Entfernungen gruppieren und unnötige Fokusaufnahmen vermeiden. Die tatsächliche Bildschärfe bleibt das entscheidende Prüfkriterium.
3. **Vierer-Rauschfusion auf dem iPhone:** Pro Kamera, Fokusstellung und Belichtung vier Aufnahmen ausrichten und robust zusammenführen. Bewegte Bereiche gesondert behandeln.
4. **HDR für große Helligkeitsunterschiede:** Beispielsweise Innenraum und helle Außenansicht durch ein Fenster mit mehreren Aufnahmen erfassen.
5. **1×-Übersicht mit 3×-Detailraster:** Die Übersicht dient als geometrisches und farbliches Gerüst. Überlappende Telebilder ergänzen die feinen Details auf einem entsprechend höher aufgelösten Zielraster.
6. **Aufgaben zwischen iPhone und Mac verteilen:** Zunächst lokale Viererfusion und Qualitätsanalyse auf dem iPhone; HDR, Fokusfusion, globale Panoramaausrichtung und abschließende Tonwertdarstellung auf dem Mac. Weitere Verlagerungen folgen erst nach Vergleichsmessungen.

## Vorgeschlagener Aufnahmeablauf

~~~text
1×-Übersicht oder Übersichtspanorama
    ↓
Panorama-Raster anhand der Übersicht und Winkeldaten planen
    ↓
Gimbalposition anfahren und Stillstand bestätigen
    ↓
LiDAR + zugehöriges Hauptkamerabild erfassen
    ↓
Benötigte Kamera-, Fokus- und Belichtungsgruppen auswählen
    ↓
Je Gruppe vier Wiederholungen aufnehmen und lokal entrauschen
    ↓
Detailgewinn prüfen, nötigenfalls gezielt ergänzen
    ↓
Nächste Position; anschließend globale Verarbeitung am Mac
~~~

Dieser Ablauf ist ein Entwurf und muss an den vorhandenen Code angepasst werden. Nicht jede Kachel braucht dieselbe Zahl an Fokuslagen, Belichtungen oder Wiederholungen.

## Technische Eckpunkte

- Die LiDAR-Tiefe gehört zunächst zur Hauptkameraperspektive. Für Telebilder sind Kamerageometrie, unterschiedliche Sichtbarkeit und Bildregistrierung zu berücksichtigen.
- ProRAW liefert laut Apple keine angehängte Fototiefenkarte. Separate Tiefenerfassung ist die vorgesehene Ausgangslösung.
- Eine Linsenposition ist kein universelles Entfernungsmaß. Autofokus auf ausgewählte Regionen und eine anschließende Schärfeprüfung sind ein praktikabler Einstieg.
- Bei 48-MP-ProRAW sind streng vorgegebene manuelle ISO-/Zeitwerte nicht pauschal garantiert. Die tatsächlichen Aufnahmeergebnisse müssen geprüft werden.
- Auch auf einem ruhenden Gimbal müssen Fokus- und Wiederholungsaufnahmen aufeinander ausgerichtet werden.
- Eine selbst berechnete Fusion ist ein neues Zwischenbild. Original-DNGs werden während der Entwicklung zusätzlich erhalten.

## Am Mac weiterarbeiten

1. Dieses Repository klonen.
2. Den bestehenden Mac-/iPhone-Code sichern und gezielt in das Repository übernehmen.
3. Den bisherigen Ablauf reproduzieren und dokumentieren.
4. Die Erweiterungen nach dem [Arbeitsplan](docs/WEITERARBEITEN.md) einzeln prüfen.

Das [technische Konzept](docs/KONZEPT.md) beschreibt Aufnahmeplanung, Aufgabenverteilung und Grenzen. Die [Quellen](docs/QUELLEN.md) trennen dokumentierte APIs, Forschung und noch zu prüfende Ableitungen. Weitere ungeprüfte Vorschläge, etwa zu Parallaxe am Gimbal und zum Gigapixel-Nachweis, sammelt [IDEEN_CLAUDE.md](docs/IDEEN_CLAUDE.md).

Der [Entwurf zur Aufnahmesteuerung](docs/ENTWURF_AUFNAHMESTEUERUNG.md) konkretisiert die adaptive Auswahl von Aufnahmegruppen, die Geometrie lokaler Viererfusionen und die zuverlässige Wiederaufnahme langer Sitzungen. Er enthält kleine Vergleichsversuche und präzisiert die bisherigen Auflösungs- und Parallaxerechnungen.

## Status und Lizenz

Stand: 2. November 2026. Dokumentation und Entwurf; keine Builds oder Hardwaretests der geplanten Erweiterungen durchgeführt. Sprache, Frameworks und Protokolle des bestehenden Projekts sind hier noch nicht dokumentiert.

Eine Projektlizenz ist noch nicht festgelegt. Verlinkte Veröffentlichungen und fremder Quellcode behalten ihre jeweiligen Rechte und Lizenzen.
