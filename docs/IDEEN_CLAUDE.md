# Ideen von Claude

Stand: 2. November 2026. Vorschläge, die über [KONZEPT.md](KONZEPT.md) und
[WEITERARBEITEN.md](WEITERARBEITEN.md) hinausgehen. Nichts davon ist umgesetzt
oder am Gerät geprüft. Alle Zahlen sind **gerechnet, nicht gemessen**. Die
Annahmen stehen jeweils dabei.

## 1. Parallaxe durch den Gimbal

Ein Smartphone-Gimbal dreht um die Mitte des Telefons, nicht um die
Eintrittspupille des Objektivs. Die 3×-Linse liegt neben der Drehachse und
verschiebt sich bei jedem Schwenk. Nahe Motive verrutschen dadurch gegenüber
fernen, und an den Kachelnähten entstehen Fehler, die keine Registrierung ganz
beseitigt.

Abschätzung für einen Kachelschritt von rund 18° (3×, 30 % Überlappung):

| Linse neben der Achse | Motiv in 2 m | 10 m | 50 m |
|---|---:|---:|---:|
| 2 cm | 28 px | 5,6 px | 1,1 px |
| 5 cm | 71 px | 14 px | 2,8 px |

Annahmen: Versatz der Linse × Schwenkwinkel als Verschiebung des
Kamerazentrums, 3×-Kamera mit 77 mm Kleinbildäquivalent und 4032 px Breite,
also rund 159 px je Grad. Der tatsächliche Versatz im OM3 ist nicht gemessen.

Unter einem Pixel bleibt der Fehler erst bei Motiven in etwa 50 m Entfernung.

Ideen dazu:

- **Klemmenadapter**, der das Telefon so versetzt, dass die 3×-Linse über der
  Schwenkachse liegt, mit Ausgleichsgewicht für die Balance. Lässt sich in
  Blender modellieren und drucken. Vorher den echten Versatz messen.
- **LiDAR als Parallaxe-Warnung**: Kacheln mit nahen Motiven markieren. Sie
  brauchen mehr Überlappung, eine eigene Behandlung beim Stitching oder
  zumindest einen Hinweis im Ergebnis.

## 2. Gigapixel nachweisen

Winkelauflösung und erreichbare Größe einer vollen Kugel (360° × 180°):

| Kamera | Bildwinkel horizontal | Auflösung | volle Kugel |
|---|---:|---:|---:|
| 1× 48 MP | 71,6° | 113 px/° | 0,82 GP |
| 1× 12 MP | 71,6° | 56 px/° | 0,21 GP |
| 3× 12 MP | 25,3° | 159 px/° | 1,64 GP |

Annahmen: 4:3-Bild, Kleinbildäquivalent 24 mm und 77 mm, Bildbreite
8064 px und 4032 px.

Folgerungen:

- Mit der 1×-Kamera ist ein Gigapixel selbst als vollständige Kugel nicht
  erreichbar.
- Mit der 3×-Kamera braucht ein Gigapixel mindestens **61 % der Vollkugel**.
- 360° × 150° mit 30 % Überlappung ergibt etwa **250 Telekacheln**. Mit vier
  Wiederholungen und rund zwei Fokus- oder Belichtungsgruppen sind das etwa
  **2.000 Auslösungen**.

**Vorher messen, ob sich das 3×-Raster lohnt.** Auf dem Papier bringt 3× nur
den Faktor 1,4 an Pixeln je Grad gegenüber 1×-48-MP. Der 48-MP-Modus nutzt
einen Quad-Bayer-Sensor, sein echter Detailgehalt liegt vermutlich unter
48 MP, der reale Gewinn also über 1,4. Ein **Siemensstern** in fester
Entfernung, einmal mit 1×-48-MP und einmal mit 3× fotografiert, klärt das,
bevor die 3×-Pipeline gebaut wird.

## 3. Lichtänderung bei langen Läufen

2.000 Auslösungen dauern eher eine Stunde als zehn Minuten. In dieser Zeit
ändern Sonne und Wolken die Szene.

- Eine **Referenzkachel** alle paar Minuten erneut aufnehmen und damit
  Helligkeit und Farbe über den Lauf nachführen.
- Bei einem plötzlichen Helligkeitssprung in der Vorschau **pausieren**,
  statt eine Kachel unter anderem Licht aufzunehmen.
- Die **Kachelreihenfolge** so wählen, dass benachbarte Kacheln zeitlich nah
  beieinander liegen.

## 4. Abdeckungskarte live während der Aufnahme

Die Abdeckungskarte aus KONZEPT.md Abschnitt 7 schon während der Aufnahme am
Mac anzeigen: welche Kacheln vorhanden, scharf und gut belichtet sind. Lücken
lassen sich dann nachschießen, solange das Stativ noch steht.

## 5. Fortsetzen nach Abbruch

Ein **Sitzungsjournal**, das jede abgeschlossene Kachel festhält. Ein leerer
Akku oder ein Verbindungsabbruch nach 180 von 250 Kacheln bedeutet dann keinen
Neustart. Dazu prüfen, ob sich die Ausgangsausrichtung des Gimbals nach einem
Neustart wiederherstellen lässt.

## 6. Wiederholgenauigkeit des OM3 messen

Angefahrenen und tatsächlich erreichten Winkel vergleichen, über die
vorhandenen Winkeldaten des iPhone. Davon hängt ab, wie viel Überlappung
wirklich nötig ist. Jedes Prozent weniger spart bei 250 Kacheln spürbar Zeit.

## 7. Simulator in Blender

Eine Testszene mit bekannter Tiefe, echter Schärfentiefe und dem
Linsenversatz aus Abschnitt 1 rendern. Damit lassen sich Fokuswahl, Stapeln,
Parallaxebehandlung und Stitching ohne Hardware testen, und zwar gegen eine
exakt bekannte Vorlage. Blender läuft dafür auch headless.

## 8. Deep-Zoom-Viewer

Ein Gigapixel-Bild öffnet niemand als Datei. Gekachelt im DZI-Format mit
OpenSeadragon lässt es sich im Browser zoomen, zum Beispiel unter einer eigenen
Subdomain. Ein Gigapixel ergibt rund 20.000 Kacheln. Das liegt am Dateilimit
eines Cloudflare-Pages-Deployments, als Speicher passt R2 besser. Limits vor der
Umsetzung prüfen.

## 9. Bausteine aus `tiefenpano`

Im Nachbarordner `D:\test\git\tiefenpano` liegt ein früherer Entwurf mit
getesteten Python-Teilen, die zu offenen Punkten hier passen:

- **Fokusstaffelung aus der Schärfentiefe**: rechnet aus einem LiDAR-Tiefenbereich
  die Folge der Fokusebenen aus. Das macht aus „LiDAR als Startschätzung“
  (KONZEPT.md Abschnitt 4) eine konkrete Rechnung.
- **Kalibrierung lensPosition ↔ Entfernung über das LiDAR**: misst die Kurve je
  Gerät als Gerade in Dioptrien, prüft ihre Plausibilität und meldet
  Fokusebenen außerhalb des Stellwegs.
- **Kachelplaner** mit Ausdünnung der Spalten zu den Polen hin.
- **Hugin-Projektdatei** mit den Gimbalwinkeln als Startwerten.

Der Entwurf setzt Apples DockKit für die Gimbalsteuerung voraus. Für den
vorhandenen OM3-Weg müsste das angepasst werden, die Rechenteile sind davon
unabhängig.
