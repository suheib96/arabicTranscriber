# Runtime boundaries

`DesktopAPI` is the native UI boundary: dialogs, job start/cancel/snapshot,
clipboard and export. Trusted HTML/CSS/JS and the font are inlined into pywebview, with no HTTP
listener and no remote
content or transcript injection via HTML. JS builds transcript nodes with
`textContent`; model output is never executable markup. Tokens are entered in
a password field, passed only to the worker, never returned in snapshots.

`Job` owns a single background thread and revisioned, locked snapshots.
Completed segments are immutable timeline values (`start`, `end`, `text`).
A new job clears the prior result only after valid input and after the previous
worker has stopped. The frontend polls snapshots every 400 ms; percentages
refer to download bytes or processed decoded duration, depending on stage.
No fabricated model-download percentage or token streaming is exposed.

`media.py` owns the external media/network boundary. FFmpeg runs without a
shell, with argument arrays and disk-redirected streams. PCM is temporary and
read in bounded contiguous windows. Silent windows still advance original
media time. Quiet boundary cuts do not overlap or concatenate distant speech.
The downloader accepts a bounded YouTube host allowlist and no playlists/live
streams; yt-dlp handles its network protocols. Input URLs are structured values.

`CohereRecognizer` is the sole ASR boundary. Fixed official model ID and `ar`,
local-first HF cache, no cloud fallback or alternate ASR. A conservative
float32 CPU option, float16 CUDA and experimental float32 MPS are explicit.
One model instance is retained per process and batch size is one. Download,
model loading and encoder kernels are not preemptible; cancellation is observed
before/after them and via decoder stopping criteria. Lack of access is a setup
prerequisite, not replaced with demo output.

`exports.py` renders the same timeline/text structure for copying and export.
UI visibility and export inclusion are presentation flags. UTF-8 remains
logical Unicode, DOCX uses bidi paragraphs plus embedded OFL fonts, PDF uses
HarfBuzz with bidi layout. Exports atomically replace their destination only
after successful generation. No inference is run for export or toggling.

The fast tests observe these public boundaries. Model inference and network
are the only faked external adapters. Real FFmpeg, document formats and native
bridge are exercised separately. See VERIFICATION.md for actual evidence.
