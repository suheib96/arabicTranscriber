# Bundled components

App source is MIT. Model weights are never redistributed in the package; the fixed
Cohere model is fetched by the user under its Hugging Face access conditions and
Apache 2.0 license. Input media, tokens and caches are not package resources.

- Noto Sans Arabic and Noto Sans: SIL Open Font License 1.1. License files are
  beside the fonts. Static weight 400 / width 100 instances derived from
  https://github.com/google/fonts/tree/main/ofl/notosansarabic and
  https://github.com/google/fonts/tree/main/ofl/notosans using fontTools.
- Node.js v24.13.0: MIT plus bundled third-party notices; upstream LICENSE is
  copied into each package. https://nodejs.org/dist/v24.13.0/
- FFmpeg from the pinned imageio-ffmpeg wheel: separate executable, GPL build.
  Exact version and binary checksum are in tools/versions.json. The app invokes
  the tool as an independent process; no FFmpeg libraries are linked into app code.
  Binary provenance and corresponding build/source instructions:
  https://github.com/imageio/imageio-ffmpeg and https://github.com/BtbN/FFmpeg-Builds
  / https://evermeet.cx/ffmpeg/ (depending on wheel platform).
  FFmpeg source: https://ffmpeg.org/download.html and licenses:
  https://ffmpeg.org/legal.html . Before public redistribution, retain the
  corresponding complete source and build recipes for the exact binary and
  all enabled GPL libraries, and distribute them alongside the binaries or
  provide a legally sufficient source offer. A link to generic sources alone
  does not establish full compliance. CI packages are development artifacts;
  a public maintainer must complete this distribution step for their target.
- Python, PyTorch, Transformers, pywebview, yt-dlp/ejs, HarfBuzz, fpdf2 and
  python-docx retain their upstream licenses. PyInstaller collects package
  license metadata where available. Use uv.lock for the exact versions.

The application provides no media rights or access bypass. YouTube availability
can change; update and rebuild the pinned downloader/runtime dependencies when needed.
