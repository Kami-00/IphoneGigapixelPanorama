# Quellen und Einordnung

Recherchestand: 2. November 2026. Die Quellen belegen Bausteine und Forschungsansätze. Sie belegen keine bereits implementierte oder am Projektgerät getestete Gesamtlösung.

## Hardware und Aufnahme

- [iPhone 14 Pro Max: technische Daten](https://support.apple.com/en-in/111846) — Hauptkamera, Telekamera, LiDAR und Aufnahmeformate.
- [Apple: LiDAR über AVFoundation, WWDC22](https://developer.apple.com/videos/play/wwdc2022/110429/) — Hauptkamera-/LiDAR-Pipeline, Tiefenfilter, Stream und Fotos. Genannte damalige Auflösungen nicht pauschal als heutige Gerätegrenze übernehmen.
- [Apple: LiDAR-Beispielprojekt](https://developer.apple.com/documentation/avfoundation/capturing-depth-using-the-lidar-camera) — synchronisierte Bild-/Tiefenerfassung.
- [Apple: manuelle Fokusstellung](https://developer.apple.com/documentation/avfoundation/avcapturedevice/lensposition) — keine universelle Zuordnung der Linsenposition zu einer Entfernung.
- [Apple: Fokusmesspunkt](https://developer.apple.com/documentation/avfoundation/avcapturedevice/focuspointofinterest) und [Belichtungsmesspunkt](https://developer.apple.com/documentation/avfoundation/avcapturedevice/exposurepointofinterest) — getrennte Messpunkte; anschließend jeweilige Betriebsart auslösen.
- [Apple: Core-Motion-Geräteorientierung](https://developer.apple.com/documentation/coremotion/getting-processed-device-motion-data) — Winkeldaten und Bezugssysteme.

## Geometrie

- [Apple: AVDepthData](https://developer.apple.com/documentation/avfoundation/avdepthdata) — Tiefendaten, Bildverzeichnung und Kalibrierung.
- [Apple: relative Geometrie zweier Kameras](https://developer.apple.com/documentation/avfoundation/avcapturedevice/extrinsicmatrix%28from%3Ato%3A%29) — optionale Werkskalibrierung physischer Kameras.
- [Apple-Ingenieurantwort zu RAW-Kalibrierdaten](https://developer.apple.com/forums/thread/826469) — aktuelle Einschränkung bei rückseitigen RAW-Aufnahmen; Stand Juni 2026.

## Schärfe, RAW und Belichtung

- [Apple: schärfstes Bild einer Serie bestimmen](https://developer.apple.com/documentation/accelerate/finding-the-sharpest-image-in-a-sequence-of-captured-images) — Laplace-Varianz als Ausgangspunkt, einschließlich Hinweis auf Rauschempfindlichkeit.
- [Choi et al.: Improved Image Selection for Focus Stacking](https://cs.uwaterloo.ca/~vanbeek/Publications/focusStacking.pdf) — adaptive Auswahl hochauflösender Fokusaufnahmen anhand schnellerer Vorschauaufnahmen.
- [Li et al.: Scene-Adaptive Image Acquisition for Focus Stacking](https://image.ee.tsinghua.edu.cn/pdf/2018_ICIP_lwt.pdf) — szenenabhängige Aufnahmeplanung; die berichteten Ergebnisse beziehen sich unter anderem auf simulierte Datensätze.
- [Stanford: Focal Stack Compositing](https://cs468.stanford.edu/papers/focalstack/) — Kombination unterschiedlicher Fokusebenen und Tiefenkanten.
- [Apple: ProRAW aufnehmen und verarbeiten, WWDC21](https://developer.apple.com/videos/play/wwdc2021/10160/) — ProRAW, lineare Entwicklung und Einschränkungen der Tiefendatenlieferung.
- [Apple DTS: RAW-/ProRAW-Radiometrie](https://developer.apple.com/forums/thread/825883) — die jüngste Korrektur im Thread berücksichtigen: keine dokumentierte Garantie streng belichtungsproportionaler Werte über Aufnahmen.
- [Apple: manuelle Belichtungssteuerung](https://developer.apple.com/documentation/avfoundation/avcapturedevice/setexposuremodecustom%28duration%3Aiso%3Acompletionhandler%3A%29) — Qualitätspriorisierung kann die tatsächlich verwendeten Einstellungen beeinflussen.
- [Apple: hochauflösende Aufnahme, WWDC26](https://developer.apple.com/videos/play/wwdc2026/304/) — unterstützte Fotoabmessungen abfragen und tatsächlich gelieferte Maße prüfen.

## Verarbeitung und Detailmosaik

- [Apple: eigene Core-Image-Bildprozessoren](https://developer.apple.com/documentation/coreimage/ciimageprocessorkernel) — native Bausteine für eigene Verarbeitung mit Metal oder CPU-Verfahren.
- [Apple: Metal-Speicherverbrauch reduzieren](https://developer.apple.com/documentation/metal/reducing-the-memory-footprint-of-metal-apps) — Grundlage für Speicher- und Pufferplanung.
- [Kluge, Weyrich, Kolb: Progressive Refinement Imaging](https://reality.cs.ucl.ac.uk/projects/progressive-imaging/kluge19progressive-lowres.pdf) — Übersichtsreferenz schrittweise mit höher aufgelösten Detailbildern ergänzen; ursprüngliche Annahme geringer Parallaxe.
- [Kluge, Weyrich, Kolb: tiefengestützte Erweiterung, 2023](https://reality.tf.fau.de/publications/2023/kluge2023progressive/kluge2023progressive.html) — progressive Farb-/Tiefenrepräsentation und Korrektur von Perspektivunterschieden. Forschungsrichtung, kein fertig übernehmbarer iPhone-ProRAW-Ablauf.
