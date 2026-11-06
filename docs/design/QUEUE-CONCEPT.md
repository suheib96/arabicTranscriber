# Warteschlange — visueller Entwurf v1

Genehmigte visuelle Referenz; die Umsetzung in 0.2.0 ergänzt die anschließend genehmigte Pause/Fortsetzen-Funktion. Erstellt mit dem eingebauten ImageGen-Werkzeug, ohne CLI-Fallback.

Bild: `queue-concept-v1.png`.
Referenz: `.scratch/arabic-transcriber/ui-idle.png`, eine vorhandene Software-UI-Aufnahme des bisherigen Quellcodes. Das aktuell per `uv run` geöffnete native Python-Fenster konnte über Computer Use nicht erfasst werden (Timeout); dies ist kein frischer Screenshot dieser Sitzung.

## Entscheidungen

- Bestehende Farben, Kopfzeile, Dateiauswahl und Transkriptaktionen bleiben als visuelle Grundlage erhalten.
- Eine kompakte Liste zwischen Eingabe und Transkript zeigt einen laufenden, zwei wartende und einen fertigen Auftrag. Der laufende Auftrag trägt seinen eigenen Fortschritt. Keine geschätzte Gesamtwartezeit.
- Eingabe und „Transkribieren“ bleiben während eines Auftrags verfügbar. Ein weiterer Klick reiht den neuen Auftrag ein.
- Auswahl und Ausführung sind unabhängig: die linke Hervorhebung bezeichnet das angezeigte Transkript, der Statuspunkt den laufenden Auftrag. Ein ausgewähltes fertiges Transkript bleibt beim automatischen Weiterlaufen ausgewählt.
- Stoppen am laufenden Auftrag und Entfernen eines wartenden Eintrags sind getrennte Aktionen. Der anschließend genehmigte Umfang ergänzt eine globale Pause/Fortsetzen-Aktion und „Speicher freigeben“; Planung und Sortierung bleiben außerhalb des Umfangs.
- Jeder Eintrag besitzt sein eigenes Transkript; Kopieren, Export und Zeiten beziehen sich auf den ausgewählten Eintrag.
- Die Beispieltitel sind fiktiv. Beim Hinzufügen fragt die App den echten YouTube-Titel ab, bevor sie Audio herunterlädt. Bis dahin zeigt die Zeile „Titel wird geladen“ mit Link/Video-ID als Referenz. Nach erfolgreicher Abfrage ersetzt der Titel diese vorläufige Beschriftung; der Link bleibt zuordenbar. Bei einem Metadatenfehler bleibt die URL sichtbar, statt einen Titel zu erfinden oder die Zeile verschwinden zu lassen.
- Der laufende Eintrag zeigt seine aktuelle Phase am Titel: etwa „Audio laden · 35 %“, anschließend „Audio vorbereiten“, „Modell laden“ und „Transkribieren · 42 %“. Nur tatsächlich messbarer Fortschritt bekommt einen Prozentwert. Das Bild zeigt beispielhaft die Transkriptionsphase.

## Vorgesehene Verarbeitungsregeln

Striktes FIFO für Medienverarbeitung: immer nur ein Auftrag mit Audio-/Videodownload, Dekodierung und Transkription. Eine begrenzte Metadatenabfrage (höchstens eine gleichzeitig, mit Timeout) darf währenddessen Titel neu hinzugefügter Links ermitteln. Sie läuft außerhalb des UI-Threads und lädt keine Audiodatei herunter. Für wartende Einträge werden nur URL/Metadaten im Speicher gehalten; kein vorgezogener Audio-/Videodownload oder weiterer Modelllauf. Nach Ende eines Auftrags startet der nächste. Nach aktivem Abbruch erst weiterlaufen, wenn der alte Worker nachweislich beendet ist. Einen videobezogenen Fehler mit „Fehler“ kennzeichnen und den nächsten starten. Gemeinsame Voraussetzungen wie fehlender Modellzugang oder unzureichender RAM unterbrechen die Warteschlange, bis der Nutzer das Problem behebt; dieselbe Voraussetzung soll nicht an jedem wartenden Video erneut scheitern. Fehler sind im primären Bild nicht als zusätzliche fünfte Beispielzeile dargestellt.

Im ersten Umfang gilt die Liste für die geöffnete App-Sitzung. Eine Wiederherstellung nach App-Neustart ist eine separate Erweiterung. Laufzeitoptionen bleiben innerhalb einer aktiven Warteschlange fest, während Linkeingabe und Dateiauswahl verfügbar bleiben. Tokens erscheinen weder in der Liste noch in exportierbaren Auftragsdaten. Kopieren und Exportieren sind bei vorhandenem ausgewähltem Transkript aktiv; die Illustrationsfarben im Bild legen keinen deaktivierten Zustand fest.

In 0.2.0 wird das Modell innerhalb der Warteschlange wiederverwendet. Eine bestätigte Pause hält es fünf Minuten im RAM; „Speicher freigeben“ entlädt es sofort. Beim Fortsetzen wird es bei Bedarf neu geladen und ab dem letzten vollständigen Audioabschnitt weitergearbeitet. Ohne offene Aufträge wird es sofort freigegeben. Der historische Bild-Prompt unten stammt vor der Pause-Ergänzung. Es werden keine gemessenen Geschwindigkeitsgewinne behauptet.

## Sichtprüfung des Bildes

Gesamtes Fenster und alle Aktionsleisten sind sichtbar. Deutsche Beschriftungen entsprechen dem Entwurf. Arabischer Text ist verbunden und von rechts ausgerichtet. Der kleine Fortschrittsbalken ist illustrativ; die echte Oberfläche muss den gemessenen Wert exakt abbilden. ImageGen-Text und Icons sind ausschließlich visuelle Referenz und werden in der App durch echte Bedienelemente ersetzt.

## Finaler ImageGen-Prompt

```text
Use case: ui-mockup
Asset type: high-fidelity desktop application concept for Arabic Transcriber, one single front-facing screen.
Input image 1 is a STYLE AND EXISTING UI REFERENCE, not a photograph. Preserve its quiet, warm off-white background, white cards, deep muted teal accent, small Arabic letter mark, clear German typography, generous spacing and understated rounded borders. Extend this existing one-column design with a compact serial job queue. This is a CONCEPT image, not a claim of implemented behavior.

Composition: approximately 1440 x 1100 landscape screenshot, one complete app surface with all controls visible, no desktop wallpaper, no photographic device frame. Small caption above the product surface: "Entwurf · Warteschlange". Inside the app use no instructional prose or technical implementation labels. Do not create a sidebar or dashboard.

Header: retain the existing dark-teal Arabic-letter mark, "Arabic Transcriber" at left, quiet "Einstellungen" at far right. Header and content width match reference.

Input card: retain small tabs "Datei" and "YouTube"; YouTube is selected. Beneath tabs, one long text field with unobtrusive placeholder "Weiteren YouTube-Link eingeben" and a clear enabled dark teal primary button "Transkribieren" with small upward-right arrow. The input and action remain ready while the first job is running.

Immediately below input, add a white bordered card titled "Warteschlange"; compact muted summary at right "1 läuft · 2 warten". Four clean, generously legible horizontal rows, subtle separators, no thumbnails. Titles left, status right with a small independent action at far right.
Row 1 selected: very pale teal fill and a thin dark-teal left selection indicator. Title exactly "Interview · Alltag in Kairo". A small active teal status dot beside "Transkribieren · 42 %". A slim progress bar 42% across the active row, optional elapsed label "02:14". Far-right small outlined stop icon, not a pause button.
Row 2: neutral white, title exactly "Gespräch · Studium", muted status "Wartet · 1", far-right small x removal button.
Row 3: neutral white, title exactly "Vortrag · Geschichte", muted status "Wartet · 2", far-right small x removal button.
Row 4: neutral white, title exactly "Interview · Sprache", small check and status "Fertig". It has no waiting number and no stop icon.
Make the running status dot visually distinct from the selected-row highlight. No other task is running. No duplicate active or completed statuses.

Below queue, retain a large white transcript card. Card header left: "Transkript", with smaller subtitle "Interview · Alltag in Kairo" to explicitly associate it with the selected queue item. At right retain a small unchecked checkbox "Zeiten ≈". Show two or three large, readable right-aligned Arabic paragraphs with joined glyphs and proper RTL:
"مرحبًا بكم. نتحدث اليوم عن أهمية التعلم وتبادل المعرفة."
"يمكن للتقنية أن تساعدنا على الوصول إلى المعلومات بسهولة."
"الأهم هو أن نستخدم هذه الأدوات بطريقة واضحة ومفيدة."
No timestamps in body because time toggle is off. Keep sufficient breathing room around Arabic and avoid decorative text or a fake waveform.

Transcript footer: left quiet unchecked checkbox "Zeiten in Kopie / Export". Right aligned secondary controls "Alles kopieren", dropdown "Text · TXT", button "Exportieren ↓". All fit inside the card with comfortable spacing. Bottom understated label "Arabisch · lokal".

Visual quality: restrained contemporary desktop productivity software, one consistent 12–16 px corner system, thin warm gray borders, readable charcoal/deep teal text, subtle pale teal active selection, no large shadows, no gradients, no glow, no purple, no ornament. The queue should feel integrated, compact enough that transcript remains useful, and look buildable in the app's existing HTML/CSS. Every visible label must use the exact German spelling above. No new features such as pause/reorder/schedule, no ETA or total queue percentage, no invented controls, no help-text paragraphs, no browser address bar, no watermark.
```

