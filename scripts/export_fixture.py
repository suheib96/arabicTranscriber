"""Generate deterministic multi-page visual QA fixtures, never demo transcription."""

from pathlib import Path

from arabic_transcriber.exports import export_transcript

out = Path(".scratch/arabic-transcriber/exports")
out.mkdir(parents=True, exist_ok=True)
text = (
    "مرحبًا بكم. نتحدث اليوم عن أهمية التعلم وتبادل المعرفة.\n"
    "يمكن للتقنية أن تساعدنا على الوصول إلى المعلومات بسهولة. "
    "نستخدم Python وBerlin 2026، والرقم 123.45 في هذا المثال. "
    "الأهم هو أن نستخدم هذه الأدوات بطريقة واضحة ومفيدة."
)
segments = [{"start": i * 24, "end": (i + 1) * 24, "text": text} for i in range(18)]
for fmt in ("docx", "pdf"):
    export_transcript(segments, out / ("arabic-layout." + fmt), fmt, True)
