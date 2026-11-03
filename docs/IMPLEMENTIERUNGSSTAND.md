# Importierter Entwicklungsstand – 02.11.2026

Die vorhandenen Arbeitsordner wurden als Quellcode übernommen. Laufende lokale Installationen und Originalaufnahmen bleiben unverändert. Keine Fotos, DNGs, Ergebnisse, privaten Verbindungsdateien, Xcode-Benutzerdaten, signierten Programme oder heruntergeladenen Fremdbibliotheken sind enthalten.

## Komponenten und Datenfluss

- `OsmoStudio/mac/OsmoStudio.swift`: SwiftUI-Mac-Oberfläche, startet den lokalen Python-Dienst und bedient ihn über HTTP.
- `OsmoStudio/server.py`: Python-HTTP-Dienst auf Port 48763, lokale Token-Paarung, Fotoaufträge und DNG-Übertragung; Bluetooth über Bleak/CoreBluetooth mit DJI-OM3-Steuerpaketen. Keine Cloud-Verarbeitung.
- `OsmoStudio/iphone/OsmoCamera.swift`: SwiftUI, AVFoundation, CoreMotion. 1×-Hauptkamera, 48-MP-Apple-ProRAW, Fokus und Belichtung, relativer Orientierungsverlauf, Originalspeicherung auf dem iPhone und Übertragung zum Mac. Kein absoluter Stern-/Kompassbezug.
- `automation.py`, `wide_capture.py`: geregelte Bewegung mit frischen Sensordaten, Stillstandserkennung und Abbruch bei fehlender Motorantwort; Standardreihen, manuelle Zweipass-Fortsetzung und große Kugel-Teilaufnahme.
- `processing.py`, `sharp_composite.py`: RAW-Entwicklung und Panorama mit schmalen Überblendungen.
- `estimate_wide.py`, `spherical_export.py`: Bildmerkmale mit Gyro-Orientierung, native sphärische Projektion, lokaler Farbabgleich, schwarze unaufgenommene Bereiche, PNG/JPEG und GPano-Metadaten.
- `make_360_viewer.py`: lokale drehbare HTML-Vorschau (verkleinert), Links auf Originalauflösung.
- `SimpleSuperresolution`: Mac-Starter plus ImageMagick-Vergrößerung, Hugin-Ausrichtung, Mittelwert und Median; keine generativen Bilddetails.
- `FocusStack`: separate lokale Fokusfusion mit geometrischer und lokaler Ausrichtung.

## Einrichtung und Start

Benötigt werden macOS mit Xcode/Command Line Tools, Python 3.11 oder neuer und Homebrew auf Apple Silicon. Die iPhone-App hat als Projektminimum iOS 17; der importierte Hardwarepfad wurde mit iPhone 14 Pro Max und DJI Osmo Mobile 3 verwendet. Eine vollständige Kompatibilitätsprüfung weiterer Geräte/macOS-Versionen steht aus.

```sh
brew install exiftool imagemagick
./setup-mac.sh
open 'OsmoStudio/Osmo Studio.app'
```

Die beiden Mac-Apps verwenden standardmäßig `.venv/bin/python` im Repository. `PANORAMA_PYTHON` kann einen anderen Interpreter angeben. Für Superresolution separat Hugin installieren, siehe `SimpleSuperresolution/tools/README.txt`.

Das Xcode-Projekt `OsmoStudio/iphone/OsmoCamera.xcodeproj` öffnen, eigenes Signing-Team und gegebenenfalls eigene Bundle-ID einstellen und auf dem iPhone installieren. Die persönliche Team-ID wurde aus dem Import entfernt. Mac und iPhone im gleichen vertrauenswürdigen WLAN betreiben; Paarung erfolgt über die Mac-App. Der lokale Dienst verwendet HTTP und ist kein öffentlich bereitzustellender Webdienst.

Weitere Einstiege:

```sh
open SimpleSuperresolution/Superresolution.app
./FocusStack/FocusStack.command
.venv/bin/python OsmoStudio/spherical_export.py /pfad/zum/aufnahmeordner --resume
```

`OsmoStudio/manual_extremes.py` ist ein bewusst separat zu startender Hardwareversuch, der reale Bewegungen und Aufnahmen auslöst. Er gehört nicht in automatische Tests. Weitere Vorschau-/Vergleichsskripte sind Entwicklungshelfer, teilweise an konkrete Datensatzgeometrien gebunden.

## Bereits ausgeführte reale Versuche

Am 01.11.2026: 26 ProRAW-DNGs mit 8064 × 6048 Quellpixeln aufgenommen. Equirektangulärer Export 36180 × 18090 Pixel (654,5 MP), davon ca. 79,5 % fotografiert und 20,5 % schwarz. Dies ist eine 360°×180°-Datei mit Abdeckungslücken, kein lückenloser Rundumblick. Helligkeitsübergänge und Lichtschleier an Leinwand und Decke bleiben sichtbar. Die Gesamtpixelzahl ist kein Nachweis gleichwertiger optischer Auflösung.

SimpleSuperresolution: drei 12-MP-Regalbilder in etwa 37 Sekunden verarbeitet, 6008 × 8029 Pixel nach Beschnitt. Ruhigere Flächen, kein klarer Schärfegewinn gegenüber dem besten Einzelbild. Die drei Bilder hatten teilweise unterschiedliche Fokus-/Belichtungseinstellungen.

Die Datensätze verbleiben lokal und sind hier nicht mitgeliefert. Ein erneuter End-to-End-Test erfordert eigene Aufnahmen und angeschlossene Geräte.

## Offene Arbeit

- Der echte 3×-Tele-Ring über 360° bleibt offen. Ein 3×3-Teleraster mit neun einzelnen 12-MP-ProRAW-Aufnahmen ist inzwischen implementiert und real geprüft (siehe unten).
- Nachtmodus, astronomische Nachführung und Video-Zeitraffer wurden besprochen, sind aber noch nicht implementiert.
- Die vollständige reale Zweipass-Aufnahme und verlässliche Rollkorrektur sind nicht nachgewiesen.
- Portable Pfade der Hauptstarter wurden für den Import angepasst; lokale historische Anleitungstexte enthalten teilweise ursprüngliche Rechnerpfade. Diese Datei beschreibt den Einstieg im Repository.

## Automatische Prüfung ohne Hardware

```sh
(cd OsmoStudio && ../.venv/bin/python -m unittest discover -p 'test_*.py')
(cd SimpleSuperresolution && ../.venv/bin/python -m unittest discover -p 'test_*.py')
(cd FocusStack && ../.venv/bin/python -m unittest discover -p 'test_*.py')
```

Die Prüfungen decken unter anderem Steuergrenzen, veraltete Sensordaten, Zweipass-Zustände, PNG-Pixelerhalt, Mittelwert/Median und Fokusfusion ab. Sie ersetzen keinen Hardware- oder Bildqualitätstest.

Importprüfung am 02.11.2026: 23 OsmoStudio-, 2 Superresolution- und 4 FocusStack-Tests bestanden (29 insgesamt). Beide Mac-Apps aus dem Repository erfolgreich gebaut; OsmoStudio meldet eine bestehende SwiftUI-Deprecation-Warnung. Geheimnisscan ohne Treffer. Die iPhone-App wurde bei diesem Import nicht erneut gebaut oder installiert; keine neue Hardwareaufnahme durchgeführt.

## Ergänzung: 3×3-Telepanorama und WLAN-Wechsel (02.11.2026)

Die Mac-App erneuert den Verbindungslink aus der aktuellen Netzadresse bei der Statusaktualisierung. Nach WLAN-Wechsel den neuen QR-Code/Link verwenden; die iPhone-App erneut verbinden.

Der Knopf „3×3-Panorama · echte 3×-Telekamera“ schaltet auf die physische Telekamera (Zoomfaktor 1 auf diesem Objektiv), bestätigt RAW-Verfügbarkeit und plant neun Positionen mit 25 % Winkelüberlappung. Eine Auslösung pro Position, keine Wiederholungsstapel. Der Knopf „Zurück zur 1×-Hauptkamera“ stellt den bisherigen 48-MP-Weg wieder her.

Für ProRAW muss ein Format mit `isHighestPhotoQualitySupported` gewählt werden. Der erste Versuch mit einem beliebigen 12-MP-Format wurde deshalb vor der Bewegung abgewiesen. Der korrigierte Hardwarelauf lieferte neun 4032 × 3024 DNGs; EXIF bestätigte 9 mm / 77 mm Kleinbildäquivalent. Gemeldeter Hochformat-Bildwinkel 19,07° × 25,25°, Schritte 14,30° × 18,94°.

Die Standardmerkmalsuche konnte nicht alle neun Ansichten verbinden. Der Telepfad nutzt daher SIFT mit gespeicherten Gyro-Winkeln, 77-mm-Brennweiteninitialisierung und einer vollständig verbundenen, gyro-geprüften Merkmalsstruktur. Native Projektion und schmale Nahtüberblendung bleiben erhalten. Reales Ergebnis: 7395 × 9866 Pixel, alle neun Quellen; Gesamtansicht geprüft. Keine vollständige 360°-Abdeckung und kein Nachweis perfekter Kanten an jeder Tiefe.

27 Steuerungs-/Verarbeitungstests bestanden, iPhone-Build und drahtlose Installation erfolgreich. Die beiden lokalen Arbeitskopien wurden für diesen Versuch aktualisiert. Rohbilder bleiben außerhalb des Git-Repositories.

## Kartenwand: lokale Ausrichtung (02.11.2026)

`OsmoStudio/planar_stitch.py <Aufnahmeordner>` verarbeitet vorhandene PNGs aus `Entwickelt` als annähernd flaches Motiv. Gemeinsame perspektivische Ausrichtung, Ausschluss widersprüchlicher Logo-Zuordnungen und ein geglättetes lokales Korrekturgitter reduzieren Kantenversatz. Originalpixel werden erst beim finalen Rendern interpoliert; schmale Nahtüberblendung. Dieser separate Versuch ersetzt nicht den Standardweg für Räume oder 360°.

An den neun Teleaufnahmen sank der Median der paarweisen Kontrollpunkt-Mediane von 2,36 Pixeln (globale Flächenausrichtung) auf 0,64 Pixel (lokales Gitter). Diese Kontrollpunkte wurden nicht zur Anpassung verwendet. Die Zahlen vergleichen die beiden neuen Ausrichtungsstufen, nicht das alte sphärische Panorama. Vier Detailausschnitte visuell geprüft; Kunststoffblister, Reflexionen und andere Tiefen bleiben mögliche Restfehler. Vollständige Ausgabe mit schwarzen Außenflächen: 9670 × 12801 Pixel. Alte Ergebnisse und Quellen bleiben erhalten. Drei gezielte Tests prüfen Pixelidentität, inverse Verschiebung und Projektionsnormalisierung.
