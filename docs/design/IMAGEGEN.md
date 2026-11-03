# Arabic Transcriber — visual reference

Generated with the built-in ImageGen tool (one image, no CLI fallback). The PNG is a visual direction only, not implemented UI.

## Four design decisions

1. Use one column with a compact File / YouTube segmented input selector; reserve most of the window for the transcript rather than a sidebar.
2. Use warm off-white surfaces, thin neutral borders, generous spacing and one restrained deep-teal accent for the selected input, primary action and progress.
3. Keep Arabic content right-aligned with large readable type; show approximate timestamp chips separately and provide one quiet visibility toggle.
4. Group Copy all and Export at the end of the document, with TXT / Word (.docx) / PDF in a compact menu rather than three competing primary buttons.

## Implementation interpretation

The generated image intentionally shows the running state. In functioning UI, replace/disable the Transcribe action while running and keep Cancel available. Preserve keyboard access and accessible contrast. Anchor the export menu upward or otherwise constrain it inside the actual window; the reference image lets it extend below the window frame. Use the OS title bar rather than reproducing macOS traffic-light controls on Windows. Render all labels and Arabic text as real text, with SVG/CSS controls and actual RTL behavior. The mockup is not a screenshot layer.

## Final prompt

Use case: ui-mockup
Asset type: high-fidelity visual reference for a real minimalist Arabic transcription desktop app, not a promotional landing page.
Primary request: Design one polished desktop application window, front-facing crisp flat screenshot, wide landscape composition approximately 1440x1000. It should feel quietly premium, modern, simple and useful on both macOS and Windows. Very sparse German text, large legible Arabic sample transcript. Single clean workspace, no sidebar, no navigation dashboard, no marketing copy.
Composition: A lightly rounded off-white application window centered on a very pale warm-gray background with subtle shadow. Compact understated title bar reading "Arabic Transcriber", tiny settings gear at far right. Content has generous 32px-like spacing. Top small segmented tabs "Datei" and "YouTube", Datei selected. A shallow file input card displays a small outlined file icon, filename "Interview.mp4", metadata "12:48 · Arabisch", and a quiet "Datei wählen" button. Under that, one primary dark teal button "Transkribieren" and subtle text action "Abbrechen". Thin teal progress bar below with compact status "Transkription läuft" and "42 %". The large transcript area takes most of the window. Its header reads "Transkript" left; on right a small toggle enabled and label "Zeitangaben". Beside it a tiny subdued "(ca.)" to indicate approximate timing. Within the transcript area, 3 spacious right-aligned Arabic paragraphs with muted small approximate timestamp chips, times "[00:00]", "[00:24]", "[00:48]". Use these Arabic texts accurately and joined in proper RTL:
"مرحبًا بكم. نتحدث اليوم عن أهمية التعلم وتبادل المعرفة."
"يمكن للتقنية أن تساعدنا على الوصول إلى المعلومات بسهولة."
"الأهم هو أن نستخدم هذه الأدوات بطريقة واضحة ومفيدة."
Last paragraph may have a subtle caret showing the document is growing. No artificial waveform illustration. Under the transcript, bottom actions: outlined button with copy icon "Alles kopieren"; outlined export button "Exportieren" with down chevron. Show a small clean opened export menu anchored to this button listing "TXT", "Word (.docx)", "PDF". Keep menu away from Arabic text.
Style: elegant contemporary productivity application, coherent restrained controls, 12px-ish corners, thin warm-gray borders, fine icons, clear dark charcoal sans-serif Latin typography and clean readable Arabic sans-serif, comfortable line height, balanced whitespace. White and warm gray with one muted deep-teal accent. Use high-quality readable real UI text. No gradients, no bright purple, no glow, no decorative illustration, no gigantic headings, no explanatory paragraphs, no brand badges, no logo, no photography, no device mockup.
Constraints: one single interface image; show all requested controls, Arabic content and approximate timestamps; image is a design reference only.

