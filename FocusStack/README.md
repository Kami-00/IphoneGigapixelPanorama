# FocusStack – lokale Bildauswertung und Fokusfusion

`FocusStack.command` doppelklicken und den Ordner mit den Aufnahmen auswählen. Das Werkzeug verarbeitet direkt im Ordner liegende HEIC-, HEIF-, JPEG-, PNG- und TIFF-Bilder. Unterordner werden nicht eingelesen. Nach Abschluss öffnet sich ein lokaler Vergleich mit Schieberegler. Es erfolgt kein Upload.

Die Originale werden nicht verändert. Jeder Start über den Starter legt einen neuen datierten Ergebnisordner im gewählten Ordner an. Verarbeitung mit der auf diesem Mac bereits vorhandenen Python-Umgebung:
`/Users/kami/Documents/Projekte/Biemer-360/venv/bin/python`
Der Starter ist daher zunächst auf diesem Rechner eingerichtet; `FOCUSSTACK_PYTHON` kann eine andere geeignete Umgebung wählen. Abhängigkeiten: Python 3, NumPy, OpenCV, Pillow und für HEIC macOS `sips`.

## Verarbeitung

1. Orientierung vereinheitlichen; Detailindikatoren und Helligkeit pro Aufnahme ermitteln. Automatische Referenzauswahl, bei Bedarf per `--reference` überschreibbar.
2. Gemeinsame Merkmale finden, geometrisch ausrichten und per ECC verfeinern. Dies gleicht auch kleinere Größenänderungen beim Fokussieren aus.
3. Farben/Helligkeit robust an die Referenz angleichen.
4. Zusätzliche lokale Ausrichtung mit begrenztem optischem Fluss. Vorwärts-/Rückwärtsprüfung vermeidet viele unzuverlässige Zuordnungen. Lokale Verschiebungen sind auf zwölf Originalpixel begrenzt. `--no-local` deaktiviert diesen Schritt für einen Kontrollversuch.
5. Detailkarten auf mehreren Skalen bestimmen. Bereiche ohne verlässlichen Schärfegewinn bleiben in der Referenz. Kategorielle Mehrheitsfilter beruhigen die Auswahlflächen.
6. Ausgewählte scharfe Bereiche mit einer Laplace-Pyramide verbinden. Keine generativen Details, keine zusätzliche Nachschärfung, kein pauschaler Mittelwert als Endergebnis.

## Ergebnisse

- `Vergleich.html`: lokal bedienbarer Vorher-/Nachher-Regler, Detailvergleiche und Quellenkarte.
- `Focus-Stack.png`: verlustfreies Endergebnis in Originalauflösung.
- `Focus-Stack.jpg`: hochwertige JPG-Fassung.
- `Referenz.jpg`, `Mittelwert.jpg`: Kontrollbilder.
- `Schaerfeauswahl.jpg`: dominante Quellaufnahme pro Bereich vor der weichen Überblendung; Legende im Vergleich.
- `bericht.json`: Parameter, verwendete Bilder, Ausrichtungswerte und Auswahlanteile.
- `arbeitsdateien`: dekodierte und ausgerichtete Zwischenbilder, zur Nachprüfung aufbewahrt.

Beispiel für die aktuelle Serie:

```sh
/Users/kami/Documents/Projekte/Biemer-360/venv/bin/python /Users/kami/Documents/Projekte/FocusStack/focus_stack.py /Users/kami/Desktop/stack --reference IMG_7195.HEIC
```

## Grenzen und Bildprüfung

Fokusstapel benötigen tatsächlich unterschiedlich scharfe Ebenen. Rauschen und kamerainterne Schärfung können wie echte Details wirken; Schärfeindikatoren sind daher keine Messung der optischen Auflösung. An Tiefenkanten, verdeckten Flächen oder bewegten Gegenständen kann auch eine lokale Ausrichtung scheitern. Die Software rekonstruiert keine Details, die in keiner Aufnahme vorhanden sind.

HEIC-Dateien werden über macOS in 8-Bit-SDR-RGB dekodiert; dies ist keine RAW-/HDR-Verarbeitung. Alle Aufnahmen müssen nach der Orientierung dieselbe Bildgröße haben. Stark unpassende Bilder werden mit Begründung ausgelassen. Wenn weniger als zwei Bilder verlässlich ausgerichtet werden können, stoppt die Verarbeitung.

Prüfung für diese Entwicklung: synthetische komplementäre Fokusbereiche müssen klar besser als ihr Mittelwert zusammengesetzt werden; bekannte Verschiebungen müssen wiedergefunden werden; ungültige Bereiche dürfen nicht gewinnen. Dazu visuelle Prüfung der echten Serie. Ein bestandener Test garantiert kein fehlerfreies Ergebnis für jedes Motiv.

Tests:

```sh
cd /Users/kami/Documents/Projekte/FocusStack
/Users/kami/Documents/Projekte/Biemer-360/venv/bin/python -m unittest -v
```
