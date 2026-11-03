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
2. Eigenen Hugging-Face-**Lesetoken** in „Modell einrichten“ eintragen. Er bleibt
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
24-Sekunden-Fenstern mit bevorzugtem Schnitt in naher Stille verarbeitet und
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

Abbrechen erhält fertige Abschnitte. FFmpeg wird beendet, Downloads reagieren
an ihren Fortschrittspunkten und die Generierung an der nächsten Decoder-Stufe.
Ein laufender HF-Dateidownload, Modellaufbau oder Encoder-Aufruf kann erst nach
Rückkehr der jeweiligen Bibliotheksoperation anhalten. Währenddessen ist kein
zweiter Auftrag möglich. Vor dem Schließen wichtige Ergebnisse kopieren/exportieren;
es gibt noch keine automatische Sitzungswiederherstellung.

## Tests

```sh
uv run pytest -q
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run python -m arabic_transcriber.app --smoke --smoke-report build/native-smoke.json
uv run python scripts/check_smoke.py build/native-smoke.json
uv run python -m arabic_transcriber.app --self-check --smoke-report build/package-check.json
```

Die kleinen Verhaltenstests verwenden echtes FFmpeg und echte Exporte.
Nur große Inferenz und Live-Netzwerk werden durch externe Adapter ersetzt.
`--self-check` prüft Runtime-Imports, Node, FFmpeg und Exporte, **keine Inferenz**.
Der native Smoke öffnet das Fenster, prüft die echte Bridge und schließt es wieder.
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
und eine ZIP. Die ZIP benötigt vorhandenes WebView2. Für einen Setup-Assistenten
[Inno Setup 6](https://jrsoftware.org/isinfo.php) installieren, den offiziellen
[WebView2-Installer](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)
als `build/MicrosoftEdgeWebview2Setup.exe` speichern und seine Microsoft-Signatur
prüfen. Dann in PowerShell:

```powershell
& 'C:/Program Files (x86)/Inno Setup 6/ISCC.exe' scripts/windows-installer.iss
uv run python scripts/archive_package.py
```

CI führt diese Schritte auf Windows aus. Der Setup-Assistent installiert
WebView2 ohne separate Terminalbefehle; Internet ist für den Bootstrapper nötig.
.NET Framework 4.8+ wird auf Windows 11 vorausgesetzt. Windows ARM/32-bit und
Intel-Mac werden initial nicht als geprüfte Plattformen ausgeliefert.
Pakete enthalten weder Gewichte, Tokens, Benutzermedien noch Signierschlüssel.
Die FFmpeg-Lizenz-/Quellcodeanforderungen für öffentliche Weitergabe stehen in
[docs/THIRD_PARTY.md](docs/THIRD_PARTY.md).

## GitHub Builds und Releases aktivieren

Es ist **kein Remote eingerichtet und nichts veröffentlicht**. Ein eigenes leeres
GitHub-Repository anlegen und dessen tatsächliche URL einsetzen:

```sh
git branch -M main
git remote add origin https://github.com/OWNER/REPOSITORY.git
git push -u origin main
# Nach erfolgreichem CI und lokalem Test:
git tag v0.1.0
git push origin v0.1.0
```

`.github/workflows/build.yml` testet macOS/Windows, baut native Pakete und stellt
Actions-Artefakte bereit. Ein Push eines `v*`-Tags erzeugt automatisch einen
GitHub Release mit ZIPs, Windows-Setup und einzelnen SHA256-Dateien. Das ist
konfiguriert, aber ohne Remote noch nicht ausgeführt. Vor einer späteren Version
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
