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
