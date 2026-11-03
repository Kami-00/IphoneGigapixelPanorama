# FlatMosaic – ein Bild aus überlappenden Aufnahmen einer flachen Fläche

Für Regale, Wände, Tafeln, Karten und Pläne: mehrere überlappende Aufnahmen werden zu einem Bild in voller Quellauflösung zusammengesetzt. Gedacht für Motive, die näherungsweise in einer Ebene liegen, und bewusst getrennt vom sphärischen Panoramaweg in `OsmoStudio`, der eine reine Drehung um einen Punkt annimmt.

Für eine **ebene Fläche ist eine Homographie exakt**, auch wenn zwischen den Aufnahmen aus der Hand seitlich versetzt wurde. Genau deshalb wird hier das volle Acht-Parameter-Modell geschätzt und nicht nur Drehung und Brennweite.

```sh
.venv/bin/python FlatMosaic/flat_mosaic.py bild1.dng bild2.dng bild3.dng --out Ergebnisse/Wand.jpg
```

DNG wird über `OsmoStudio/tools/render_raw` entwickelt (Apples CoreImage-RAW-Pipeline, einmal `./setup-mac.sh` ausführen), HEIC über macOS `sips`; PNG, JPEG und TIFF werden direkt gelesen. Die Originale werden nicht verändert. Entwickelte Zwischenbilder landen in `arbeitsdateien` neben der Zieldatei und werden wiederverwendet.

Nützliche Schalter:

- `--scale 0.15` – schneller Probelauf in kleinem Maßstab. Ausrichtung und Nähte sind dieselben wie bei voller Auflösung.
- `--calibration datei.json` – die einmal berechnete Ausrichtung sichern und wiederverwenden. Ein zweiter Lauf in anderer Größe überspringt damit die gesamte Merkmalssuche.
- `--full-canvas` – die gesamte aufgenommene Fläche mit schwarzen Rändern statt des größten vollständig gefüllten Rechtecks.
- `--reg-max 4000` – größere Arbeitsgröße der Merkmalssuche. Genauer, aber langsamer.
- `--grid 7x2 --order serpentine` – das Aufnahmemuster mitgeben: sieben Aufnahmen je Reihe, jede zweite Reihe rückwärts. Die Dateien werden in Aufnahmereihenfolge übergeben. Gesucht wird dann nur noch zwischen tatsächlich benachbarten Aufnahmen.

**Bei sich wiederholenden Motiven ist `--grid` der entscheidende Schalter.** Rotes Lochblech, Regalraster oder gleiche Verpackungen passen genauso gut eine ganze Kartenbreite daneben. Ohne das Muster entstehen Zuordnungen, die in sich stimmig und trotzdem falsch sind; mit Muster entfallen sie, bevor überhaupt gesucht wird.

## Verarbeitung

1. RAW entwickeln, falls nötig; alle Aufnahmen müssen dieselbe Bildgröße haben.
2. SIFT-Merkmale auf einer begrenzten Arbeitsgröße. Je Bildpaar Zuordnung, RANSAC-Homographie und eine Flächenprüfung: Treffer, die eng beieinander liegen, werden verworfen, weil sich wiederholende Verpackungsgrafik sonst falsche Paare erzeugt. Mit `--grid` werden von vornherein nur benachbarte Aufnahmen verglichen.
3. Aufspannbaum vom am besten verbundenen Bild aus, stärkste Überlappungen zuerst.
4. Globaler Ausgleich über alle Zuordnungen gleichzeitig. Paare, die schon der Verkettung widersprechen, werden **vor** dem Ausgleich verworfen: ist eine Falschzuordnung erst in der Optimierung, zieht sie alle Bilder mit und fällt danach nicht mehr auf. Die Schwelle richtet sich nach der Arbeitsgröße, damit gewöhnliche Kettendrift erhalten bleibt. Danach eine zweite Runde gegen den Median. Kein Paar wird verworfen, wenn dadurch ein Bild die Verbindung verliert.
5. Belichtungsangleich und GraphCut-Nähte auf verkleinerter Fassung, damit die Nähte um Gegenstände herumlaufen.
6. Zuschnitt auf das größte vollständig gefüllte Rechteck, **bevor** überblendet wird. Danach Mehrband-Überblendung in voller Auflösung, Bild für Bild geladen und sofort wieder freigegeben.

Schritt 6 ist nicht nur Kosmetik: bei sechs 48-MP-Aufnahmen ist die umschließende Fläche 277 MP, das gelieferte Rechteck 169 MP. Der Zuschnitt vorweg entscheidet auf einem 16-GB-Rechner darüber, ob der Lauf durchläuft oder in die Auslagerung geht.

## Ergebnisse

- Die Zieldatei in voller Quellauflösung; `.jpg` oder `.png` je nach Endung.
- Daneben eine gleichnamige `.json` mit Quellen, Maßen, Restabweichung je Bildpaar, verworfenen Paaren und Laufzeit.
- Kamera-, Objektiv- und Zeitangaben werden per `exiftool` von der ersten Aufnahme übernommen, sofern vorhanden.

## Grenzen und Bildprüfung

Die Software ergänzt nichts, was nicht fotografiert wurde; unbedeckte Flächen bleiben schwarz. Gegenstände, die deutlich aus der Ebene herausragen, lassen sich von einer Homographie grundsätzlich nicht gleichzeitig mit dem Hintergrund zur Deckung bringen. Die Nähte laufen deshalb um solche Stellen herum; eine Restabweichung bleibt und ist Parallaxe, kein Rechenfehler. Pixelzahl ist kein Nachweis gleichwertiger optischer Auflösung: Verwacklung und Fokusfehler der Einzelbilder bleiben erhalten.

Zweiter geprüfter Lauf am 02.11.2026: 14 Telaufnahmen einer Lochblechwand, iPhone 14 Pro Max bei 77 mm, 12 MP ProRAW, als 7×2-Schlangenlauf aufgenommen. **Ohne `--grid` ging es schief**: von 91 Bildpaaren waren 58 Falschzuordnungen am Lochmuster, sechs der vierzehn Aufnahmen landeten an der falschen Stelle, und das Ergebnis war ein 40-MP-Streifen statt eines Zweizeilers. Mit `--grid 7x2` blieben von 31 Nachbarpaaren 26 übrig, alle Aufnahmen saßen richtig, Restabweichung 1,68 px bei Arbeitsgröße 3000 (2,3 px im Original). Ergebnis 13474 × 5941 Pixel (80 MP). Die wiedergefundene Lage wurde gegen die Aufnahmereihenfolge geprüft: obere Reihe gleichmäßig nach rechts, Wende, untere Reihe nach links, 43 % Reihenüberlappung. Reihennaht an vier Stellen bei 100 % geprüft.

Erster geprüfter realer Lauf am 02.11.2026: sechs 48-MP-ProRAW-Aufnahmen einer Regalwand, iPhone 17 Pro bei 100 mm aus der Hand, ohne Angabe eines Aufnahmemusters. Mit `--reg-max 4000` neun Bildpaare, keines verworfen, Restabweichung 1,79 px bei dieser Arbeitsgröße, das entspricht 3,6 Pixeln im Original. Ergebnis 11636 × 14555 Pixel (169 MP) in 67 Sekunden; die umschließende Fläche wäre 277 MP gewesen. Bei der Standardarbeitsgröße 2400 ist eines der Paare eine Falschzuordnung und wird verworfen, ohne dass eine Aufnahme die Verbindung verliert. Nähte und Treffpunkt von vier Bildern bei 100 % geprüft, keine Doppelkonturen und keine Helligkeitssprünge.

Tests:

```sh
cd FlatMosaic
../.venv/bin/python -m unittest -v
```

Geprüft werden: wiedergefundene bekannte Homographie zwischen zwei Ansichten, vollständiger Wiederaufbau einer synthetischen Wand aus vier Ansichten einschließlich Musterabgleich gegen das Original, Zuschnitt ohne schwarze Ränder gegenüber der ganzen Fläche, Verwerfen einer Falschzuordnung bei erhaltener Verbindung, Nachbarschaft aus Schlangenlauf und Raster, Beschränkung der Suche auf dieses Muster, erhaltene Ausrichtungsangaben bei wiederverwendeter Kalibrierung, größtes gefülltes Rechteck, Maßstabstreue der Bildkästen sowie Ablehnung nicht überlappender und einzelner Aufnahmen. Ein bestandener Test sichert kein gutes Ergebnis für jedes Motiv zu.

## Verhältnis zu `OsmoStudio/planar_stitch.py`

`OsmoStudio/planar_stitch.py` verfolgt dieselbe Geometrie und bringt zwei Dinge mit, die hier fehlen: eine dünn besetzte Jacobi-Matrix für den Ausgleich und zurückgehaltene Kontrollpunkte als ehrliche Fehlerschätzung. Umgekehrt fehlen dort RAW-Entwicklung, Aufruf mit beliebigen Dateien, Zuschnitt vor dem Überblenden und die wiederverwendbare Kalibrierung. Die beiden gehören zusammengeführt. Zum Zeitpunkt dieser Ergänzung wurde `planar_stitch.py` gerade an anderer Stelle bearbeitet und deshalb nicht angefasst.
