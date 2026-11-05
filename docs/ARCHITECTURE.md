# Runtime boundaries

`DesktopAPI` is the native UI boundary: dialogs, job start/cancel/snapshot,
clipboard and export. Trusted HTML/CSS/JS and the font are inlined into pywebview, with no HTTP
listener and no remote
content or transcript injection via HTML. JS builds transcript nodes with
`textContent`; model output is never executable markup. Tokens are entered in
a password field, passed only to the worker, never returned in snapshots.

`Job` owns a lightweight supervisor thread and a spawn worker process, with
revisioned locked snapshots. Model/native calls and their GIL are isolated from
the UI process. After a 0.5-second cancellation grace period, an unresponsive
worker and its descendants are terminated. Process exit releases model RAM.
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
Batch size is one, windows are bounded to 12 seconds, CPU threads are capped at
four with one inter-op thread, and weights load directly at target device/dtype.
A RAM/VRAM preflight estimates parameter memory plus 1.5 GiB working reserve.
Individual download/model calls still have cooperative cancellation limits; the
supervisor can terminate the isolated worker if those calls fail to return. Lack of access is a setup
prerequisite, not replaced with demo output.

`exports.py` renders the same timeline/text structure for copying and export.
UI visibility and export inclusion are presentation flags. UTF-8 remains
logical Unicode, DOCX uses bidi paragraphs plus embedded OFL fonts, PDF uses
HarfBuzz with bidi layout. Exports atomically replace their destination only
after successful generation. No inference is run for export or toggling.

The fast tests observe these public boundaries. Model inference and network
are the only faked external adapters. Real FFmpeg, document formats and native
bridge are exercised separately. See VERIFICATION.md for actual evidence.


Operational logging is configured only at app startup and rotates in the user's
local log directory. It records phases, timings, worker RSS and available memory,
without URLs, file paths, transcript, tokens or arbitrary exception messages.
`--worker-check` exercises frozen process spawning, IPC and forced cancellation.
The native entry point calls `multiprocessing.freeze_support()` before argument
parsing or GUI initialization, including Windows resource-tracker invocations.
