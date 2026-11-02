# Entwurf: Aufnahmeplanung und zuverlässige Sitzungen

Stand: 2. November 2026. Weiterführung von [KONZEPT.md](KONZEPT.md) und [IDEEN_CLAUDE.md](IDEEN_CLAUDE.md). Die folgenden Entscheidungen sind Vorschläge für den Ausbau der vorhandenen Mac-Software und eigenen iPhone-App. Sie sind nicht implementiert oder am Gerät geprüft.

## 1. Zuerst fehlende Qualität bestimmen, dann eine Aufnahmegruppe wählen

Eine starre Kombination aller Kameras, Fokusstellungen, Belichtungen und Wiederholungen erzeugt viele Bilder, die keine zusätzlichen Details beitragen. Der nächste Ausbau sollte deshalb Aufnahmegruppen gezielt auswählen.

**Vier Wiederholungen je Ergebnisbild bleiben zunächst der gewünschte Standard.** Die erste Optimierung reduziert unnötige Fokus-/Belichtungskombinationen. Ein optionaler Abbruch nach einem oder zwei Bildern wäre eine spätere, gesondert zu prüfende Erweiterung.

Für jeden Bildbereich werden mehrere Fragen getrennt beantwortet:

| Merkmal | Zu prüfende Frage | Mögliche nächste Aktion |
|---|---|---|
| Geometrie | Ist der Bereich zuverlässig zugeordnet und ausgerichtet? | Registrierung prüfen oder Ansicht erneut erfassen |
| Fokus | Sind relevante Details bei brauchbarer Belichtung scharf? | Passende Fokusgruppe ergänzen |
| Belichtung | Sind relevante Lichter oder Schatten ohne Details? | Weitere Belichtung bei gehaltenem Fokus |
| Rauschen | Sind feine Details nach Fusion ausreichend erkennbar? | Nutzen einer weiteren gleichartigen Gruppe prüfen |
| Bewegung | Passt der Inhalt noch zwischen den Aufnahmen zusammen? | Referenzbild wählen oder Gruppe neu aufnehmen |
| Detailauflösung | Liegen echte Tele-Details oder nur Übersichtsdetails vor? | Fehlende Teleaufnahme planen |
| Verlässlichkeit | Erlaubt die vorhandene Struktur überhaupt eine Aussage? | Als unsicher markieren oder gezielte Diagnoseaufnahme |

Ein heller, dunkler oder verrauschter Bereich wird nicht automatisch als unscharf behandelt. Weiß bleibt gegebenenfalls weiß, Schwarz schwarz. Bei fehlender Struktur wird die Schärfe nicht als bewiesen ausgegeben.

Auch Bewegungsunschärfe, misslungene Registrierung und falscher Fokus können ähnlich aussehen. Eine Folgeaufnahme muss die vermutete Ursache prüfen: etwa einen anderen Fokus, eine tatsächlich kürzere Belichtung oder besseren Stillstand. Wiederholtes Autofokussieren ist kein allgemeines Mittel gegen jede Unschärfe.

## 2. Ein einfacher Planer vor einem komplexen Optimierungsmodell

Am Anfang reichen nachvollziehbare Regeln:

- Mehrere unscharfe Regionen in ähnlicher Entfernung mit einer gemeinsamen Fokusgruppe erfassen.
- Für scharfe, aber abgeschnittene Fensterdetails eine dunklere Gruppe bei gleichem Fokus ergänzen.
- Bei kaum sichtbarer Struktur zuerst die Belichtung verbessern und danach die Schärfe prüfen.
- Bei Bewegung oder fehlerhafter Ausrichtung einen anderen Versuch wählen beziehungsweise mit weniger Frames fusionieren.
- Fehlende LiDAR-Tiefe als **unbekannt** behandeln und über Bilder prüfen. Sie bedeutet nicht automatisch unendlich.

Als Prioritätsregel bietet sich an:

> Bevorzuge die Aktion, die voraussichtlich die meisten noch fehlenden relevanten Details pro zusätzlicher Sekunde liefert.

Das ist eine eigene Heuristik, keine bewiesene optimale Lösung. Kamerawechsel, Fokussieren, Belichtungsanpassung und spätere Rückkehr zu einer Position kosten ebenfalls Zeit. Bei paralleler Verarbeitung zählt die Verzögerung des Gesamtablaufs; Einzelzeiten dürfen nicht blind addiert werden.

Unsichere Regionen brauchen außerdem ein begrenztes Diagnosebudget. Eine geringe Messverlässlichkeit darf sie nicht dauerhaft von der Planung ausschließen. Wichtig sind eine begrenzte Zahl an Versuchen und die klare Meldung verbleibender Probleme.

## 3. Eine Position kann beendet sein, ohne alle Qualitätsziele zu erfüllen

Für die Live-Abdeckung sind diese Zustände hilfreich:

- noch nicht erfasst;
- erfasst, aber noch nicht geprüft;
- ausreichend für das gewählte Ziel;
- unzureichend und durch eine bekannte Aktion voraussichtlich verbesserbar;
- nicht zuverlässig bewertbar;
- unter den aktuellen Bedingungen nicht weiter verbesserbar.

Eine Position endet entweder mit erfüllten Zielen oder mit dokumentierten Restproblemen. Gründe für das Ende können auch ein Zeit-/Bildlimit, wiederholte Fehlversuche oder ausbleibender Detailgewinn sein. Ein solcher Abbruch darf die Qualitätskarte nicht einfach grün färben.

Die Anzeige sollte getrennt zeigen, wo nur die 1×-Grundlage vorliegt und wo echte 3×-Details ausreichend belegt sind. Eine große Ausgabedatei allein bestätigt keine gleichmäßig hohe Detailauflösung.

## 4. Das LiDAR-Farbbild zusätzlich als Brückenbild nutzen

Pro Haltepunkt ist bereits ein synchrones Hauptkamera-RGB-/LiDAR-Paar vorgesehen. Das Farbbild kann eine zweite Aufgabe übernehmen:

~~~text
Globale 1×-Übersicht
        ↕
Aktuelles Hauptkamera-RGB am Haltepunkt + LiDAR
        ↕
Aktuelle 3×-Detailaufnahme
        ↔ überlappende Tele-Nachbarn
~~~

Diese Zwischenreferenz könnte die grobe Lokalisierung bei Lichtänderungen und unterschiedlichen Bildausschnitten erleichtern. Dafür ist nicht zwingend eine zusätzliche 48-MP-Aufnahme nötig. Das ist eine eigene Ableitung aus der vorhandenen Tiefenerfassung und progressiven Referenzfusion.

Kamerawechsel, Aufnahmezeitpunkte, Verzeichnung und verschiedene Kamerazentren bleiben zu berücksichtigen. Das Brückenbild liefert eine Startschätzung; Tele-Nachbarüberlappungen und eine Kontrolle anhand unabhängiger Bildpunkte bleiben erforderlich.

## 5. Jede iPhone-Fusion braucht eine eindeutige Bildgeometrie

Die vier Bilder werden auf das Pixelraster eines benannten Referenzframes ausgerichtet. Das Fusionsbild übernimmt diese definierte Geometrie, nicht einen beliebigen Mittelwert der Gyrowinkel.

Zum Ergebnis gehören mindestens:

- Referenzframe und verwendete Einzelbilder;
- gültige Bildfläche, Ausschnitt und Lage des Pixelursprungs;
- relevante Ausrichtungstransformationen;
- Kamera-/Formatangaben sowie Orientierung und Aufnahmezeitraum;
- Algorithmusversion und verwendete Fusionsparameter;
- Karte der lokal brauchbaren Beiträge oder eine entsprechend definierte Verlässlichkeitskarte.

**Vier aufgenommen bedeutet nicht vier überall nutzbar.** Bei bewegtem Blattwerk können lokal nur einzelne Frames beitragen. Die Mac-Auswertung muss erkennen können, wenn eine rechnerisch vollständige Vierergruppe in einem Bereich kaum Rauschvorteil liefert.

Originalaufnahmen bleiben während der Entwicklung zusätzlich erhalten. Eine neue Algorithmusversion kann dieselben Originale später anders bewerten und fusionieren; ihre Herkunft bleibt nachvollziehbar.

## 6. Aufnahmeende, sichere Speicherung und Qualität getrennt bestätigen

Diese Ereignisse sind unterschiedliche Zustände:

1. Alle Kameraaufnahmen der Gruppe sind beendet.
2. Die Dateien sind auf dem iPhone vollständig gespeichert.
3. Die Dateien beziehungsweise Ergebnisse sind vollständig am Mac angekommen und geprüft.
4. Die Qualitätsprüfung ist abgeschlossen.
5. Der gewünschte Bildbereich erfüllt das Ziel oder hat dokumentierte Restprobleme.

Der Gimbal kann nach bestätigtem Ende sämtlicher für den aktuellen Positionsbesuch geplanter Kameraaufnahmen grundsätzlich weiterfahren, während Fusion und Übertragung nachlaufen. Weitere Fokus- oder Belichtungsgruppen an derselben Position sind dabei ausdrücklich eingeschlossen. Dafür braucht es eine Bewegungsfreigabe, eine Bereitschaftsmeldung und begrenzte Warteschlangen. Das iPhone darf wegen älterer Berechnungen nicht unbegrenzt weitere Aufträge annehmen.

Eine kurze Vorprüfung vor dem Weiterfahren soll offensichtliche Fehler erkennen. Ist die endgültige Qualitätsprüfung noch offen, wird die Position entsprechend markiert. Eine spätere Nachforderung kann dann eine erneute Anfahrt erfordern; diese Kosten gehören zur Planung.

Die tatsächliche Überlappung von Aufnahme, Berechnung und Übertragung ist am Gerät zu messen. Bei Speicher-, Temperatur- oder Dateirückstand wird die nächste Gruppe verzögert, Rechenarbeit an den Mac abgegeben oder kontrolliert pausiert. Apples Thermal-State-Schnittstelle ist ein verfügbarer Baustein zur Beobachtung der Wärmebelastung; sie liefert keine fertige projektspezifische Drosselstrategie.

## 7. Wiederholbare Kommandos und ein belastbares Sitzungsjournal

Jede Sitzung, Kachel, Aufnahmegruppe und Einzelaufnahme erhält eine stabile Kennung. Ein Auftrag verweist auf eine Planrevision. Ein tatsächlicher neuer Aufnahmeversuch erhält eine neue Versuchkennung.

Wenn nach einem Verbindungsproblem derselbe Auftrag erneut gesendet wird, fragt beziehungsweise meldet die App zuerst seinen vorhandenen Zustand. Gleiche Kennung mit anderen Parametern gilt als Konflikt. Ein verlorener Empfangsnachweis darf nicht automatisch eine neue Kameraauslösung verursachen.

Auch das iPhone braucht dafür ein dauerhaft gespeichertes Auftragsjournal beziehungsweise Dateimanifest. Der Auftrag wird vor der ersten Auslösung festgehalten. Nach einem Absturz werden zweifelhafte Zustände zunächst als unklar behandelt und mit vorhandenen Dateien und Metadaten abgeglichen. Ein Journal ausschließlich auf dem Mac reicht dafür nicht.

Der Mac bestätigt den Dateieingang nach vollständigem Empfang, gespeicherter Zuordnung und Prüfsummenprüfung. Eine beschädigte oder unvollständige Übertragung wird erneut übertragen. Das ist ein Entwurf für wiederholbare Kommunikation, keine Garantie physikalisch exakt einmaliger Auslösung bei jedem denkbaren Absturz.

### Unterbrochene Vierergruppen

Zwei vorhandene Frames sind noch keine vollständige Vierergruppe. Nach Kameraneustart, Gimbalbewegung oder deutlicher Lichtänderung wird ein neuer Versuch begonnen, statt alte und neue Bilder nur wegen der Anzahl zu vermischen.

Eine Auswertung mit weniger nutzbaren Frames kann ein bewusst dokumentierter Rückfall sein. Ursprünglicher Plan, tatsächlich erfasste Bilder und tatsächlich verwendete Beiträge bleiben getrennt sichtbar.

### Fortsetzen nach Neustart

Gleiche Gyrowerte garantieren nach einem Neustart nicht dieselbe ursprüngliche Ansicht. Eine gespeicherte Referenzkachel hilft, die Ausrichtung anhand des Bildes wiederherzustellen; die Winkeldaten unterstützen diesen Vorgang.

Bei verschobenem Stativ, stark veränderter Szene oder nicht wiederherstellbarer Ansicht wird ein neuer Sitzungsabschnitt angelegt. Ein Lichtwechsel erzeugt einen neuen Beleuchtungsabschnitt. Frühere Aufnahmen können erneut zu prüfen sein. Eine globale Helligkeitskorrektur kann veränderte Schatten oder bewegte Objekte nicht vollständig ausgleichen.

## 8. Überlappung und Wartezeit messen

Zunächst konservativ planen und anschließend tatsächliche Fehler auswerten:

- Erreichen und Beruhigen der angeforderten Ausrichtung;
- gültige Bildfläche nach Ausrichtung und Beschnitt;
- Fokusänderungen und optische Stabilisierung;
- Fehler und räumliche Verteilung der übereinstimmenden Bildpunkte.

Viele Übereinstimmungen in nur einer Ecke sichern nicht die gesamte Naht ab. Eine Begrenzung auf die Bildmitte kann Randprobleme reduzieren, kostet aber zusätzliche Aufnahmen und wird erst nach Vergleichstests entschieden.

Für die Wartezeit ist neben Bewegung auch die aktive Kamera wichtig. Dieselbe kleine Winkelschwingung wirkt sich bei Tele anders auf die Pixel aus. Gyrodaten sind eine Hilfe; die optische Bildqualität muss zusätzlich geprüft werden.

Die Dauer langer Läufe wird aus gemessenen Aufnahme-, Wechsel-, Bewegungs-, Rechen- und Übertragungszeiten geschätzt. Eine feste Stundenangabe allein aus der Zahl der Auslösungen wäre nicht belastbar.

## 9. Kleine Versuche mit getrennten Fragen

Die folgenden Versuche sind geplant und noch nicht durchgeführt.

### A. Aufnahmeprotokoll und Wiederaufnahme

Drei Kacheln mit jeweils einer Vierergruppe genügen für einen ersten Protokolltest. Denselben Auftrag mehrfach senden; Verbindung nach Bild zwei trennen; einen Empfangsnachweis verlieren lassen; eine Übertragung beschädigen. Prüfen, ob Zustand und Dateien nachvollziehbar bleiben und unbeabsichtigte zusätzliche Aufnahmen erkannt werden.

Zusätzlich Prozessabbrüche zwischen Kameraauslösung und vollständig gespeicherter Datei sowie zwischen Mac-Speicherung und Empfangsbestätigung prüfen. Diese Fälle testen die dauerhafte Zustandsführung; ein bloßer Verbindungsverlust deckt sie nicht ab.

Anschließend App/Gimbal neu starten und eine Referenzansicht wiederfinden. Danach das Stativ bewusst verschieben und prüfen, ob die alte Sitzung als nicht unmittelbar fortsetzbar erkannt wird.

### B. Aufnahmeplaner zunächst offline vergleichen

Eine feste Kamera und unbewegte Ansicht mit strukturierten Zielen in drei Tiefen, einem hellen und einem dunklen Bereich verwenden. Eine beispielhafte Kontrollmenge umfasst drei Fokusstellungen, drei Belichtungen und je vier Wiederholungen: **36 Auslösungen**.

Diese Menge ist keine garantierte perfekte Fokus-/HDR-Abdeckung. Tatsächliche Belichtungen, Schärfe und Formatunterstützung werden mitgeprüft.

Den Planer später auf dieser Aufzeichnung abspielen: Er darf für seine nächste Entscheidung nur bereits ausgewählte Gruppen sehen. Die übrigen Aufnahmen dienen ausschließlich der anschließenden Bewertung. Dadurch lässt sich der Algorithmus vergleichen, ohne die komplette Hardware bei jeder Änderung neu aufbauen zu müssen.

Qualitätsschwellen vorher festlegen oder auf einer getrennten Aufzeichnung kalibrieren. Auch vorab aus ungesehenen Gruppen berechnete Qualitätswerte dürfen dem Planer nicht zugänglich sein.

Erfassen: benötigte Gruppen, fehlende Details gegenüber der Kontrollmenge, fälschlich als ausreichend bewertete Bereiche und Verhalten bei Strukturarmut oder ausbleibender Verbesserung. Für Bewegung und andere Störungen eine eigene Aufnahmevariante ergänzen; die unbewegte Kontrollmenge prüft diesen Fall nicht.

### C. Nutzen der Brückenbilder prüfen

Eine 1×-Übersicht und ein überlappendes 2×2-Teleraster aufnehmen, zunächst mit festem Fokus und gleicher Belichtung. Die lokalen Hauptkamera-/LiDAR-Bilder mitführen.

Drei Ausrichtungen vergleichen: nur Tele-Nachbarn; Tele mit globaler Übersicht; Tele mit Übersicht und lokalen Brückenbildern. Unabhängige Kontrollpunkte, Doppelkonturen, gültige Fläche, Fehler und Zeitbedarf beurteilen.

### D. Lokale Fusion gegen denselben Mac-Lauf prüfen

Dieselben Originale auf beiden Geräten verarbeiten. Erst Detailerhalt, Rauschen und Bewegungsartefakte vergleichen, dann Gesamtzeit, Speicher und Datenmenge. Weniger Ergebnisdateien allein beweisen noch keinen schnelleren oder kleineren Gesamtprozess.

## 10. Einordnung der bisherigen Zahlen

Die Zahlen in IDEEN_CLAUDE.md sind Szenarien, keine gemessenen Gerätegrenzen. Die horizontale Bildwinkelrechnung passt unter den dort gewählten Annahmen. Einige Schlussfolgerungen brauchen jedoch Präzisierung:

- Im dort angenommenen Parallaxemodell liegt die Ein-Pixel-Grenze bei etwa 56 m für 2 cm und 140 m für 5 cm Achsversatz; nicht pauschal bei 50 m. Der reale Versatz und die tatsächlichen Szenentiefen sind zu messen.
- Die Gigapixel-Tabelle beschreibt eine gewählte equirektangulare Ausgabeabtastung. Ausgabegröße, abgedeckter Bildwinkel beziehungsweise Kugeloberfläche und echte optische Detailauflösung sind verschiedene Größen.
- Für denselben zentralen Ausschnitt ergibt sich nominell ein linearer Tele-/48-MP-Abtastfaktor von (77/24) × (4032/8064), also etwa 1,60. Der tatsächlich sichtbare Detailgewinn wird daraus nicht garantiert.
- Ein Klemmenadapter wäre erst nach Messung von Achsen, Bewegungsbereich und tatsächlich zu verbessernder Parallaxe ein sinnvoller eigener Entwicklungsschritt.

## 11. Empfohlene Reihenfolge

1. Bestehenden Mac-/iPhone-Code einsehen und den aktuellen Ablauf reproduzieren.
2. Aufnahmeidentitäten, Zustände, sichere Speicherung und Wiederaufnahme ergänzen.
3. Eine feste Kamera mit Viererfusion und nachvollziehbarer Pixelgeometrie vergleichen.
4. Den regionalen Aufnahmeplaner auf einer kleinen Kontrollmenge offline prüfen.
5. Tele-Raster, Brückenbilder und Live-Abdeckung zusammenführen.
6. Erst anschließend mehr Verarbeitung aufs iPhone und tiefengestützte Parallaxekorrektur bewerten.

Die Rechenteile aus tiefenpano sind eine mögliche Ausgangsbasis. Vor Übernahme müssen insbesondere Tele-/48-MP-Kameraprofile, unbekannte Tiefe, Kalibrierannahmen und tatsächliche Fokus-Rückmeldungen geprüft werden. Vorhandene Tests belegen ohne aktuellen Lauf keinen erfolgreichen Stand und ersetzen keine Hardwareprüfung.

## Grundlagen und Quellen

- [Apple: ProRAW-Radiometrie](https://developer.apple.com/forums/thread/825883) — die neueste Korrektur im Thread berücksichtigen; ProRAW ist kein ungeprüftes Modell unabhängiger Sensorframes.
- [Apple: Temperaturzustand beobachten](https://developer.apple.com/documentation/foundation/processinfo/thermalstate-swift.property) — Baustein für Lastbeobachtung.
- [Choi et al.: Improved Image Selection for Focus Stacking](https://cs.uwaterloo.ca/~vanbeek/Publications/focusStacking.pdf) — Grundlage szenenabhängiger Bildauswahl.
- [Kluge et al.: Progressive Refinement Imaging](https://reality.cs.ucl.ac.uk/projects/progressive-imaging/kluge19progressive-lowres.pdf) — progressive Kombination einer Übersicht mit Detailaufnahmen.
- [Tiefengestützte Erweiterung, 2023](https://reality.tf.fau.de/publications/2023/kluge2023progressive/kluge2023progressive.html) — weiterführender geometrischer Forschungsansatz.

Die hier vorgeschlagene Zustandsfolge, Brückenbild-Nutzung, Qualitätsbewertung und Auftragsbehandlung sind eigene technische Ableitungen. Quellen und vorhandene APIs belegen deren Bausteine, keine bereits geprüfte Gesamtlösung.
