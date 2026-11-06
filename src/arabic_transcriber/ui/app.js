const $ = id => document.getElementById(id);
let source = 'file', selectedFile = '', snapshot = {segments: [], status: 'idle'};
let polling = false, renderedSegments = [], renderedTimes = false, localError = '';
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
let controlPending = false;
const queueRows = new Map();
const options = () => ({token: $('token').value, offline: $('offline').checked, device: $('device').value});
const pendingItem = item => ['queued', 'running', 'paused', 'cancelling'].includes(item.status);
function renderQueue(items) {
  const ids = new Set(items.map(item => item.id));
  for (const [id, row] of queueRows) if (!ids.has(id)) { row.element.remove(); queueRows.delete(id); }
  let waiting = 0;
  for (const item of items) {
    let row = queueRows.get(item.id);
    if (!row) {
      const element = document.createElement('div'); element.className = 'queue-row'; element.dataset.id = item.id;
      const title = document.createElement('button'); title.className = 'queue-title'; title.onclick = () => act('select', item.id);
      const status = document.createElement('span'); status.className = 'queue-stage';
      const progress = document.createElement('progress'); progress.max = 1;
      const elapsed = document.createElement('span'); elapsed.className = 'queue-elapsed';
      const action = document.createElement('button'); action.className = 'queue-action';
      element.append(title, status, progress, elapsed, action); $('queueList').append(element);
      row = {element, title, status, progress, elapsed, action}; queueRows.set(item.id, row);
    }
    const active = item.id === snapshot.active_id;
    const loadingTitle = ['pending', 'loading'].includes(item.metadata_status);
    row.element.classList.toggle('selected', item.id === snapshot.selected_id);
    row.element.dataset.status = item.status;
    row.title.textContent = loadingTitle ? 'Titel wird geladen …' : item.title;
    row.title.title = item.source === 'youtube' ? `${item.title}\n${item.value}` : item.title;
    row.title.setAttribute('aria-pressed', String(item.id === snapshot.selected_id));
    let label = item.stage || 'Wartet';
    if (item.status === 'queued') label = `Wartet · ${++waiting}`;
    else if (item.status === 'paused') label = 'Pausiert';
    if (active && item.progress != null && item.status === 'running') label += ` · ${Math.round(item.progress * 100)} %`;
    row.status.textContent = label;
    row.progress.hidden = !active || item.status !== 'running';
    row.progress.setAttribute('aria-label', item.title);
    if (item.progress == null) row.progress.removeAttribute('value'); else row.progress.value = item.progress;
    row.elapsed.textContent = item.elapsed_seconds ? timeLabel(item.elapsed_seconds) : '';
    const cancellable = ['running', 'paused', 'cancelling'].includes(item.status);
    const removable = item.status === 'queued' || item.status === 'error';
    row.action.hidden = !cancellable && !removable;
    row.action.disabled = controlPending || item.status === 'cancelling';
    row.action.classList.toggle('queue-remove', !cancellable);
    row.action.textContent = cancellable ? '□' : '×';
    const actionTitle = cancellable ? 'Auftrag abbrechen' : 'Auftrag entfernen';
    row.action.title = actionTitle; row.action.setAttribute('aria-label', `${actionTitle}: ${item.title}`);
    row.action.onclick = () => act(cancellable ? 'cancel' : 'remove', item.id);
  }
}
function render() {
  const items = snapshot.items || [], segments = snapshot.segments || [];
  const pending = items.filter(pendingItem), busy = pending.length > 0;
  const message = localError || snapshot.queue_error || snapshot.error || '';
  $('error').hidden = !message; $('error').textContent = message;
  $('queueCard').hidden = !items.length;
  renderQueue(items);
  const waiting = items.filter(i => i.status === 'queued').length;
  $('queueSummary').textContent = snapshot.paused ? `Pausiert · ${pending.length} offen` : snapshot.active_id ? `1 läuft${waiting ? ` · ${waiting} warten` : ''}` : waiting ? `${waiting} ${waiting === 1 ? 'wartet' : 'warten'}` : 'Abgeschlossen';
  $('pause').hidden = !busy && !snapshot.paused;
  $('pause').textContent = snapshot.paused ? 'Fortsetzen' : 'Pause';
  $('pause').classList.toggle('resume', !!snapshot.paused);
  $('pause').disabled = controlPending || snapshot.releasing_memory;
  $('releaseMemory').hidden = !snapshot.paused;
  $('releaseMemory').disabled = controlPending || !snapshot.worker_running || snapshot.releasing_memory;
  const active = items.find(item => item.id === snapshot.active_id);
  $('memoryState').textContent = snapshot.releasing_memory ? 'Speicher wird freigegeben …' : snapshot.model_loaded ? `Modell im RAM${snapshot.paused && snapshot.release_in_seconds != null ? ` · Freigabe in ${timeLabel(snapshot.release_in_seconds)}` : ''}` : active && (active.stage || '').startsWith('Modell') ? 'Modell wird geladen …' : 'Modell entladen';
  $('queueState').textContent = snapshot.pausing ? 'Pause angefordert …' : '';
  $('start').disabled = controlPending;
  ['token', 'device', 'offline'].forEach(id => $(id).disabled = busy && !snapshot.paused);
  $('copy').disabled = $('export').disabled = !segments.length;
  $('empty').hidden = segments.length > 0; $('segmentCount').textContent = segments.length || '';
  const selected = items.find(item => item.id === snapshot.selected_id);
  $('transcriptTitle').textContent = selected ? selected.title : '';
  renderTranscript(segments);
}
function error(e) { localError = String(e.message || e); $('error').hidden = false; $('error').textContent = localError; }
function feedback(text) { localError = ''; $('error').hidden = !snapshot.error; $('feedback').textContent = text; setTimeout(() => $('feedback').textContent = '', 3500); }
function selectSource(value) {
  source = value; $('choose').hidden = value !== 'file'; $('urlLabel').hidden = value !== 'youtube';
  for (const v of ['file', 'youtube']) { $(v + 'Tab').classList.toggle('selected', v === value); $(v + 'Tab').setAttribute('aria-pressed', String(v === value)); }
}
async function refresh() { snapshot = await pywebview.api.snapshot(); render(); }
async function act(method, argument) {
  if (controlPending) return;
  controlPending = true; render();
  try { const result = await pywebview.api[method](argument); if (!result.ok) error(result.error || 'Aktion fehlgeschlagen.'); else localError = ''; await refresh(); }
  catch(e) { error(e); }
  finally { controlPending = false; render(); }
}
$('fileTab').onclick = () => selectSource('file'); $('youtubeTab').onclick = () => selectSource('youtube');
$('settingsButton').onclick = () => {
  $('settings').hidden = !$('settings').hidden;
  $('settingsButton').setAttribute('aria-expanded', String(!$('settings').hidden));
};
$('access').onclick = async event => { event.preventDefault(); try { await pywebview.api.open_model_access(); } catch(e) { error(e); } };
$('choose').onclick = async () => {
  try { const path = await pywebview.api.choose_file(); if (path) { selectedFile = path; $('filename').textContent = path.split(/[\\/]/).pop(); localError = ''; $('error').hidden = true; } } catch(e) { error(e); }
};
$('start').onclick = async () => {
  if (controlPending) return;
  controlPending = true; render();
  try {
    const result = await pywebview.api.start(source, source === 'file' ? selectedFile : $('url').value, options());
    if (!result.ok) error(result.error);
    else {
      localError = ''; $('token').value = '';
      if (source === 'youtube') $('url').value = '';
      else { selectedFile = ''; $('filename').textContent = 'Audio oder Video auswählen'; }
      await refresh();
    }
  } catch(e) { error(e); }
  finally { controlPending = false; render(); }
};
$('pause').onclick = () => { const paused = snapshot.paused; const settings = options(); if (paused) $('token').value = ''; return act(paused ? 'resume' : 'pause', paused ? settings : undefined); };
$('releaseMemory').onclick = () => act('release_memory');
$('times').onchange = render;
$('copy').onclick = async () => { try { const r = await pywebview.api.copy_all($('outputTimes').checked); if (!r.ok) error(r.error); else feedback('Kopiert'); } catch(e) { error(e); } };
$('export').onclick = async () => { try { const r = await pywebview.api.export($('format').value, $('outputTimes').checked); if (r.error) error(r.error); else if (r.path) feedback('Gespeichert'); } catch(e) { error(e); } };
async function poll() {
  if (!polling) return;
  try { const next = await pywebview.api.snapshot(); if (next.error && next.error !== snapshot.error) localError = ''; snapshot = next; render(); }
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
  } catch(e) { /* CPU stays available if platform detection fails. */ }
  poll();
});
window.addEventListener('beforeunload', () => polling = false);
window.desktopSmoke = async () => {
  await document.fonts.ready;
  const state = await pywebview.api.snapshot();
  return {title: document.title, bridge: state.status === 'idle', buttons: !!$('start') && !!$('export') && !!$('pause') && !!$('releaseMemory'),
    rtl: $('transcript').dir, font: document.fonts.check('21px NotoArabic'), bodyWidth: document.body.scrollWidth, viewport: innerWidth};
};
render();
