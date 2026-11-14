# Runtime boundaries

`DesktopAPI` is the native UI boundary: dialogs, job start/cancel/snapshot,
clipboard and export. Trusted HTML/CSS/JS and the font are inlined into pywebview, with no HTTP
listener and no remote
content or transcript injection via HTML. JS builds transcript nodes with
`textContent`; model output is never executable markup. Tokens are entered in
a password field, passed only to the worker, never returned in snapshots.

`Job` owns a locked FIFO and selection, a lightweight supervisor, and at most
one spawned model worker. `worker.serve` keeps the sole recognizer alive across
successive media tasks. Snapshots contain all row summaries and only the
selected transcript. Selection never changes automatically when the queue
advances. Tokens are private session options, absent from snapshots and logs.

Pause is cooperative at safe media/segment boundaries. A versioned shared
signal prevents rapid resume/pause transitions from losing acknowledgements;
it has no process lock that a terminated worker could poison. The backend
supervisor releases the worker after 300 seconds of confirmed pause, or of an
unacknowledged request when a native call is stuck. Immediate release forces
shutdown. Committed text and the exact decoded-audio cursor arrive atomically
in one IPC message. The parent retains each paused task's temporary directory,
completed decode flag and downloaded source, so a replacement worker can
resume without duplicate committed segments or treating a partial decode as
complete. Finishing the final chunk completes/releases an empty queue even if
pause was requested. Runtime option changes on resume replace the worker.

Cancellation has a 0.5-second grace period, then stops the worker and its
FFmpeg/Node descendants before any successor. A per-video error advances FIFO;
model-load prerequisites block/pause the queue and retain its work for retry.
Empty queue and app close release the process and temporary work. Waiting media
are never downloaded in advance. A separate single metadata thread resolves
YouTube titles via bounded HTTPS oEmbed requests and certifi's CA bundle; late
responses cannot restore removed rows. The frontend polls every 400 ms without
overlap and uses keyed queue rows and incremental transcript nodes.
Percentages represent download bytes or committed decoded duration; unknown
stages have no fabricated percentage or completion estimate.

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
`--worker-check` exercises frozen spawning, FIFO, pause, release/resume,
checkpoint continuity, selected transcripts and forced cancellation without
model weights or a product fallback.
The native entry point calls `multiprocessing.freeze_support()` before argument
parsing or GUI initialization, including Windows resource-tracker invocations.


`playlists.py` normalizes explicit playlist URLs and enumerates yt-dlp flat
metadata with playback download disabled. `Job.import_playlist` submits a short
request; the existing metadata thread resolves it, checks cancellation/close,
and appends titled tasks atomically in relative playlist order. Video IDs are
normalized for deduplication. Completed request cleanup cannot clear options of
a newly accepted import. Access tokens are private import/session options and
are never sent to the metadata reader, snapshots or archive exports. Only
individual video URLs reach the media worker. Playlist import can be cancelled
independently of a currently running transcription.

`Job.export_entries` returns a consistent copy of nonempty per-item results,
including playlist URL/title provenance without runtime credentials. Compare
playlist URLs when selecting a common collection title; equal titles alone do
not identify one playlist. Collection names include the actual result count and
local date, with UTF-8-byte-bounded safe filenames for Windows/macOS.
`exports.export_collection` writes each existing export format sequentially
into a temporary ZIP and atomically replaces the selected destination only
when successful. Numbered sanitized basenames preserve Unicode titles without
path separators or filename collisions. Partial results are explicitly named.
The same ZIP also includes a combined document in the selected format. TXT
separates title/body blocks; DOCX/PDF reuse the existing Arabic font/body pipeline
with per-video headings and page boundaries. A playlist title and count/date
use separate title lines so mixed RTL/LTR ordering remains readable. The complete
archive is committed only after this additional document succeeds too. The UI
defaults to PDF and displays complete/partial counts without altering selection.
Transcript content is not automatically persisted, and no ZIP is created until
the user exports. The session store remains memory-only.
