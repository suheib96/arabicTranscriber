# Warteschlange und Geschwindigkeit — Untersuchung, 2026-11-06

Historische Ausgangsuntersuchung vor der genehmigten Umsetzung. Die serielle Warteschlange und Modellwiederverwendung sind anschließend in 0.2.0 umgesetzt worden; CPU-/GPU-/Quantisierungsexperimente bleiben offen. Die folgenden Ausgangsbeobachtungen stammen aus der Konzeptphase. Kein App-Code geändert, keine neue Runtime, kein Build oder Release ausgelöst. Die vorhandene `uv run`-Sitzung wurde nicht beendet oder mit einem zweiten Modelllauf belastet.

## Verifizierter Ausgangsstand

- Lokales HEAD und live abgefragtes GitHub `main`: `ef25ef07ac21d1d9bd09ca9ba9ba93121a59e82f`.
- Gegenüber Release `v0.1.2` unterscheiden sich nur README und Verifikationsbericht. Die lokale Anwendung enthält keine zusätzliche unveröffentlichte Beschleunigung.
- Bereits veröffentlicht: isolierter Worker, maximal vier CPU-Intraop-Threads/ein Interop-Thread, Batch eins, höchstens zwölf Sekunden Audio pro Abschnitt, FFmpeg mit einem Thread, Speicherprüfung und Abbruch eines blockierten Workers.
- Nach jedem Auftrag wird der Worker beendet. Dadurch wird Modell-RAM freigegeben; bei einem weiteren Auftrag werden Modell und Prozessor erneut geladen. Der Downloadcache bleibt erhalten.
- Aktuelles Windows-Paket enthält `torch 2.15.0+cpu`. Apple MPS ist experimentell. Weder MPS-/CUDA-Ausführung dieses Checkpoints noch deren Geschwindigkeit ist belegt.
- Der letzte protokollierte YouTube-Auftrag erreichte „Audio vorbereiten“ nach 151,04 s und „Modell laden“ nach 151,65 s; er endete nach 161,15 s mit `ValueError` beim Modellladen. Der geloggte verfügbare RAM lag bei etwa 2 GB. Das Protokoll speichert keine Fehlermeldung, keine URL und keinen Inhalt. Es belegt keine abgeschlossene echte Modellinferenz oder deren Geschwindigkeit; erfolgreiche Diagnose-Fixtures sind keine Sprachbenchmarks.

## Priorisierte Vorschläge, noch nicht implementiert

1. **Modell während einer gefüllten Warteschlange wiederverwenden.** Ein einzelner isolierter Worker bearbeitet Aufträge nacheinander mit demselben geladenen Cohere-Modell. Beim Leerlauf wird er beendet und gibt den Speicher frei. Das spart potenziell Ladezeit zwischen Videos, beschleunigt aber nicht automatisch die Berechnung jedes Audioabschnitts. Ein erzwungener Abbruch beendet den alten Worker vollständig; erst danach darf ein neuer Worker für den nächsten Auftrag starten und das Modell neu laden.
2. **Zeiten sauber messen.** Separat Download, Dekodierung, Prozessor-/Modellladen, erster Text und eigentliche Inferenz erfassen. Dieselbe kurze lokale arabische Sprachaufnahme als Vergleich verwenden; kalten Start und direkt folgenden Auftrag vergleichen. Pro Test genau eine Einstellung ändern. Keine URLs, Tokens, Dateinamen oder Transkripte in Produktionslogs aufnehmen.
3. **CPU auf realer Zielhardware abstimmen.** Die jetzige Vier-Thread-Grenze ist eine bewusste Ressourcengrenze. Zwei, vier und gegebenenfalls sechs Threads vergleichen, einschließlich Laufzeit, Spitzenspeicher und Bedienbarkeit. Mehr Threads sind kein garantierter Gewinn. Keine parallelen Videoaufträge oder vorab laufenden Audio-/Videodownloads einführen. Nur die vom Nutzer ausdrücklich gewünschte, begrenzte Titelabfrage darf neben dem aktuellen Auftrag laufen.
4. **Beschleuniger und Präzision prüfen.** Auf Apple Silicon MPS mit genau diesem offiziellen Modell und geeigneter Präzision untersuchen; auf Windows einen CUDA-Build erst bei nachgewiesener geeigneter NVIDIA-Hardware anbieten. Lenovo-Zielgerät hat laut Nutzer 32 GB RAM, GPU ist unbekannt. Den funktionierenden CPU-Weg behalten. Keine Geschwindigkeitsfaktoren oder automatische Hardwareunterstützung versprechen.
5. **Quantisierung erst als späteres Experiment.** Kompaktere Rechenformate könnten Speicher und Laufzeit verbessern. Für genau dieses Cohere-Conformer-Modell müssen Operationen, CPU-/GPU-Unterstützung, Packaging und arabische Erkennungsqualität separat geprüft werden. Kein Modellwechsel und keine ungeprüfte quantisierte Ableitung als Standard.

Bekannte fehlende Grundvoraussetzungen sollten möglichst schon vor einem langen Audio-Download sichtbar sein. Dazu gehören Geräteunterstützung und ein verfügbarer RAM-Budgetcheck anhand des vorhandenen Checkpoints beziehungsweise einer ausdrücklich geschätzten Größe. Das spart vergebliche Wartezeit; es ist keine Beschleunigung der eigentlichen Spracherkennung.

## Sinnvolle öffentliche Prüfgrenzen für spätere Umsetzung

- Queue hinzufügen/validieren, FIFO und höchstens ein tatsächlich arbeitender Auftrag; weitere Eingaben während der Verarbeitung möglich.
- Echte YouTube-Titel vor Audio-Download, vorläufiger Titel-/URL-Zustand, Metadatenfehler/Timeout und Entfernen während einer Titelabfrage; eine verspätete Antwort darf keinen entfernten Eintrag wiederherstellen. Nur eine Metadatenabfrage gleichzeitig, keine zweite Medienpipeline.
- Ende, Einzelfehler, gemeinsame fehlende Voraussetzung, aktiver Abbruch und Entfernen eines wartenden Auftrags.
- Pro Auftrag erhaltene Segmente und Auswahl: automatischer Folgestart überschreibt kein gerade betrachtetes anderes Transkript; Kopieren/Export gehören zur Auswahl.
- Modellreuse bei zwei erfolgreichen Aufträgen sowie vollständige Freigabe nach leerer Queue; erzwungener Abbruch mit sauberem Prozessneustart.
- Echte Modellbenchmarks bleiben getrennt von schnellen Tests mit Fakes an der Inferenzgrenze.

## Quellen für mögliche Experimente

- Festes Originalmodell und Sprachumfang: https://huggingface.co/CohereLabs/cohere-transcribe-arabic-07-2026
- Cohere-ASR-Integration: https://huggingface.co/docs/transformers/model_doc/cohere_asr
- CPU-Threadsteuerung: https://docs.pytorch.org/docs/2.15/generated/torch.set_num_threads.html
- Apple-MPS-Grundlage, kein Nachweis für den konkreten Checkpoint: https://docs.pytorch.org/docs/2.15/notes/mps.html
- Quantisierungsmöglichkeiten, keine konkrete Cohere-Kompatibilitätszusage: https://huggingface.co/docs/transformers/quantization/torchao

Bestehende Start-/Build-Befehle bleiben unverändert: `uv run arabic-transcriber`, `uv run python scripts/build.py`, auf Windows `scripts/build_windows_setup.ps1`. Dieser Konzeptstand wurde nicht paketiert. Die im vorherigen Verifikationsbericht belegten Tests/Builds gelten für v0.1.2; für diese Konzeptdateien wurden keine Anwendungstests wiederholt. Neue Signier- oder Notarisierungszugänge wurden nicht eingerichtet.
