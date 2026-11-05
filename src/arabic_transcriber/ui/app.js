const $ = id => document.getElementById(id);
let source = 'file', selectedFile = '', snapshot = {segments: [], status: 'idle'};
let polling = false, renderedSegments = [], renderedTimes = false;
const timeLabel = seconds => {
  const value = Math.floor(seconds), hours = Math.floor(value / 3600);
  const rest = `${String(Math.floor(value / 60) % 60).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`;
  return hours ? `${String(hours).padStart(2, '0')}:${rest}` : rest;
};
function stamp(paragraph, segment, visible) {
  let time = paragraph.querySelector('time');
  if (!visible) { if (time) time.remove(); return; }
  if (!time) { time = document.createElement('time'); paragraph.prepend(time); }
  time.textContent = `≈ ${timeLabel(segment.start)} – ${timeLabel(segment.end)}`;
}
function renderTranscript(segments) {
  const area = $('transcript'), times = $('times').checked;
  const atBottom = area.scrollHeight - area.scrollTop - area.clientHeight < 70;
  const samePrefix = renderedSegments.length <= segments.length && renderedSegments.every((s, i) =>
    s.start === segments[i].start && s.end === segments[i].end && s.text === segments[i].text);
  if (!samePrefix) { area.replaceChildren(); renderedSegments = []; }
  const added = segments.length > renderedSegments.length;
  for (let i = renderedSegments.length; i < segments.length; i++) {
    const paragraph = document.createElement('p'); paragraph.className = 'segment';
    const words = document.createElement('span'); words.className = 'words';
    words.textContent = segments[i].text; paragraph.append(words);
    stamp(paragraph, segments[i], times); area.append(paragraph);
  }
  if (times !== renderedTimes) Array.from(area.children).forEach((p, i) => stamp(p, segments[i], times));
  renderedSegments = segments.slice(); renderedTimes = times;
  if (added && atBottom) area.scrollTop = area.scrollHeight;
}
function render() {
  const busy = ['running', 'cancelling'].includes(snapshot.status), segments = snapshot.segments || [];
  $('stage').textContent = snapshot.stage || 'Bereit';
  $('error').hidden = !snapshot.error; $('error').textContent = snapshot.error || '';
  $('progress').hidden = !busy; $('dot').classList.toggle('working', busy);
  $('elapsed').textContent = busy ? timeLabel(snapshot.elapsed_seconds || 0) : '';
  if (snapshot.progress == null) { $('progress').removeAttribute('value'); $('percent').textContent = ''; }
  else { $('progress').value = snapshot.progress; $('percent').textContent = `${Math.round(snapshot.progress * 100)} %`; }
  ['start', 'choose', 'fileTab', 'youtubeTab', 'url', 'token', 'device', 'offline'].forEach(id => $(id).disabled = busy);
  $('cancel').hidden = !busy; $('cancel').disabled = snapshot.status === 'cancelling';
  $('copy').disabled = $('export').disabled = !segments.length;
  $('empty').hidden = segments.length > 0; $('segmentCount').textContent = segments.length || '';
  renderTranscript(segments);
}
function error(e) { $('error').hidden = false; $('error').textContent = String(e.message || e); }
function feedback(text) { $('feedback').textContent = text; setTimeout(() => $('feedback').textContent = '', 3500); }
function selectSource(value) {
  source = value; $('choose').hidden = value !== 'file'; $('urlLabel').hidden = value !== 'youtube';
  for (const v of ['file', 'youtube']) { $(v + 'Tab').classList.toggle('selected', v === value); $(v + 'Tab').setAttribute('aria-pressed', String(v === value)); }
}
$('fileTab').onclick = () => selectSource('file'); $('youtubeTab').onclick = () => selectSource('youtube');
$('settingsButton').onclick = () => {
  $('settings').hidden = !$('settings').hidden;
  $('settingsButton').setAttribute('aria-expanded', String(!$('settings').hidden));
};
$('access').onclick = async event => { event.preventDefault(); try { await pywebview.api.open_model_access(); } catch(e) { error(e); } };
$('choose').onclick = async () => {
  try { const path = await pywebview.api.choose_file(); if (path) { selectedFile = path; $('filename').textContent = path.split(/[\\/]/).pop(); } } catch(e) { error(e); }
};
$('start').onclick = async () => {
  try {
    $('start').disabled = true;
    const result = await pywebview.api.start(source, source === 'file' ? selectedFile : $('url').value,
      {token: $('token').value, offline: $('offline').checked, device: $('device').value});
    $('token').value = '';
    if (!result.ok) { $('start').disabled = false; error(result.error); }
    else { snapshot = await pywebview.api.snapshot(); render(); }
  } catch(e) { $('start').disabled = false; error(e); }
};
$('cancel').onclick = async () => {
  try { $('cancel').disabled = true; await pywebview.api.cancel(); snapshot = await pywebview.api.snapshot(); render(); }
  catch(e) { $('cancel').disabled = false; error(e); }
};
$('times').onchange = render;
$('copy').onclick = async () => { try { const r = await pywebview.api.copy_all($('outputTimes').checked); if (!r.ok) error(r.error); else feedback('Kopiert'); } catch(e) { error(e); } };
$('export').onclick = async () => { try { const r = await pywebview.api.export($('format').value, $('outputTimes').checked); if (r.error) error(r.error); else if (r.path) feedback('Gespeichert'); } catch(e) { error(e); } };
async function poll() {
  if (!polling) return;
  try { snapshot = await pywebview.api.snapshot(); render(); }
  catch(e) { error('Verbindung zur Verarbeitung unterbrochen.'); }
  finally { if (polling) setTimeout(poll, 400); }
}
window.addEventListener('pywebviewready', async () => {
  if (polling) return;
  polling = true;
  try {
    const info = await pywebview.api.platform_info();
    document.querySelector('option[value="mps"]').hidden = info.platform !== 'darwin';
    document.querySelector('option[value="cuda"]').hidden = info.platform === 'darwin';
  } catch(e) { /* Keep manual CPU selection available if platform detection fails. */ }
  poll();
});
window.addEventListener('beforeunload', () => polling = false);
window.desktopSmoke = async () => {
  await document.fonts.ready;
  const state = await pywebview.api.snapshot();
  return {title: document.title, bridge: state.status === 'idle', buttons: !!$('start') && !!$('export'),
    rtl: $('transcript').dir, font: document.fonts.check('21px NotoArabic'), bodyWidth: document.body.scrollWidth, viewport: innerWidth};
};
render();
