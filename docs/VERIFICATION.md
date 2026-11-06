# Update 2026-11-06 — version 0.2.0 (local only)

- Approved ImageGen queue design implemented with real HTML/CSS controls. The
  subsequent approved scope adds global pause/resume and immediate memory
  release, with a five-minute pause retention period.
- Twenty-eight public behavior tests passed. Real spawned processes and FFmpeg
  exercise serial FIFO, one model instance across queued tasks, separate selected
  transcripts, progressive commits, cancellation, model-prerequisite retry,
  metadata fallback/removal races, pause/resume, reload, final-chunk completion,
  rapid repeated pause transitions and processing-time accounting after reload.
- The automatic timeout was exercised with a short configured test interval,
  with no UI/snapshot polls driving it. Default 300-second retention is checked
  separately. A forced release/cancel interrupts a native PyDLL call that holds
  the worker GIL; the successor verifies the old process has exited.
- Source worker check passed FIFO, paused model retention, immediate release,
  replacement worker, exact resumed audio offsets, selection and cancellation.
  Source runtime check passed actual Cohere preprocessing, Node, FFmpeg decode,
  model imports and TXT/DOCX/PDF export. These checks explicitly report
  `real_model_inference: false` and are never a product transcription fallback.
- Actual HTTPS YouTube oEmbed returned a real public title without media
  download. Requests use a bounded response, socket timeout and certifi CA bundle.
  One metadata thread is independent of the single heavy media pipeline.
- Browser checks passed actual shipped document interactions: adding while
  running, title escaping, selecting separate transcripts, pause countdown,
  release/resume controls, stable Arabic text/selection, timestamp toggles,
  760-pixel window overflow and non-overlapping slow snapshot calls. Idle,
  running, paused, released and compact-window screenshots are in ignored scratch.
- Ruff checks/formatting and `git diff --check` passed. No new dependencies or
  alternative ASR model were introduced; app/package version is 0.2.0.

Native macOS arm64 build `uv run python scripts/build.py` completed. The
**frozen 0.2.0 executable** passed worker FIFO/pause/release/reload/resume and
forced cancellation (0.55 s), real runtime/preprocessing/media/export self-check,
and WKWebView window/bridge/font smoke. Hardware MPS availability was true in the
native runtime; MPS inference itself remains unverified. Bundle version 0.2.0,
post-smoke ad-hoc signature and independently read ZIP SHA256 passed. Archive
inspection found no model weights, job media, scratch or signing key files.
`dist/Arabic Transcriber.app` and `dist/release/ArabicTranscriber-macOS-arm64.zip`
are the verified local outputs.
No push, tag or new GitHub Release is part of this extension. The public download
remains v0.1.2 until a separately authorized publication.

Windows 0.2.0 execution and full original-checkpoint inference/quality/speed are
not verified by these Mac checks. CPU Float32/RAM preflight remains unchanged;
model reuse avoids repeated loads but no measured inference speedup is claimed.
Developer-ID/notarization and Windows signing credentials remain unavailable.

# Update 2026-11-05 — version 0.1.2

- Reproduced the exact native picker failure with pywebview's real filter
  parser at the public `DesktopAPI.choose_file` boundary. The slash in the
  description `Audio / Video` was invalid. `Audio und Video` passes validation.
- Built the actual 0.1.2 macOS bundle, opened its native Open panel and selected
  a generated WAV file. The filename appeared in the app and Transcribe became
  available. No inference was started with this silent picker fixture. Further
  interactive cancellation testing stopped when the user resumed app use.
- Frontend regression verified that polling preserves a local dialog error and
  successful selection clears it. Existing incremental transcript and polling
  checks remain green. Fourteen pytest checks and Ruff lint/format passed.
- Bundle version 0.1.2, ad-hoc signature and release ZIP SHA256 verified.
- During subsequent user interaction the real app reported insufficient memory:
  approximately 9.9 GB required and 2.7 GB available. Full model inference remains
  unverified. This is a current observation, not proof of yesterday's hang.
- User supplied the empty public target repository
  `https://github.com/suheib96/arabicTranscriber`. CI uses current explicit
  macOS 15 arm64 and Windows Server 2025 x64 runners. Initial main CI
  [42009368433](https://github.com/suheib96/arabicTranscriber/actions/runs/42009368433)
  passed both OS test/UI suites, both frozen worker/runtime/window checks,
  archive uploads and the Windows installer build. Windows uses PyTorch
  `2.15.0+cpu`; CUDA is not included in this installer. Worker cancellation was
  0.73 s on Windows and 0.76 s on macOS. These checks use no model weights.
  The first Windows UI check exposed cp1252 stdout encoding; explicit UTF-8
  transport passed both a local cp1252 regression and the actual Windows runner.
  Tag `v0.1.2` independently rebuilt and passed all tests/packages in
  [release run 42011007646](https://github.com/suheib96/arabicTranscriber/actions/runs/42011007646).
  [Release 0.1.2](https://github.com/suheib96/arabicTranscriber/releases/tag/v0.1.2)
  is published as a prerelease with Mac ZIP, Windows portable ZIP, Windows Setup
  EXE and their three SHA256 files. All three package hashes match GitHub's
  independently calculated upload digests. Frozen runtime/worker reports from
  both final release builds report success and explicitly no real inference.
  Windows native dialog acceptance, installer execution on user hardware and
  full model inference remain unverified.

# Update 2026-11-05 — version 0.1.1

The exact reported two-minute YouTube hang has not been reproduced: URL, device
and last stage were requested but not supplied during this run. The following
independent failure modes were reproduced and corrected, without claiming that
they establish the cause of that particular incident.

- An uncooperative model load left `Job.cancel()` stuck and prevented restart.
  Processing now runs in a spawned process. A native PyDLL call holding its GIL
  is forcibly stopped after a brief grace period; existing segments remain.
  Source worker check passed in 0.74 s and **frozen app worker check in 0.73 s**,
  including IPC, successive segments and restart. No inference fixture is used
  as a fallback in product operation.
- Progress-only renders recreated transcript DOM and cleared selection. The
  browser regression now verifies stable text nodes and preserved selection.
  Slow 650 ms snapshot responses also verify that polling never overlaps.
- UI status strings are short, with measured percentage only where available;
  no “without percentage” / “Batch 1” explanations. Advanced options are
  collapsed and platform-specific GPU choices are hidden where inappropriate.
  Elapsed time keeps advancing while model progress is not measurable.
- A generated two-minute H264/AAC video was encoded/decoded with real FFmpeg;
  audio windows never exceed 192,000 samples (12 seconds at 16 kHz), are
  contiguous, and preserve the complete timeline. This is not live YouTube or
  a speech-quality/inference-speed benchmark.
- Model processing is batch one, with at most four CPU intra-op threads and one
  inter-op thread, direct target dtype/device loading and RAM/VRAM preflight.
  Worker exit releases model memory after every job (disk cache retained).
- The user's original checkpoint now exists locally (4.13 GB), and its actual
  offline processor loaded. Available RAM during that probe was 2.71 GB versus
  an estimated 9.87 GB CPU budget. Full weights/inference were not loaded under
  this memory pressure. This observation is not proof of yesterday's state.
- Thirteen pytest checks, Ruff lint/format, frontend rendering/interaction,
  source and frozen worker checks, frozen runtime/preprocessing/export check,
  native window/bridge/font smoke, bundle version, ZIP checksum and ad-hoc
  signature all passed. No weights, media, signing secrets or scratch in ZIP.
- Windows installer build helper and signing scripts parse in PowerShell.
  Windows/macOS CI now also checks frozen spawning/cancellation. Actual Windows
  build/installation, CUDA/MPS inference and credential-backed signing remain
  unverified on this Mac. No remote CI/release run or public publication occurred.
- Rotating local logs retain stages/timing/memory/error types only, with no
  input URLs, filenames, transcripts or credentials. No throwaway debug logging
  remains in production; controlled probes are marked in ignored scratch.

Reproduce locally:

```sh
uv run pytest -q
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run python -m arabic_transcriber.app --worker-check --smoke-report build/worker-check.json
uv run python scripts/build.py
"dist/Arabic Transcriber.app/Contents/MacOS/Arabic Transcriber" --worker-check --smoke-report build/worker-check.json
"dist/Arabic Transcriber.app/Contents/MacOS/Arabic Transcriber" --self-check --smoke-report build/package-check.json
"dist/Arabic Transcriber.app/Contents/MacOS/Arabic Transcriber" --smoke --smoke-report build/native-smoke.json
uv run python scripts/check_smoke.py build/native-smoke.json
```

Windows setup: on Windows 11 x64 with uv and Inno Setup 6 installed, run
`scripts/build_windows_setup.ps1`. This helper's syntax is checked here; a
Windows execution result is not claimed. See README for runtime prerequisites.

The historical initial verification below describes 2026-11-03, before the model
cache and the process-isolation changes above.

---

# Verification on 2026-11-03

This is local evidence, not a claim of a published GitHub release.

## Passed

- Python 3.12.12 development environment on macOS 27.0 arm64, 16 GB physical RAM.
  Locked PyTorch/NumPy wheels require macOS 14+, reflected in bundle metadata.
- Ten focused pytest behavior checks: desktop initial state and cancelled
  dialogs, bundled inline document assets, clipboard/save timestamp choice, local jobs with actual FFmpeg,
  progressive snapshots, cancel preserving results and restart, network-adapter
  success/error, skipped-silence offsets, model prerequisite errors,
  playlist/channel rejection, real TXT/DOCX/PDF export and actual Cohere feature extraction.
- Ruff lint and formatting checks; `git diff --check`.
- `CohereAsrForConditionalGeneration` and processor import from Transformers
  5.22.1, PyTorch 2.15.0. Fixed official model ID and language `ar` in runtime.
- Explicit offline model setup probe produced the actionable missing-cache
  message. No HF token and no model cache were present; no weights downloaded.
- Real `CohereAsrFeatureExtractor` ran on a deterministic waveform without
  weights. This caught the required librosa dependency; librosa 0.11.0 and its
  scientific runtime are now locked and included in the package self-check.
- Source runtime self-check: actual FFmpeg decode, Node v24.13.0, yt-dlp
  2026.10.26, ejs, Cohere runtime imports and all three real exports.
- Native UI loads HTML/CSS/JS and its Arabic font directly into WebView without
  a loopback HTTP server. A repeat startup failure on the earlier URL-based
  path led to this change; the previous resource root also excluded the font.
  The native smoke now checks actual font readiness and exits on timeout.
- Native pywebview window launched and real JS→Python snapshot bridge completed
  its smoke report: title, buttons, RTL attribute and no horizontal overflow.
- Shipped HTML tested in headless Chrome: three real DOM RTL paragraphs,
  approximate times, timestamp toggle preserving text, disabled Transcribe and
  active Cancel, settings. Idle/running/settings screenshots visually inspected.
  Test transcript was explicitly labelled TESTFIXTUR; it is not product/demo output.
- Eighteen known Arabic/mixed Latin segments rendered as four-page DOCX and
  four-page PDF fixtures. Every page inspected: joined Arabic, Latin names,
  numbers, punctuation, line wrapping, margins and page transitions readable.
  DOCX rendered through the document skill's LibreOffice renderer; PDF through
  Poppler. Fixed Latin font fallback and RTL paragraph alignment during review.
  Both OFL fonts are embedded. Export timestamp labels use `ca.` consistently.
- Full `uv run python scripts/build.py` completed; 385.6 MiB ZIP and SHA256
  generated, checksum independently verified. ZIP inspected for weights, input
  media and signing secrets: none included.
- Native macOS arm64 PyInstaller bundle built with Python, WKWebView bridge,
  fonts, model runtime, FFmpeg and Node. The separate package self-check passed
  **inside the frozen executable**, including real decode, actual Cohere feature extraction and exporters.
- Packaged native window/bridge smoke passed independently of the source venv.
- `codesign --verify --deep --strict` passed for the final **ad-hoc** signature.
  Initial signing failed under disk pressure on the 402 MB PyTorch library;
  removing this task's own build intermediates and signing with adequate
  temporary space resolved it. No Developer ID or notarization is claimed.
- Bundled runtime detects MPS as available outside the sandbox. That is hardware
  detection only, **not** a verified Cohere/MPS inference result.
- GitHub Actions YAML parsed locally. Jobs: test, native package, tag release.
  Microsoft WebView2 bootstrap URL resolved to Microsoft's delivery host.
- `.scratch/`, model weights, media, tokens and signing credentials remain
  ignored/untracked. No Git remote is configured.

## Reproducible checks

```sh
uv run pytest -q
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run python scripts/prepare_tools.py
uv run python -m arabic_transcriber.app --self-check --smoke-report build/source-check.json
uv run python -m arabic_transcriber.app --smoke --smoke-report build/native-smoke.json
uv run python scripts/check_smoke.py build/native-smoke.json
uv run python scripts/build.py
"dist/Arabic Transcriber.app/Contents/MacOS/Arabic Transcriber" --self-check --smoke-report build/package-check.json
"dist/Arabic Transcriber.app/Contents/MacOS/Arabic Transcriber" --smoke --smoke-report build/package-smoke.json
uv run python scripts/check_smoke.py build/package-smoke.json
```

Build uses PyInstaller without a redundant macOS COLLECT directory. It needs
several GB free for binary copies, signing and ZIP. Do not attempt the 4.13 GB
model download while this machine's remaining disk space is insufficient.
Scratch evidence: `.scratch/arabic-transcriber/` contains native JSON reports,
HTML screenshots, model/cache probe results and export page renders.

## External prerequisites and unverified checks

- **Real Cohere inference, download/resume and later offline inference** require
  the user's accepted model gate/read token, disk space and sufficient RAM.
  Performance, full memory footprint, quality at boundaries and CPU/CUDA/MPS
  execution have not been measured with the real weights. No alternate ASR used.
- **Live YouTube** has no supplied test URL and was not exercised against the
  network. The deterministic adapter flow and bundled Node/ejs are checked;
  current YouTube availability remains best effort.
- **Windows 11 x64 build, WebView2 setup, native dialog behavior and installer**
  require the configured Windows CI or a Windows test machine. A Mac build does
  not prove them. The Windows workflow has not run without a target repository.
- **Developer ID, notarization, Authenticode and reputation** require the user's
  paid/provider credentials. Hooks are prepared but no real certificates exist.
- **GitHub builds/releases** are configured locally only. Supply an actual remote,
  push main and inspect CI before pushing a version tag. Nothing was published.
- Computer Use native visual inspection was unavailable because its service
  timed out. Native launch/bridge and actual frontend rendering/interaction
  were checked through the app smoke and browser software test instead.
- Native file/save dialogs were wired to pywebview and tested at the desktop
  boundary with cancelled/selected dialog results; interactive OS dialog checks
  and clipboard use are still part of the user's manual acceptance test.
