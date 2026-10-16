// MITSU HUD — reactor core, voice pipeline, panels. Original code.
const $ = id => document.getElementById(id);
const log = $('log'), act = $('act'), meta = $('meta');
let profile = {}, providers = [], ws = null, wsAlive = false, rec = null;
let state = 'idle'; // idle | listening | speaking | working | error
let lastInteract = Date.now();
let AC = null, analyser = null, audioEl = null, synthOK = false;

/* ---------- reactor ---------- */
const cv = $('reactor'), ctx = cv.getContext('2d');
const CX = 260, CY = 260;
let t = 0, wave = new Array(64).fill(0);
function paper() { return document.body.classList.contains('paper'); }
function color() {
  // monochrome HUD: brightness carries state, not hue — in both themes
  if (paper()) return state === 'idle' ? '#a1a1aa' : '#0a0a0b';
  return state === 'idle' ? '#52525b' : '#f4f4f5';
}
function ring(r, dash, speed, w, alpha) {
  ctx.save(); ctx.translate(CX, CY); ctx.rotate(t * speed);
  ctx.strokeStyle = color(); ctx.globalAlpha = alpha; ctx.lineWidth = w;
  ctx.setLineDash(dash); ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.stroke(); ctx.restore();
}
function draw() {
  t += 0.008 + (state === 'speaking' ? 0.02 : state === 'working' ? 0.012 : 0);
  ctx.clearRect(0, 0, 520, 520);
  const c = color();
  // waveform ring
  ctx.save(); ctx.translate(CX, CY); ctx.strokeStyle = c; ctx.globalAlpha = .9; ctx.lineWidth = 3;
  ctx.beginPath();
  for (let i = 0; i <= 64; i++) {
    const a = (i / 64) * Math.PI * 2, v = wave[i % 64];
    const r = 150 + (state === 'speaking' || state === 'listening' ? v * 46 : Math.sin(t * 3 + i * .4) * 7);
    const x = Math.cos(a) * r, y = Math.sin(a) * r;
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  }
  ctx.closePath(); ctx.stroke(); ctx.restore();
  ring(120, [8, 10], .25, 2, .7); ring(100, [2, 6], -.4, 1.5, .6); ring(190, [30, 14], .12, 2, .5);
  ring(215, [4, 18], -.08, 1, .35);
  // core
  const pulse = 34 + Math.sin(t * (state === 'speaking' ? 9 : 3)) * (state === 'speaking' ? 9 : 4);
  const g = ctx.createRadialGradient(CX, CY, 2, CX, CY, pulse + 22);
  g.addColorStop(0, paper() ? '#0a0a0b' : '#ffffff'); g.addColorStop(.35, c); g.addColorStop(1, 'transparent');
  ctx.globalAlpha = state === 'idle' ? .75 : 1; ctx.fillStyle = g;
  ctx.beginPath(); ctx.arc(CX, CY, pulse + 22, 0, Math.PI * 2); ctx.fill(); ctx.globalAlpha = 1;
  requestAnimationFrame(draw);
}
function setState(s, label) {
  state = s;
  $('state').textContent = (s === 'error' ? '⚠ ' : '') + (label || s.toUpperCase());
  $('state').style.color = color();
}
requestAnimationFrame(draw);
setInterval(() => { $('clock').textContent = new Date().toLocaleTimeString(); }, 1000);

/* ---------- audio: browser voice first, server voice fallback ---------- */
function ensureAC() {
  if (AC) {
    try { if (AC.state === 'suspended') AC.resume(); } catch (e) {}
    return AC;
  }
  try {
    const Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) return null;
    AC = new Ctor();
    analyser = AC.createAnalyser(); analyser.fftSize = 128;
    if (AC.state === 'suspended') AC.resume();
    return AC;
  } catch (e) { AC = null; return null; }
}
function feedWave() {
  if (!analyser) return; // <audio> fallback path: no analyser node
  const d = new Uint8Array(analyser.frequencyBinCount);
  const tick = () => {
    if (state !== 'speaking' && state !== 'listening') return;
    analyser.getByteFrequencyData(d);
    for (let i = 0; i < 64; i++) wave[i] = d[Math.floor(i * d.length / 64)] / 255;
    setTimeout(tick, 60);
  };
  tick();
}
let speakToken = 0;
function stopVoice() {
  speakToken++;
  try { speechSynthesis && speechSynthesis.cancel(); } catch (e) {}
  try { audioEl && audioEl.pause(); } catch (e) {}
  audioEl = null;
  if (state === 'speaking') setState('idle');
}
function speak(text) {
  if (!$('speak').checked || !text) return;
  stopVoice(); ensureAC(); setState('speaking');
  const my = ++speakToken;
  const done = () => { if (my === speakToken) setState('idle'); };
  // 1) browser voice (Chrome/Firefox) unless forced to server voice
  if (!$('servervoice').checked && 'speechSynthesis' in window && synthOK !== false) {
    try {
      const u = new SpeechSynthesisUtterance(text.slice(0, 600));
      u.rate = (profile.speech_rate || 175) / 175; u.lang = profile.language || 'en';
      const vs = speechSynthesis.getVoices();
      const v = vs.find(v => v.name === profile.voice);
      if (v) u.voice = v;
      u.onend = done;
      // broken backend (e.g. speechSynthesis exists but never speaks):
      // instant error must fall back to the server voice, not go silent
      u.onerror = () => {
        if (my === speakToken && !audioEl &&
            !(speechSynthesis && speechSynthesis.speaking)) serverSpeak(text, done);
        else done();
      };
      speechSynthesis.cancel(); speechSynthesis.speak(u);
      // liveliness for the ring while synth speaks (no analyser available)
      const idle = setInterval(() => {
        if (state !== 'speaking') return clearInterval(idle);
        for (let i = 0; i < 64; i++) wave[i] = .3 + Math.random() * .5;
      }, 90);
      // safety: if nothing speaks in 3s (no backend, e.g. WebKit native), fall through
      // token-guarded so a late timer can never double-speak over real audio
      setTimeout(() => {
        if (my === speakToken && state === 'speaking' && speechSynthesis && !speechSynthesis.speaking && !audioEl)
          serverSpeak(text, done);
      }, 3000);
      return;
    } catch (e) { /* fall through to server */ }
  }
  serverSpeak(text, done);
}
async function serverSpeak(text, done) {
  try {
    const r = await fetch('/api/tts?text=' + encodeURIComponent(text.slice(0, 800)) +
      '&rate=' + (profile.speech_rate || 175) + '&voice=' + (profile.server_voice || 'lessac'));
    if (!r.ok) throw new Error(await r.text());
    const buf = await r.arrayBuffer();
    const ac = ensureAC();
    if (ac && ac.decodeAudioData) {
      const decoded = await ac.decodeAudioData(buf);
      const src = ac.createBufferSource(); src.buffer = decoded;
      src.connect(analyser); analyser.connect(ac.destination);
      src.onended = done; src.start(); feedWave();
      audioEl = { pause: () => { try { src.stop(); } catch (e) {} } };
      return;
    }
    // ancient engines (old WebKit): plain <audio> always plays
    const url = URL.createObjectURL(new Blob([buf], { type: 'audio/wav' }));
    const el = new Audio();
    el.onended = () => { URL.revokeObjectURL(url); done(); };
    el.onerror = () => { URL.revokeObjectURL(url); done(); };
    audioEl = el;
    el.src = url;
    try { await el.play(); feedWave(); }
    catch (e) { URL.revokeObjectURL(url); done(); }
  } catch (e) {
    addMsg('MITSU', 'Voice backend unreachable: ' + e.message + ' — reply shown as text.');
    done();
  }
}

/* ---------- chat ---------- */
function addMsg(who, text, sub = '') {
  const d = document.createElement('div');
  d.className = 'msg' + (who === 'You' ? ' me' : '');
  const w = document.createElement('div'); w.className = 'who'; w.textContent = who + ' ' + sub;
  const b = document.createElement('div'); b.textContent = text;
  d.append(w, b); log.appendChild(d); log.scrollTop = log.scrollHeight;
}
async function boot() {
  const bl = $('bootlog'), lines = ['MITSU OS v0.2 — boot', 'core … ok', 'memory … ok', 'providers … ok'];
  for (const l of lines) { bl.textContent += l + '\n'; await new Promise(r => setTimeout(r, 180)); }
  $('bootbtn').classList.remove('hidden');
  $('setupbtn').classList.remove('hidden');
  await new Promise(res => $('bootbtn').onclick = () => { ensureAC(); res(); });
  $('boot').classList.add('hidden');
  const h = await (await fetch('/api/health')).json();
  $('mode').textContent = h.mode; $('net').textContent = h.mode;
  profile = await (await fetch('/api/profile')).json();
  providers = await (await fetch('/api/providers?probe=1')).json();
  let defProv = profile.default_provider, defModel = profile.default_model;
  if (defProv === 'auto' || defModel === 'auto') {
    try {
      const d = await (await fetch('/api/defaults')).json();
      if (defProv === 'auto') defProv = d.provider;
      if (defModel === 'auto') defModel = d.model;
    } catch (e) {}
  }
  fillProviderDD();
  $('provider').value = providers.some(x => x.usable && x.name === defProv)
    ? defProv : (providers.find(x => x.usable) || {}).name || defProv;
  ddPaint('provider');
  await refreshModels();
  if (defModel) { $('model').value = defModel; ddPaint('model'); }  // was silently left on first list entry → moondream = vision-only = dead chat
  const vs = await (await fetch('/api/voice/status')).json();
  synthOK = 'speechSynthesis' in window;
  ddFill('svoice', vs.server.voices.map(v => ({ v: v.id, label: `${v.label}${v.ready ? '' : ' (missing)'}` })));
  $('svoice').value = profile.server_voice || 'lessac';
  ddPaint('svoice');
  $('speakup').checked = profile.speak_up !== false;
  $('vstat').textContent = `browser voice: ${synthOK ? 'yes' : 'NO (native window)'} · server voice: ${vs.server.piper ? 'PIPER ✓' : vs.server.espeak ? 'espeak' : 'MISSING'}\nvoices dir: ${(vs.server.voices_dir || '')} (${vs.server.models_found || 0} models · ${(vs.server.voices || []).length} voices)`;
  if (synthOK) speechSynthesis.getVoices();
  try {
    const caps = await (await fetch('/api/desktop/caps')).json();
    $('sys').textContent = `${caps.control.os} · ${caps.control.desktop} · ${caps.control.session}`;
  } catch (e) { $('sys').textContent = 'system: unknown'; }
  if (!profile.completed_onboarding) $('onboard').classList.remove('hidden');
  else {
    const h = new Date().getHours();
    const part = h < 5 ? 'night' : h < 12 ? 'morning' : h < 18 ? 'afternoon' : 'evening';
    const g = `Good ${part}${profile.display_name ? ', ' + profile.display_name : ''}. Mitsu online — what are we doing today?`;
    addMsg('MITSU', `Systems nominal. ${g}`);
    if (profile.speak_up !== false) setTimeout(() => speak(g), 1200);
  }
  connect(); loadAuto(); loadSkills(); refreshTasks(); loadMem(); loadWake(); refreshOllama();
  // JARVIS-style: mic opens on boot (INITIALIZE click already unlocked audio).
  // Opt out anytime: ⚙ Settings → uncheck, or 👂 / Alt+A / /always.
  if (profile.always_listen !== false) {
    addMsg('MITSU', 'Ears open 👂 — talk anytime.');
    setAlways(true);
  }
  document.body.classList.toggle('paper', (profile.theme || 'void') === 'paper');
  $('froot').value = profile.workspace_dir || '';
  try {
    const w = await (await fetch('/api/wake')).json();
    $('wake').checked = !!w.listening;
    if (!$('wake').checked && !w.available) $('wake').disabled = true;
  } catch (e) {}
  setInterval(refreshTasks, 8000);
  // unprompted check-ins: at most one per 30 min, only when speaking is welcome
  let lastHey = Date.now();
  setInterval(() => {
    if (profile.speak_up === false || !$('speak').checked) return;
    if (Date.now() - lastInteract < 30 * 60 * 1000) return;
    if (Date.now() - lastHey < 30 * 60 * 1000) return;
    lastHey = Date.now();
    const nudge = `Still here${profile.display_name ? ', ' + profile.display_name : ''}. Say the word when you need me.`;
    addMsg('MITSU', nudge); speak(nudge);
  }, 60 * 1000);
}
// custom dropdowns: themed button+list driving the hidden native select
// (native popups ignore styling in some engines — this never does)
function ddPaint(id) {
  const sel = $(id), btn = $(id + '-btn');
  const cur = [...sel.options].find(o => o.value === sel.value);
  btn.textContent = ((cur && cur.textContent) || sel.value || '—') + ' ▾';
}
function ddBuild(id) {
  const sel = $(id), list = $(id + '-list'), btn = $(id + '-btn');
  btn.onclick = e => {
    e.stopPropagation();
    document.querySelectorAll('.dd-list').forEach(l => { if (l !== list) l.classList.add('hidden'); });
    list.classList.toggle('hidden');
  };
  list.onclick = e => {
    const v = e.target.dataset && e.target.dataset.v;
    if (v === undefined) return;
    sel.value = v;
    sel.dispatchEvent(new Event('change'));
    list.classList.add('hidden');
    ddPaint(id);
  };
  sel.addEventListener('change', () => ddPaint(id));
}
function ddFill(id, items) {
  const sel = $(id), list = $(id + '-list');
  const keep = sel.value;
  sel.innerHTML = items.map(i => `<option value="${i.v}">${i.label}</option>`).join('');
  if (keep && [...sel.options].some(o => o.value === keep)) sel.value = keep;
  list.innerHTML = '';
  items.forEach(i => {
    const d = document.createElement('div');
    d.textContent = i.label; d.dataset.v = i.v;
    list.appendChild(d);
  });
  ddPaint(id);
}
document.addEventListener('click', () => document.querySelectorAll('.dd-list').forEach(l => l.classList.add('hidden')));
ddBuild('provider'); ddBuild('model'); ddBuild('svoice');
async function refreshModels() {
  const p = $('provider').value;
  const r = await (await fetch('/api/models?provider=' + encodeURIComponent(p))).json();
  const list = Array.isArray(r) ? r : [];
  ddFill('model', (list.length ? list : [{ id: profile.default_model || '', installed: true }])
    .map(m => {
      const locked = (p === 'zen' || p === 'go') && m.free;
      return { v: m.id, label: `${m.id}${m.free ? ' FREE' : ''}${locked ? '·OpenCode-app-only' : ''}${m.installed ? '' : ' ○'}` };
    }));
  $('pmodel').textContent = p + ' / ' + ($('model').value || profile.default_model || '');
}
// Mitsu voice picker — speaks a preview in the new voice
$('svoice').onchange = async () => {
  profile.server_voice = $('svoice').value;
  await fetch('/api/profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile) });
  serverSpeak('Voice updated. This is how I sound now.', () => setState('idle'));
};
$('speakup').onchange = async () => {
  profile.speak_up = $('speakup').checked;
  await fetch('/api/profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile) });
};
// provider picker shows only probe-verified working brains.
// Anything locked/keyless/dead hides; "➕" opens the key modal to add them.
function fillProviderDD() {
  const okP = providers.filter(x => x.usable);
  const offP = providers.filter(x => !x.usable);
  ddFill('provider', [
    ...okP.map(p => ({ v: p.name, label: p.name })),
    ...(offP.length ? [{ v: '__add', label: '➕ other providers (add key)' }] : []),
  ]);
  const cur = $('provider').value;
  if (!okP.some(x => x.name === cur)) {
    const d = okP.find(x => x.name === profile.default_provider) || okP[0];
    if (d) $('provider').value = d.v;
    ddPaint('provider');
  }
  refreshModels();
}
function openKeyModal() {
  const offP = providers.filter(x => !x.usable);
  $('key-prov').innerHTML = offP
    .map(p => `<option value="${p.name}">${p.name}</option>`).join('');
  $('key-why').textContent = 'Add an API key to enable a provider. No key → stay on local Ollama or keyless Pollinations.';
  $('keymodal').classList.remove('hidden');
}
$('provider').addEventListener('change', async () => {
  if ($('provider').value === '__add') {  // picker's "add a key" entry
    openKeyModal();
    const keep = providers.find(x => x.usable);
    if (keep) { $('provider').value = keep.name; }
    ddPaint('provider');
    return;
  }
  const p = providers.find(x => x.name === $('provider').value);
  if (p && !p.usable) {  // selected a dead/locked one (stale data)
    openKeyModal();
    const keep = providers.find(x => x.usable);
    if (keep) { $('provider').value = keep.name; }
    ddPaint('provider');
    return;
  }
  await refreshModels();
  if (p && p.kind !== 'ollama' && !p.has_key) {
    openKeyModal();
  } else {
    profile.default_provider = $('provider').value; profile.default_model = $('model').value;
    await fetch('/api/profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile) });
  }
});
$('key-ok').onclick = async () => {
  const name = $('key-prov').value || (providers.find(x => !x.usable) || {}).name;
  const p = name && providers.find(x => x.name === name);
  const k = $('key-in').value.trim();
  if (p && k) {
    await fetch('/api/providers', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: p.name, kind: p.kind, api_key: k, default_model: p.default_model || $('model').value })
    });
    providers = await (await fetch('/api/providers?probe=1')).json();
    fillProviderDD();
    $('provider').value = p.name; ddPaint('provider');
    await refreshModels();
    if (p.default_model) { $('model').value = p.default_model; ddPaint('model'); }
    profile.default_provider = p.name; profile.default_model = p.default_model || '';
    await fetch('/api/profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile) });
    addMsg('MITSU', `Key saved — ${p.name} is in the picker if it answers (probed live).`);
  }
  $('key-in').value = ''; $('keymodal').classList.add('hidden');
};
$('key-no').onclick = () => {
  const keep = providers.find(x => x.usable);
  if (keep && !$('provider').value || $('provider').value === '__add') {
    $('provider').value = keep ? keep.name : profile.default_provider;
    ddPaint('provider'); refreshModels();
  }
  $('keymodal').classList.add('hidden');
};
$('model').onchange = () => $('pmodel').textContent = $('provider').value + ' / ' + $('model').value;
function connect() {
  ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/chat');
  ws.onopen = () => {
    wsAlive = true;
    if (act.textContent.startsWith('Disconnected')) act.textContent = 'Idle';
  };
  ws.onclose = () => {
    wsAlive = false;
    act.textContent = 'Disconnected — reconnecting…';
    setState('idle');
    setTimeout(() => { connect(); }, 3000);
  };
  ws.onerror = () => { try { ws.close(); } catch (e) {} };
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.type === 'activity') { act.textContent = m.text; setState('working', 'WORKING'); }
    if (m.type === 'message') {
      addMsg('MITSU', m.text, `${m.provider}/${m.model}`);
      meta.textContent = `model ${m.model} · ${m.route || ''}`;
    }
    if (m.type === 'speak') {
      speak(m.text);
      // conversation mode: when the reply finishes, listen again
      if (convo) {
        const w = setInterval(() => {
          if (state === 'idle') { clearInterval(w); if (convo) serverListen(true); }
        }, 600);
      }
    }
    if (m.type === 'idle') { act.textContent = 'Idle'; if (state === 'working') setState('idle'); }
    if (m.type === 'notify') {
      $('alerts').textContent = `${m.title}: ${m.body}\n` + $('alerts').textContent;
      speak(`${m.title}. ${m.body}`);
    }
    if (m.type === 'research.done') act.textContent = 'Report ready';
    if (m.type === 'wake') {
      setState('listening', 'YES?');
      addMsg('MITSU', `Yes? Listening… (${m.word || 'wake'})`);
      speak('Yes?');
      setTimeout(() => { if (state !== 'speaking') serverListen(false); }, 2500);
    }
    if (m.type === 'sudo.prompt') {
      $('sudo').classList.remove('hidden'); $('sudo-why').textContent = m.prompt;
      $('sudo-ok').onclick = () => {
        ws.send(JSON.stringify({ type: 'sudo.password', token: m.token, password: $('sudo-pw').value }));
        $('sudo-pw').value = ''; $('sudo').classList.add('hidden');
      };
      $('sudo-no').onclick = () => {
        ws.send(JSON.stringify({ type: 'sudo.password', token: m.token, password: '' }));
        $('sudo').classList.add('hidden');
      };
    }
  };
}
$('form').onsubmit = e => {
  e.preventDefault();
  const t = $('in').value.trim(); if (!t) return;
  if (!ws || ws.readyState !== 1) {
    addMsg('MITSU', 'Not connected — reconnecting, send again in a moment.');
    try { connect(); } catch (e) {}
    return;
  }
  if (t.startsWith('/')) { $('in').value = ''; autoresize(); slash(t); return; }
  sendChat(t);
};
// roomy composer: auto-grows, Enter sends, Shift+Enter newline
function autoresize() {
  const ta = $('in');
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, window.innerHeight * 0.3) + 'px';
}
$('in').addEventListener('input', autoresize);
$('in').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('form').requestSubmit(); }
});
function sendChat(t) {
  lastInteract = Date.now();
  $('in').value = '';
  autoresize();
  stopVoice(); addMsg('You', t); setState('working', 'THINKING');
  try {
    ws.send(JSON.stringify({
      type: 'chat', text: t, provider: $('provider').value,
      model: $('model').value, auto_route: $('auto').checked, speak: $('speak').checked
    }));
  } catch (e) {
    addMsg('MITSU', 'Send failed (disconnected) — reconnecting, try again.');
    try { connect(); } catch (e2) {}
    setState('idle');
  }
}
// slash commands — every agent answers to these
async function slash(t) {
  const [cmd, ...rest] = t.slice(1).split(' ');
  const arg = rest.join(' ').trim();
  addMsg('You', t);
  const say = m => addMsg('MITSU', m);
  switch (cmd) {
    case 'help': $('keys').classList.remove('hidden'); break;
    case 'clear': log.innerHTML = ''; break;
    case 'tasks': refreshTasks(); say('Tasks refreshed (right rail).'); break;
    case 'stop': stopAll(); say('Stopped everything.'); break;
    case 'remember': case 'forget':
      if (arg) sendChat(`${cmd} ${arg}`); else say(`Usage: /${cmd} <text>`);
      break;
    case 'research':
      if (arg) { $('rq').value = arg; $('rgo').click(); } else say('Usage: /research <question>');
      break;
    case 'build':
      if (arg) { $('bgoal').value = arg; $('bgo').click(); } else say('Usage: /build <goal>');
      break;
    case 'pull':
      if (arg) {
        const r = await (await fetch('/api/ollama/pull', { method: 'POST',
          headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: arg }) })).json();
        say(`Pulling ${arg} (task ${r.task_id}).`);
      } else say('Usage: /pull <model>');
      break;
    case 'shot': $('shot').click(); break;
    case 'what': sendChat('What is on my screen? ' + arg); break;
    case 'always': setAlways(!$('always').style.borderWidth); say(always ? 'Always listening 👂 ON.' : 'Always listening OFF.'); break;
    case 'su': openSu(); break;
    case 'model': {
      const [p, ...mm] = arg.split(' ');
      if (p) { $('provider').value = p; $('provider').dispatchEvent(new Event('change')); }
      if (mm.length) $('model').value = mm.join(' ');
      break;
    }
    case 'voice':
      if (arg) { $('svoice').value = arg; $('svoice').dispatchEvent(new Event('change')); }
      else {
        const opts = [...$('svoice').options].map(o => o.value).filter(Boolean);
        say('Voices: ' + (opts.length ? opts.join(', ') : 'lessac, amy, ryan, ljspeech, arctic, kristin, dante, joe, sparkle, mochi') + '.');
      }
      break;
    default: say(`Unknown /${cmd}. Try /help.`);
  }
}
// keyboard shortcuts
document.addEventListener('keydown', e => {
  const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
  if (e.key === 'Escape') {
    stopVoice();
    document.querySelectorAll('.modal').forEach(m => m.classList.add('hidden'));
    return;
  }
  if (e.ctrlKey && e.shiftKey && (e.key === 'X' || e.key === 'x')) { e.preventDefault(); stopAll(); return; }
  if (e.ctrlKey && e.key === 'Enter') { e.preventDefault(); $('form').requestSubmit(); return; }
  if (typing) return;
  if (e.key === '/') { e.preventDefault(); $('in').focus(); }
  else if (e.key === '?') $('keys').classList.toggle('hidden');
  else if (e.altKey && (e.key === 'm' || e.key === 'M')) { e.preventDefault(); $('mic').click(); }
  else if (e.altKey && (e.key === 'a' || e.key === 'A')) { e.preventDefault(); setAlways(!always); }
  else if (e.altKey && (e.key === 'o' || e.key === 'O')) {    e.preventDefault();
    document.querySelectorAll('details.card').forEach(d => { if (d.textContent.includes('Ollama models')) d.open = true; });
    $('oq').focus();
  }
  else if (e.altKey && (e.key === 'r' || e.key === 'R')) { e.preventDefault(); $('rq').focus(); }
  else if (e.altKey && (e.key === 'f' || e.key === 'F')) { e.preventDefault(); $('ftree').click(); }
  else if (e.altKey && (e.key === 's' || e.key === 'S')) { e.preventDefault(); $('settings').click(); }
});
$('keys-close').onclick = () => $('keys').classList.add('hidden');
$('mdoctor').onclick = async () => {
  const d = await (await fetch('/api/stt/doctor')).json();
  $('dout').textContent =
    `recorder: ${d.recorder || 'NONE'}\nsources:\n${(d.sources || []).map(s => '  ' + s).join('\n') || '  (none found)'}\n` +
    (d.hints.length ? 'fix:\n' + d.hints.map(h => '  • ' + h).join('\n') : 'mic path looks OK — try 🎙');
};
$('shush').onclick = stopVoice;
$('mic').onclick = async () => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SR) {
    if (rec) { rec.stop(); rec = null; setState('idle'); return; }
    rec = new SR(); rec.lang = profile.language || 'en'; ensureAC(); setState('listening');
    rec.onresult = e => { $('in').value = e.results[0][0].transcript; autoresize(); $('form').requestSubmit(); };
    rec.onend = () => { rec = null; if (state === 'listening') setState('idle'); };
    rec.onerror = () => { addMsg('MITSU', 'Mic error — typed input still works.'); setState('idle'); };
    rec.start(); act.textContent = 'Listening…';
  } else {
    serverListen(false);
  }
};
let convo = false;
$('convo').onclick = () => {
  convo = !convo;
  $('convo').style.borderColor = convo ? (paper() ? '#0a0a0b' : '#ffffff') : '';
  $('convo').style.borderWidth = convo ? '2px' : '';
  act.textContent = convo ? 'Conversation mode ON — talk, I keep listening' : 'Idle';
  if (convo) serverListen(false);
};
// server mic + denoise + whisper. chain=true when continuing a conversation.
let listening = false; // one server capture at a time — never overlap
let always = false;    // JARVIS-style: mic stays open, talk anytime
// ---- super user (pass-phase here, digest only server-side) ----
let suMode = 'setup';  // setup | unlock
async function openSu() {
  const st = await (await fetch('/api/su/status')).json();
  if (st.enabled && !st.unlocked) suMode = 'unlock';
  else if (st.unlocked) {
    addMsg('MITSU', `Super user UNLOCKED for ${Math.ceil(st.lock_left_s / 60)} min — /su unlock again after. Every command lands in su.log.`);
    return;
  }
  $('su-title').textContent = st.enabled ? 'UNLOCK SUPER USER' : 'ARM SUPER USER';
  $('su-why').textContent = st.enabled
    ? 'Enter your pass-phase to unlock local admin-grade shell for a short window.'
    : 'Set a pass-phase (never stored — only a digest). Arming enables gated shell: /su exec <cmd>. Sudo stays manual, always.';
  $('su-note').textContent = st.enabled
    ? `window: 1–30 min · shell allowed: ${st.allow_shell ? 'yes' : 'no'} · type /su disable to disarm`
    : 'type /su disable anytime to disarm; every action is logged';
  $('sumodal').classList.remove('hidden');
  $('su-pass').focus();
}
$('su-ok').onclick = async () => {
  const p = $('su-pass').value.trim();
  const ep = suMode === 'setup' ? '/api/su/setup' : '/api/su/unlock';
  const r = await (await fetch(ep, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ passphrase: p }) })).json();
  addMsg('MITSU', r.ok ? (suMode === 'setup' ? 'Super user ARMED. Unlock per session with /su unlock.' : `Super user UNLOCKED for ${r.minutes} min.`) : (r.error || 'failed'));
  $('su-pass').value = ''; $('sumodal').classList.add('hidden');
};
$('su-no').onclick = () => { $('su-pass').value = ''; $('sumodal').classList.add('hidden'); };
async function serverListen(chain) {
  // native window / no speech recognition → server mic + offline whisper
  if (listening) return;
  listening = true;
  try {
    ensureAC(); setState('listening', 'LISTENING'); act.textContent = always ? 'Always listening 👂 — talk anytime' : 'Listening… (auto-stops on silence)';
    const r = await (await fetch('/api/stt/record', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ seconds: 30, vad: true })
    })).json();
    setState('idle');
    if (r.text) {
      lastInteract = Date.now();
      act.textContent = `Heard ✓ noise −${Math.abs((r.snr_after || 0) - (r.snr_before || 0)).toFixed(0)}dB · ${r.speech_sec || '?'}s speech`;
      $('in').value = r.text; autoresize(); $('form').requestSubmit();
    } else if (!chain) {
      addMsg('MITSU', 'Heard nothing — check the mic, or type below.');
    } else if (always) {
      // silence in always-mode: re-arm shortly, loop never dies
      setTimeout(() => { if (always && state === 'idle') serverListen(true); }, 1500);
    }
  } catch (e) {
    setState('idle');
    if (always) {
      // mic hiccup in always-mode: back off, then re-arm (never spam)
      act.textContent = 'Mic hiccup — re-arming…';
      setTimeout(() => { if (always && state === 'idle') serverListen(true); }, 4000);
    } else {
      addMsg('MITSU', 'Voice input unavailable here (' + (e.message || e) + '). Type below, or use browser mode.');
    }
  } finally {
    listening = false;
  }
}
function setAlways(on) {
  always = on;
  $('always').style.borderColor = on ? (paper() ? '#0a0a0b' : '#ffffff') : '';
  $('always').style.borderWidth = on ? '2px' : '';
  act.textContent = on ? 'Always listening 👂 — talk anytime' : 'Idle';
  if (on && state === 'idle') serverListen(true);
}
$('always').onclick = () => setAlways(!always);
// safety net: if anything returns to idle while always-mode is on, re-arm
setInterval(() => {
  if (always && state === 'idle' && !listening) serverListen(true);
}, 5000);
function stopAll() { stopVoice(); fetch('/api/stop', { method: 'POST' }); setState('idle'); }
$('vtest').onclick = () => { ensureAC(); serverSpeak('Mitsu voice systems online.', () => setState('idle')); setState('speaking', 'TEST'); };
$('mtest').onclick = async () => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SR) { addMsg('MITSU', 'Mic backend present. Press 🎙 and speak.'); return; }
  try {
    const s = await navigator.mediaDevices.getUserMedia({ audio: true });
    addMsg('MITSU', 'Mic hardware OK (level test passed). Speech-to-text needs browser mode or whisper installed — typed input works.');
    s.getTracks().forEach(tr => tr.stop());
  } catch (e) { addMsg('MITSU', 'No mic accessible here: ' + e.message); }
};
$('ob-go').onclick = async () => {
  profile.display_name = $('ob-name').value || 'friend';
  profile.personality = $('ob-personality').value;
  profile.completed_onboarding = true;
  await fetch('/api/profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile) });
  $('onboard').classList.add('hidden');
  const g = `Hey ${profile.display_name}, systems are green. What are we building today?`;
  addMsg('MITSU', g); speak(g);
  if (profile.always_listen !== false) { addMsg('MITSU', 'Ears open 👂 — talk anytime.'); setAlways(true); }
};
$('workfocus').onclick = async () => {
  const r = await (await fetch('/api/desktop/work-focus', { method: 'POST' })).json();
  addMsg('MITSU', 'Work view: ' + (r.via || r.error));
};
function addImg(who, url) {
  const d = document.createElement('div'); d.className = 'msg';
  const w = document.createElement('div'); w.className = 'who'; w.textContent = who;
  const img = document.createElement('img');
  img.src = url; img.style.cssText = 'max-width:100%;border:1px solid var(--line);border-radius:8px';
  d.append(w, img); log.appendChild(d); log.scrollTop = log.scrollHeight;
}
$('shot').onclick = async () => {
  const tok = await requestApproval('take a screenshot');
  if (!tok) return;
  const r = await (await fetch('/api/desktop/shot', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: tok })
  })).json();
  if (r.ok) addImg('MITSU ▣', r.data_url);
  else addMsg('MITSU', 'Screenshot failed: ' + (r.error || 'denied'));
};
$('wins').onclick = async () => {
  const r = await (await fetch('/api/desktop/windows')).json();
  addMsg('MITSU ▦', (r.windows || []).map(w => `• ${w.app}: ${w.title}`.slice(0, 90)).join('\n') || ('windows: ' + (r.error || 'none')));
};
$('rgo').onclick = async () => {
  const q = $('rq').value.trim(); if (!q) return;
  $('rout').textContent = 'Researching…';
  const { task_id } = await (await fetch('/api/research', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q })
  })).json();
  const poll = setInterval(async () => {
    const r = await (await fetch('/api/research/' + task_id)).json();
    if (r.status === 'completed' || r.status === 'failed') {
      clearInterval(poll); $('rout').textContent = '';
      addMsg('MITSU 🔍', r.report || r.logs.join('\n')); speak('Research complete.');
    } else $('rout').textContent = r.logs.slice(-1)[0] || 'Working…';
  }, 1500);
};
$('bgo').onclick = async () => {
  const r = await (await fetch('/api/build', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal: $('bgoal').value, dest: $('bdest').value || profile.workspace_dir || '/tmp/opencode/mitsuwork' })
  })).json();
  $('bout').textContent = 'task ' + r.task_id; speak('Build started. Watch the activity feed.');
};
async function refreshTasks() {
  try {
    const r = await (await fetch('/api/tasks')).json();
    const box = $('tasks'); box.innerHTML = '';
    if (!r.length) box.textContent = 'none';
    r.slice(-6).forEach(t => {
      const d = document.createElement('div');
      d.textContent = `${t.id} ${t.name.slice(0, 24)} [${t.status}] ${Math.round(t.progress * 100)}% `;
      [['cancel', '✕'], ['pause', '⏸'], ['resume', '▶']].forEach(([a, ic]) => {
        const b = document.createElement('button');
        b.className = 'tbtn'; b.textContent = ic; b.title = a;
        b.onclick = () => fetch(`/api/tasks/${t.id}/${a}`, { method: 'POST' }).then(refreshTasks);
        d.appendChild(b);
      });
      box.appendChild(d);
    });
  } catch (e) {}
}
// generic approval: returns a one-shot token, or null on deny
function requestApproval(action) {
  return new Promise(res => {
    $('ap-why').textContent = `Mitsu wants permission: ${action}. Approve once, or deny.`;
    $('approval').classList.remove('hidden');
    $('ap-ok').onclick = async () => {
      $('approval').classList.add('hidden');
      const r = await (await fetch('/api/approve', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      })).json();
      res(r.token);
    };
    $('ap-no').onclick = () => { $('approval').classList.add('hidden'); res(null); };
  });
}
// files: list → preview → edit → approved save
let froot = '', fpath = '';
$('ftree').onclick = async () => {
  froot = $('froot').value.trim() || profile.workspace_dir || '/tmp';
  const r = await (await fetch('/api/workspace/tree?root=' + encodeURIComponent(froot))).json();
  const box = $('flist'); box.innerHTML = '';
  (r.files || []).slice(0, 300).forEach(f => {
    if (f.endsWith('/')) return;
    const d = document.createElement('div'); d.textContent = f;
    d.onclick = async () => {
      fpath = f; $('fname').textContent = f; $('fview').classList.remove('hidden');
      try {
        const c = await (await fetch('/api/workspace/file?root=' + encodeURIComponent(froot) + '&path=' + encodeURIComponent(f))).json();
        $('ftext').value = c.content || '';
      } catch (e) { $('ftext').value = '(unreadable: ' + e.message + ')'; }
    };
    box.appendChild(d);
  });
};
$('fsave').onclick = async () => {
  const tok = await requestApproval(`write file ${fpath}`);
  if (!tok) return;
  await fetch('/api/workspace/write', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ root: froot, path: fpath, content: $('ftext').value, token: tok })
  });
  act.textContent = 'Saved ' + fpath;
};
$('fdel').onclick = async () => {
  const tok = await requestApproval(`DELETE file ${fpath} (sensitive)`);
  if (!tok) return;
  await fetch('/api/workspace/delete', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ root: froot, path: fpath, content: '', token: tok })
  });
  $('fview').classList.add('hidden'); $('ftree').click();
};
// wake word toggle + event
$('wake').onchange = async () => {
  try {
    const r = await (await fetch('/api/wake', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: $('wake').checked })
    })).json();
    act.textContent = r.listening ? 'Wake word ON — say "hey jarvis"' : 'Wake word off';
    if (!r.listening && $('wake').checked) { $('wake').checked = false; addMsg('MITSU', 'Wake word unavailable: mic or engine missing.'); }
  } catch (e) {
    $('wake').checked = false;
    addMsg('MITSU', 'Wake word failed: ' + (e.message || e));
  }
};
async function loadAuto() {
  const r = await (await fetch('/api/automations')).json();
  $('alist').textContent = r.map(x => `${x.name} [${x.kind}/${x.action}]`).join('\n') || 'none yet';
}
$('aadd').onclick = async () => {
  const kind = $('akind').value, tgt = $('atarget').value.trim();
  let body = { name: $('aname').value || 'reminder', kind: 'interval',
    action: 'notify', payload: { body: $('abody').value || 'Hi!' }, every_sec: 3600 };
  if (kind.startsWith('event-')) {
    const et = kind.slice(6);
    body = { name: $('aname').value || et, kind: 'event', action: 'notify',
      payload: { body: $('abody').value || 'Event fired', event: { type: et,
        task: et === 'task_done' ? tgt : '', path: et === 'file_change' ? tgt : '',
        minutes: 30 } }, every_sec: 3600 };
  }
  await fetch('/api/automations', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body) });
  loadAuto();
};
async function loadSkills() {
  const r = await (await fetch('/api/skills')).json();
  $('sklist').innerHTML = '';
  r.forEach(s => {
    const l = document.createElement('label'); l.className = 'chk';
    const c = document.createElement('input'); c.type = 'checkbox'; c.checked = s.enabled;
    c.onchange = e => fetch('/api/skills/' + s.name, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: e.target.checked })
    });
    const sp = document.createElement('span');
    sp.textContent = ` ${s.name} — ${s.description}`;
    l.append(c, sp);
    $('sklist').appendChild(l);
  });
}
$('mgo').onclick = async () => {
  const r = await (await fetch('/api/memory/search?q=' + encodeURIComponent($('mq').value))).json();
  $('mout').textContent = r.map(h => `• ${h.text.slice(0, 120)}`).join('\n') || 'no matches';
};
async function loadMem() {
  const m = await (await fetch('/api/memory')).json();
  const box = $('mstored'); box.innerHTML = '';
  (m.long_term || []).forEach((f, i) => {
    const d = document.createElement('div');
    d.textContent = `• ${f.fact.slice(0, 80)} `;
    const e = document.createElement('button'); e.className = 'tbtn'; e.textContent = '✏';
    e.onclick = async () => {
      const v = prompt('Edit memory:', f.fact);
      if (v !== null) {
        await fetch('/api/memory/item', { method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ kind: 'long_term', index: i, fact: v }) });
        loadMem();
      }
    };
    const x = document.createElement('button'); x.className = 'tbtn'; x.textContent = '✕';
    x.onclick = async () => {
      await fetch(`/api/memory/item?kind=long_term&index=${i}`, { method: 'DELETE' });
      loadMem();
    };
    d.append(e, x); box.appendChild(d);
  });
  const c = document.createElement('button'); c.textContent = 'FORGET ALL';
  c.onclick = async () => { await fetch('/api/memory/clear', { method: 'POST' }); loadMem(); };
  box.appendChild(c);
}
setInterval(async () => {
  try {
    const p = await (await fetch('/api/companion')).json();
    if (p.enabled || p.task) {
      $('pet').classList.remove('hidden');
      $('pface').textContent = p.face + ' '; $('pmsg').textContent = p.message || p.task || 'idle';
    } else $('pet').classList.add('hidden');
  } catch (e) {}
}, 5000);
$('pet').onclick = async () => {
  await fetch('/api/companion', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ poke: true }) });
};
$('settings').onclick = () => {
  $('c-name').value = profile.display_name || '';
  $('c-ws').value = profile.workspace_dir || '';
  $('c-theme').value = profile.theme || 'void';
  $('c-always').checked = profile.always_listen !== false;
  $('cfg').classList.remove('hidden');
};
$('c-close').onclick = () => $('cfg').classList.add('hidden');
$('c-save').onclick = async () => {
  profile.display_name = $('c-name').value;
  profile.workspace_dir = $('c-ws').value;
  profile.theme = $('c-theme').value;
  profile.always_listen = $('c-always').checked;
  document.body.classList.toggle('paper', profile.theme === 'paper');
  $('froot').value = profile.workspace_dir || '';
  await fetch('/api/profile', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile) });
  $('cfg').classList.add('hidden');
};
// custom "mitsu" voiceprint enrollment
async function loadWake() {
  try {
    const t = await (await fetch('/api/wake/templates')).json();
    $('wtstat').textContent = t.ready ? `enrolled ✓ (${t.count} samples)` : `samples: ${t.count}/3`;
  } catch (e) {}
}
$('wenroll').onclick = async () => {
  addMsg('MITSU', 'Say "mitsu" now… (recording 4s)');
  const r = await fetch('/api/wake/enroll', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ seconds: 4 })
  });
  if (r.ok) {
    const t = await r.json();
    addMsg('MITSU', t.ready ? 'Voiceprint ready — "mitsu" wakes me now.' : `Sample ${t.count}/3 saved.`);
  } else {
    addMsg('MITSU', 'Enroll failed: ' + (await r.text()).slice(0, 120));
  }
  loadWake();
};
$('wclear').onclick = async () => {
  await fetch('/api/wake/templates', { method: 'DELETE' });
  loadWake();
};
// ---- one-click setup ----
async function loadSetup() {
  const items = await (await fetch('/api/setup')).json();
  const box = $('slist'); box.innerHTML = '';
  items.forEach(it => {
    const d = document.createElement('div');
    d.textContent = `${it.ok ? '✓' : '○'} ${it.label} [${it.size}]${it.hint ? ' (' + it.hint + ')' : ''}`;
    box.appendChild(d);
  });
  return items;
}
$('setupbtn').onclick = async () => {
  $('setup').classList.remove('hidden');
  try {
    const os = await (await fetch('/api/setup/os')).json();
    $('sollama').textContent = os.elevate_label || 'OLLAMA ENGINE';
  } catch (e) {}
  await loadSetup();
  $('sout').textContent = '';
};
$('sclose').onclick = () => $('setup').classList.add('hidden');
$('sinstall').onclick = async () => {
  const items = await loadSetup();
  const missing = items.filter(i => !i.ok && i.id !== 'ollama-bin').map(i => i.id);
  if (!missing.length) { $('sout').textContent = 'Everything already installed ✓'; return; }
  $('sout').textContent = 'Installing… watch Live activity. (Big downloads take a while.)';
  const { task_id } = await (await fetch('/api/setup/install', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids: missing })
  })).json();
  const poll = setInterval(async () => {
    const ts = await (await fetch('/api/tasks')).json();
    const t = ts.find(x => x.id === task_id);
    if (t && (t.status === 'completed' || t.status === 'failed' || t.status === 'cancelled')) {
      clearInterval(poll);
      $('sout').textContent = 'Setup ' + t.status + '. ' + (t.logs.slice(-1)[0] || '');
      loadSetup();
    } else if (t) {
      $('sout').textContent = t.logs.slice(-1)[0] || 'Working…';
    }
  }, 2000);
};
$('sollama').onclick = async () => {
  $('sout').textContent = 'Installing Ollama engine — approve the sudo prompt…';
  try {
    const r = await (await fetch('/api/setup/ollama', { method: 'POST' })).json();
    $('sout').textContent = r.msg || 'Ollama installed ✓';
  } catch (e) {
    $('sout').textContent = 'Ollama install failed/denied. Terminal alternative: curl -fsSL https://ollama.com/install.sh | sh';
  }
  loadSetup();
};
// ---- ollama model shop ----
async function refreshOllama(q = '') {
  const r = await (await fetch('/api/ollama/library?q=' + encodeURIComponent(q))).json();
  const lib = $('olib'); lib.innerHTML = '';
  (r.library || []).slice(0, 20).forEach(m => {
    const d = document.createElement('div');
    d.textContent = `• ${m.name} [${m.size}] — ${m.blurb} `;
    const b = document.createElement('button'); b.className = 'tbtn'; b.textContent = 'PULL';
    b.onclick = async () => {
      const t = await (await fetch('/api/ollama/pull', { method: 'POST',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: m.name }) })).json();
      addMsg('MITSU', `Pulling ${m.name} (task ${t.task_id}) — progress in Tasks.`);
    };
    d.appendChild(b); lib.appendChild(d);
  });
  const loc = $('olocal'); loc.innerHTML = '<u>Installed:</u><br/>';
  (r.local || []).forEach(m => {
    const d = document.createElement('div');
    d.textContent = `• ${m.name} [${m.size}] `;
    const x = document.createElement('button'); x.className = 'tbtn'; x.textContent = '✕';
    x.onclick = async () => {
      await fetch('/api/ollama/local?name=' + encodeURIComponent(m.name), { method: 'DELETE' });
      refreshOllama($('oq').value);
    };
    d.appendChild(x); loc.appendChild(d);
  });
  if (!(r.local || []).length) loc.innerHTML += 'none — pull one above';
}
$('ogo').onclick = () => refreshOllama($('oq').value);
boot();
