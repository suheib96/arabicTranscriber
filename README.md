# Arabic Transcriber

Minimalistische Desktop-App für lokale arabische Transkription mit
**CohereLabs/cohere-transcribe-arabic-07-2026**. Python und pywebview,
Datei-/YouTube-Import, wachsendes RTL-Transkript, Fortschritt, Abbrechen,
Alles kopieren sowie TXT, Word DOCX und PDF.

## Lokal starten

Voraussetzungen für Entwicklung: macOS 14+ (Apple Silicon) oder Windows 11 x64,
[uv](https://docs.astral.sh/uv/getting-started/installation/), Internet für Setup.
Die Pakete brauchen keine eigene Python-Installation. Windows benötigt die
Microsoft WebView2 Runtime; der Setup-Assistent installiert sie bei Bedarf.

```sh
uv sync --frozen --extra dev --python 3.12
uv run python scripts/prepare_tools.py
uv run arabic-transcriber
```

`prepare_tools.py` lädt Node 24.13.0 mit Hersteller-SHA256 und übernimmt FFmpeg
aus dem gepinnten Python-Wheel. Der App-Start funktioniert auch direkt mit
`.venv/bin/python -m arabic_transcriber.app` (Windows: `.venv\Scripts\python.exe`).
Für lokale Dateien reicht der gebündelte FFmpeg; YouTube verwendet zusätzlich
Node und das gepinnte yt-dlp-ejs. HTML, CSS, JavaScript und Schrift werden direkt in die native WebView geladen;
es wird kein lokaler HTTP-Server benötigt.

## Modell einmalig einrichten

1. Auf der [offiziellen Modellseite](https://huggingface.co/CohereLabs/cohere-transcribe-arabic-07-2026)
   anmelden und die Zugangsbedingungen mit dem eigenen Account akzeptieren.
2. Eigenen Hugging-Face-**Lesetoken** in „Einstellungen“ eintragen. Er bleibt
   nur im Speicher des Auftrags und wird danach entfernt. Alternativ den Token
   lokal mit `hf auth login` hinterlegen oder `HF_TOKEN` als Umgebungsvariable
   setzen. Niemals Token in Git, Chat oder geteilte Pakete kopieren.
3. Datei auswählen und transkribieren. Der erste Auftrag lädt ca. **4,13 GB
   Gewichte** in den normalen Hugging-Face-Cache. Das ist **nicht** der gesamte
   RAM-Bedarf. Float32 auf CPU benötigt bereits etwa 8 GB nur für Parameter;
   Aktivierungen und Laufzeit brauchen zusätzlichen Speicher. Auf diesem
   16-GB-Mac wurde keine echte Inferenz verifiziert.
4. Danach „Offline · nur Cache verwenden“ für lokale Dateien aktivieren.
   Ein vollständiger Cache wird ohne erneuten Download verwendet. Standard:
   `~/.cache/huggingface/hub` bzw. `%USERPROFILE%\.cache\huggingface\hub`;
   `HF_HOME` kann den Speicherort ändern. Der Cache gehört dem Empfänger,
   nicht zum verteilten App-Bundle.

CPU/Float32 ist der konservative Standard. NVIDIA CUDA/Float16 kann bei einer
passenden PyTorch-Installation ausgewählt werden; CUDA-Pakete/Hardware sind
separat zu prüfen. Apple MPS/Float32 ist **experimentell** und muss mit genau
diesem Modell getestet werden. Es gibt keinen Ersatzmotor und keine
Cloud-Transkription. Gated Zugang, Speicher und Hardware sind reale Voraussetzungen.

## Bedienung und Grenzen

Datei wählen oder einen HTTPS-Link zu einem einzelnen YouTube-Video einfügen.
YouTube lädt bevorzugt Audio und verwendet denselben lokalen Modellpfad.
Private, geografisch gesperrte, geschützte oder von YouTube blockierte Videos
können scheitern. Livestreams und Playlists werden nicht verarbeitet.
Vorbereitung, YouTube-Download, Modellladen und Transkription haben getrennte
Statusanzeigen. Nur messbare Stadien zeigen einen Prozentsatz.

Audio wird auf temporärem Datenträger in Mono/16 kHz dekodiert, in höchstens
12-Sekunden-Fenstern mit bevorzugtem Schnitt in naher Stille verarbeitet und
nicht vollständig in RAM geladen. Erkannte Abschnitte erscheinen sofort.
Sehr stille Fenster werden konservativ übersprungen; ursprüngliche Offsets
bleiben erhalten. Keine Sprechererkennung und keine garantierte Echtzeit.
Schnittgrenzen können die Erkennung beeinflussen; echte Wortgrenzen sind ohne
Alignment nicht garantiert. Die Qualität an Grenzen ist mit realen Aufnahmen zu prüfen.
Temporäre Medien werden nach Erfolg, Fehler oder Abbruch gelöscht.
Für lange Medien ausreichend temporären Plattenplatz einplanen (PCM ca. 115 MB/Stunde).

„Zeiten“ zeigt **ungefähre Audioabschnittszeiten**, keine nativen Cohere-Wortzeiten.
„Zeiten in Kopie / Export“ steuert unabhängig davon alle Ausgabeformate.
Umschalten verändert weder Text noch Modelllauf. DOCX ist das aktuelle
Word-Format; es werden keine DOCX-Dateien als `.doc` ausgegeben. Die App bettet
frei lizenzierte Schriften in DOCX und PDF ein. PDF verwendet HarfBuzz und
bidirektionales Layout, TXT ist UTF-8.

Abbrechen erhält fertige Abschnitte. Die Verarbeitung läuft in einem eigenen
Prozess. Reagiert eine Bibliothek nicht auf Abbrechen, beendet die App diesen
Prozess nach einer kurzen Schonfrist mitsamt seinen Medien-Hilfsprozessen.
Nach jedem Auftrag wird der Modellprozess geschlossen und sein RAM freigegeben;
der Downloadcache auf der Festplatte bleibt erhalten. Das erneute Laden bei einem
weiteren Auftrag ist ein bewusster Kompromiss zugunsten freier Systemressourcen.

CPU-Verarbeitung nutzt höchstens vier Rechenthreads und einen Inter-op-Thread.
Vor dem Modellladen wird der verfügbare RAM bzw. CUDA-Grafikspeicher geprüft.
Der Float32-Pfad veranschlagt bei diesem Checkpoint rund 9,9 GB freien RAM
(Parameter plus geschätzter Arbeitsreserve), CUDA/Float16 rund 5,7 GB freien
Grafikspeicher. Das sind vorsichtige Schätzungen, keine garantierten Spitzenwerte.
16 GB Gesamtspeicher können bei geöffneten anderen Apps zu knapp sein; auf einem
Windows-PC mit 32 GB RAM bleibt mehr Reserve. Unified Memory ist keine
Voraussetzung: CPU arbeitet auch unter Windows mit normalem RAM. CUDA nutzt die
separate NVIDIA-GPU und deren VRAM, sofern das gebaute PyTorch diese unterstützt.

Vor dem Schließen wichtige Ergebnisse kopieren/exportieren; es gibt noch keine
automatische Sitzungswiederherstellung. Lokale rotierende Diagnoselogs enthalten
nur Phasen, Laufzeiten, Prozessspeicher und Fehlerklassen, keine URLs, Dateinamen,
Tokens oder Transkripte. macOS: `~/Library/Logs/ArabicTranscriber/runtime.log`;
Windows: `%LOCALAPPDATA%\ArabicTranscriber\logs\runtime.log`.


## Tests

```sh
uv run pytest -q
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run python -m arabic_transcriber.app --smoke --smoke-report build/native-smoke.json
uv run python scripts/check_smoke.py build/native-smoke.json
uv run python -m arabic_transcriber.app --self-check --smoke-report build/package-check.json
uv run python -m arabic_transcriber.app --worker-check --smoke-report build/worker-check.json
```

Die kleinen Verhaltenstests verwenden echtes FFmpeg und echte Exporte.
Nur große Inferenz und Live-Netzwerk werden durch externe Adapter ersetzt.
`--self-check` prüft Runtime-Imports, Node, FFmpeg und Exporte, **keine Inferenz**.
`--worker-check` prüft echte Prozessstarts, fortlaufende Segmente, Abbruch eines
nativ blockierten Workers und Neustart ohne Modellgewichte. Der native Smoke
öffnet das Fenster, prüft die echte Bridge und schließt es wieder.
Für den zusätzlichen HTML-Bedientest (Node/Playwright nur Entwicklung):

```sh
npm install --no-save --package-lock=false playwright@1.58.2
npx playwright install chromium
node scripts/ui_smoke.cjs
```

Optionaler **echter** Modelltest nach freigeschaltetem Zugang:

```sh
uv run python scripts/model_smoke.py /absoluter/pfad/arabisch.wav --device cpu
# Später ohne Netzwerk:
uv run python scripts/model_smoke.py /absoluter/pfad/arabisch.wav --device cpu --offline
```

Ein manueller Live-YouTube-Test erfolgt über die App mit einem eigenen erlaubten
öffentlichen Videolink. Dieser Test lädt echte Medien und Modellgewichte;
CI tut das nicht. Bisherige Belege und nicht verifizierte Punkte stehen in
[docs/VERIFICATION.md](docs/VERIFICATION.md).

## Native Pakete bauen

Immer **auf dem Zielsystem und mit passender Architektur** bauen, mindestens
mehrere GB freien Plattenplatz vorhalten. Ein Mac-Build beweist keinen Windows-Build.

```sh
uv sync --frozen --extra dev --python 3.12
uv run python scripts/build.py
```

macOS: `dist/Arabic Transcriber.app`, ZIP und SHA256 in `dist/release/`.
Das App-Bundle kann in „Programme“ verschoben werden. Lokaler Pakettest:

```sh
"dist/Arabic Transcriber.app/Contents/MacOS/Arabic Transcriber" --self-check --smoke-report build/package-check.json
"dist/Arabic Transcriber.app/Contents/MacOS/Arabic Transcriber" --smoke --smoke-report build/package-smoke.json
uv run python scripts/check_smoke.py build/package-smoke.json
```

Windows 11 x64: derselbe Build-Befehl erzeugt einen vollständigen App-Ordner
mit `Arabic Transcriber.exe` und eine ZIP. Die EXE muss mit dem gesamten Ordner
verteilt werden; sie ist keine einzelne selbstentpackende Datei. Ein Setup ist
für Empfänger einfacher. Auf dem Windows-Buildrechner einmalig uv und
[Inno Setup 6](https://jrsoftware.org/isinfo.php) installieren, den Quellcode
kopieren/auschecken und im Projektordner in PowerShell ausführen:

```powershell
.\scripts\build_windows_setup.ps1
```

Der Helfer installiert die Entwicklungsabhängigkeiten, baut die native App,
lädt den offiziellen Microsoft-WebView2-Bootstrapper, prüft dessen Signatur und
erstellt `dist/release/ArabicTranscriber-Windows-x64-Setup.exe` samt Prüfsumme.
Optional konfigurierte Signier-Secrets werden berücksichtigt. Diese Schritte
benötigen keinen Mac-spezifischen Codewechsel und keinen Unified Memory.
Empfänger starten nur die Setup-EXE und danach die App; Python oder Terminal
sind bei ihnen nicht erforderlich. Der Hugging-Face-Modellzugang und der
Modellcache müssen auf jedem Zielrechner einmal eingerichtet werden.

CI führt diese Schritte auf Windows aus. Der Setup-Assistent installiert
WebView2 ohne separate Terminalbefehle; Internet ist für den Bootstrapper nötig.
.NET Framework 4.8+ wird auf Windows 11 vorausgesetzt. Windows ARM/32-bit und
Intel-Mac werden initial nicht als geprüfte Plattformen ausgeliefert.
Pakete enthalten weder Gewichte, Tokens, Benutzermedien noch Signierschlüssel.
Die FFmpeg-Lizenz-/Quellcodeanforderungen für öffentliche Weitergabe stehen in
[docs/THIRD_PARTY.md](docs/THIRD_PARTY.md).

## GitHub Builds und Releases aktivieren

Ziel-Repository: [suheib96/arabicTranscriber](https://github.com/suheib96/arabicTranscriber).
Der erste Build wird auf `main` geprüft; erst danach wird der Versionstag gepusht:

```sh
git branch -M main
git remote add origin https://github.com/suheib96/arabicTranscriber.git
git push -u origin main
# Nach erfolgreichem CI und lokalem Test:
git tag v0.1.2
git push origin v0.1.2
```

`.github/workflows/build.yml` testet auf macOS 15 (Apple Silicon) und Windows Server 2025 x64, baut native Pakete und stellt
Actions-Artefakte bereit. Ein Push eines `v*`-Tags erzeugt automatisch einen
GitHub Release mit ZIPs, Windows-Setup und einzelnen SHA256-Dateien. Das ist
eingerichtet. Aktuelle Ergebnisse stehen unter [Actions](https://github.com/suheib96/arabicTranscriber/actions),
Downloads unter [Releases](https://github.com/suheib96/arabicTranscriber/releases). Vor einer späteren Version
`pyproject.toml`, `__init__.py`, Bundle-/Installer-Version gemeinsam erhöhen und
`uv lock` aktualisieren. Dependencies für yt-dlp/Node regelmäßig bewusst
aktualisieren, testen und neu paketieren; kein unkontrolliertes Selbstupdate.
PR-Builds erhalten keine Signier-Secrets; nur der Release-Job erhält `contents: write`.

## Optional signieren

Ohne Secrets bleiben Builds unsigned bzw. auf macOS ad-hoc signiert. Das ist
kein Developer-ID-Vertrauensnachweis. Keine Sicherheitsmechanismen abschalten.
Signierung/Notarisierung kann Installationshürden senken, garantiert aber keine
vollständig warnungsfreie Installation oder SmartScreen-Reputation.

macOS benötigt eine eigene Apple-Developer-Mitgliedschaft ([99 USD pro Jahr, regionale Preise können abweichen](https://developer.apple.com/programs/enroll/)) und ein **Developer ID
Application**-Zertifikat mit privatem Schlüssel. Als GitHub Secrets setzen:
`APPLE_CERTIFICATE_P12_BASE64`, `APPLE_CERTIFICATE_PASSWORD`, `APPLE_SIGN_IDENTITY`
(vollständiger Keychain-Identitätsname). Für Notarisierung zusätzlich `APPLE_ID`,
`APPLE_TEAM_ID`, `APPLE_APP_PASSWORD` (anwendungsspezifisches Passwort).
CI importiert das Zertifikat in eine temporäre Keychain, PyInstaller signiert
verschachtelten Code mit Hardened Runtime, `notarytool` lädt hoch, danach
`stapler` und `spctl`. Die Keychain wird zum Schluss entfernt.
Lokal kann eine schon importierte Identität über `APPLE_SIGN_IDENTITY` genutzt
werden; `scripts/sign_macos.py` läuft im Build automatisch. Ohne Notary-Zugang
bleibt das Ergebnis nur signiert, nicht notarisiert.

Windows: optional `WINDOWS_CERTIFICATE_PFX_BASE64` und
`WINDOWS_CERTIFICATE_PASSWORD` für ein rechtmäßig nutzbares exportierbares
Authenticode-Zertifikat. `scripts/sign_windows.ps1` nutzt Windows-SDK SignTool,
SHA256 und RFC3161-Zeitstempel für App und Installer. Viele heutige öffentliche
Zertifikate verlangen Hardware oder einen Cloud-Signierdienst; dann diesen
anbieterabhängigen Hook durch den eigenen HSM-/Artifact-Signing-Aufruf ersetzen.
Der vorbereitete PFX-Weg behauptet keine Verfügbarkeit eines solchen Zertifikats.
Kosten für öffentliche Windows-Zertifikate bzw. Cloud-Signierung hängen vom Anbieter, Identitätsprüfung und Hardware-/Dienstmodell ab; vor Einrichtung ein aktuelles Angebot prüfen. Es wurden keine Zertifikate gekauft und keine Mitgliedschaften eingerichtet.

Offizielle Grundlagen: [Apple Developer ID / Hardened Runtime](https://help.apple.com/xcode/mac/current/en.lproj/dev033e997ca.html),
[Apple Notarisierungsablauf](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow),
[Microsoft Signieroptionen](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options),
[SmartScreen-Reputation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation),
[WebView2-Verteilung](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution).
