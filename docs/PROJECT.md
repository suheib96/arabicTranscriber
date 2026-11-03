# Arabic Transcriber: product specification

## Outcome

Deliver a minimal, modern desktop app that lets a nontechnical user transcribe Arabic speech from a local video/audio file or a YouTube URL. The same codebase supports macOS and Windows, with separately built application packages. The user develops on a Mac and intends to share packages through GitHub Releases or directly with others.

## Interface

Use Python for orchestration, media processing and transcription. The preferred interface is pywebview with a small local HTML/CSS/JavaScript frontend. The user prefers one clean desktop window, sparse explanatory text, clear labeled buttons, generous spacing and a polished modern appearance. Avoid adding a web server or frontend framework unless it materially simplifies a demonstrated need. No cloud transcription service is required.

Provide File / YouTube input selection, file picker or link field, Transcribe, visible progress and growing Arabic transcript, Cancel, a timestamp visibility toggle, Copy all and Save/export actions. Keep model configuration unobtrusive. Maintain correct Arabic right-to-left display and sensible mixed Arabic/Latin text behavior. Opening a native file or save dialog must work through the application bridge. Keep the window responsive during work. Preserve completed segments after cancellation or recoverable errors.

An explicitly requested ImageGen sub-agent should generate a visual reference and explain a few concrete design choices. Use the image to inform real frontend controls, not as a screenshot replacement for functioning UI. Preserve the final reference image in the project; discarded variants may remain in `.scratch`.

## Model and runtime

Fix the speech model identity to `CohereLabs/cohere-transcribe-arabic-07-2026`, with language `ar`. No automatic selection of another ASR model or cloud fallback. The original Hugging Face repository is gated: explain first-run access, use the user's own local read token without logging or committing it, download/cache the model once and support later offline use of local files. Acquiring model access is the user's account action; missing access must not stop development of the rest of the app.

The original weights are approximately 4.13 GB on disk. This is not total runtime memory. Investigate device, dtype and bounded batch size on available hardware before claiming performance or memory requirements. Prefer a shared Transformers/PyTorch runtime first; enable supported accelerators where verified and provide an honest CPU option. A macOS-only MLX artifact must not be distributed as though it ran on Windows. Any optional compressed derivative needs explicit provenance and remains the same model family; choose the official original as the initial fixed default.

## Media and progress

Use FFmpeg/ffprobe for media decoding to suitable mono audio, generally 16 kHz, and yt-dlp for YouTube audio import. Fetch audio rather than full video where available. Resolve and package required downloader components and JavaScript runtime where the current yt-dlp version needs them. Show separate preparation/download/model/transcription stages and actionable errors. YouTube support is best effort and needs a maintainable update path.

Process bounded audio segments sequentially or in small batches. Publish each completed segment to the frontend promptly. Progress is based on processed media duration; label stages without measurable percentage honestly. Do not promise real-time speed, token streaming, speaker attribution or exact word timings. Handle silence to avoid spurious speech, without introducing another speech-transcription model. Keep original timeline offsets when skipping silence; avoid duplicated/dropped words at segment boundaries.

## Timestamps

Cohere does not supply native timestamps. Initial timestamps may be approximate audio-segment offsets, visibly described as approximate in a concise tooltip/settings hint. Store segments with original timeline start/end and text separately from presentation. Let the user show/hide times in the app and choose whether they are included in copied/exported output. Toggling visibility must preserve the transcript and must not rerun transcription. Exact word alignment is beyond the initial requirement.

## Copy and export

Provide a button to copy the entire transcript with a success state, plus exports to UTF-8 TXT, Word `.docx` and PDF. The user said DOC; implement the current Word-compatible DOCX format and label it clearly. Never put DOCX bytes behind a legacy `.doc` extension.

Apply the timestamp option consistently to copies and all export formats. Preserve Arabic script, right-to-left paragraphs, punctuation, Latin names/numbers and multiline text. Bundle appropriately licensed Arabic fonts where needed. Verify DOCX/PDF rendering visually with mixed text and multiple pages: joined Arabic glyphs, ordering, line wrapping and page boundaries must work. Use available document/PDF skills to guide this work. Export through a native save dialog with correct extension and cancellation handling.

## Tests and verification

Use the TDD skill in small vertical red-to-green cycles. The user explicitly authorizes selecting test boundaries without asking for confirmation. Record a small set of public boundaries: job input/error lifecycle; successive transcript/progress events and cancellation; transcript rendering with timestamps; copy/export of known Arabic text. Prefer deterministic audio fixtures and fakes only at external boundaries (large model inference and live network) for fast tests. Exercise real FFmpeg and document exporters where practical. Keep an optional real-model smoke check separate from regular CI and report clearly whether it ran. Do not download multi-gigabyte weights for every CI run. Include a lightweight bridge/frontend smoke check and inspect actual UI, not just static code.

## Packaging and GitHub

Use Conventional Commits for coherent steps. Keep generated artifacts, models, tokens, input media and `.scratch/` outside version control. Package Python, frontend assets and necessary media tools so recipients do not need to install Python or use terminal commands. Prefer a maintainable app bundle/installer over forcing a huge self-extracting single file. Build and test macOS and Windows packages separately on matching operating systems; document CPU architectures and acceleration requirements. Inspect pywebview platform dependencies, especially Windows WebView2, and handle them explicitly.

Implement GitHub Actions for main/PR tests and package builds with downloadable artifacts. Version tags such as `v*` trigger release package builds and upload resulting macOS/Windows assets and checksums to a GitHub Release, with least necessary permissions. Never expose credentials to untrusted PR runs. The project currently has no specified GitHub remote; create/configure local workflows and precise push/tag instructions, but do not invent a repository or claim workflows ran remotely.

## Signing and delivery

Investigate current Apple signing/notarization and Windows signing/reputation requirements using official sources. Add optional, documented signing hooks backed by repository secrets. Builds must still work in unsigned development mode without paid credentials. Mark unsigned artifacts honestly. Signing/notarization can reduce installation friction but cannot guarantee zero operating-system warnings; never disable security checks or present unsigned packages as certified. The user has not supplied certificates, developer memberships or a signing provider, so do not buy or enroll on their behalf.

The final implementation report must explain how to start locally, run tests, build each package, enable release automation, and supply signing credentials. State which checks actually passed and what remains for real-model, Windows or signed-distribution verification.

## Source references verified during planning

- Original model and access: https://huggingface.co/CohereLabs/cohere-transcribe-arabic-07-2026
- Cohere ASR API: https://huggingface.co/docs/transformers/model_doc/cohere_asr
- pywebview: https://pywebview.flowrl.com/
- yt-dlp: https://github.com/yt-dlp/yt-dlp
- PyInstaller: https://pyinstaller.org/en/stable/
- GitHub build matrix: https://docs.github.com/en/actions/tutorials/build-and-test-code/python

Recheck version-sensitive APIs and platform/signing details against their official sources during implementation.
