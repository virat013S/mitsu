"""Detached desktop companion window (§15): `mitsu pet`.

Selectable characters (all original, canvas-drawn — no external assets):
animals: neko (cat), panda, kitsune (fox). anime: hoshi (star mage),
kaito (scarf swordsman). Moods drive expressions; the buddy wanders, naps,
celebrates finished tasks, and sulks on errors. Modes: overlay (always on
top), windowed, hidden. Click to poke.
"""
from __future__ import annotations

import urllib.request

HTML = """<!doctype html><html><head><meta charset="utf-8">
<style>
body{margin:0;background:#000;color:#f4f4f5;font:12px system-ui;user-select:none}
#bar{display:flex;gap:4px;padding:6px;flex-wrap:wrap;justify-content:center}
button{background:#111;color:#f4f4f5;border:1px solid #333;border-radius:6px;padding:3px 8px;cursor:pointer;font-size:11px}
button.on{border-color:#f4f4f5}
#cv{display:block;margin:0 auto;cursor:pointer}
#msg{text-align:center;opacity:.75;min-height:30px;padding:0 8px}
#prog{height:4px;background:#222;margin:4px 10px;border-radius:2px}
#prog div{height:100%;background:#f4f4f5;border-radius:2px;width:0%}
</style></head><body>
<div id="bar"></div>
<canvas id="cv" width="260" height="240"></canvas>
<div id="prog"><div></div></div>
<div id="msg">…</div>
<div id="bar2" style="display:flex;gap:4px;padding:6px;justify-content:center">
<button id="m-hide">HIDE (close me, server keeps running)</button>
</div>
<script>
let char = localStorage.getItem('pet') || 'neko';
let mood = 'idle', msg = '', task = '', prog = 0, lastDone = '';
let x = 130, dir = 1, vy = 0, y = 0, happy = 0, blink = 0, nap = 0, confetti = [];
const cv = document.getElementById('cv'), c = cv.getContext('2d');
const CHARS = ['neko', 'panda', 'kitsune', 'hoshi', 'kaito'];
const NAMES = { neko: '🐈 Neko', panda: '🐼 Panda', kitsune: '🦊 Kitsune', hoshi: '✦ Hoshi', kaito: '🧣 Kaito' };
function bar() {
  const b = document.getElementById('bar'); b.innerHTML = '';
  CHARS.forEach(k => {
    const btn = document.createElement('button');
    btn.textContent = NAMES[k]; if (k === char) btn.className = 'on';
    btn.onclick = () => { char = k; localStorage.setItem('pet', k); bar(); };
    b.appendChild(btn);
  });
}
bar();
function eyes(m, bx, by, s, bl) {
  c.fillStyle = '#111';
  if (mood === 'sleeping' || nap > 0) {
    c.fillRect(bx - 9 * s, by, 14 * s, 2.5 * s); c.fillRect(bx + 5 * s, by, 14 * s, 2.5 * s);
  } else if (mood === 'happy' || mood === 'excited' || happy > 0) {
    c.beginPath(); c.arc(bx - 7 * s, by + 2 * s, 5 * s, Math.PI, 0); c.fill();
    c.beginPath(); c.arc(bx + 7 * s, by + 2 * s, 5 * s, Math.PI, 0); c.fill();
  } else if (bl) {
    c.fillRect(bx - 9 * s, by, 12 * s, 2.5 * s); c.fillRect(bx + 4 * s, by, 12 * s, 2.5 * s);
  } else {
    c.beginPath(); c.arc(bx - 6 * s, by, 3.4 * s, 0, 7); c.fill();
    c.beginPath(); c.arc(bx + 6 * s, by, 3.4 * s, 0, 7); c.fill();
  }
  if (mood === 'confused') {
    c.fillStyle = '#f4f4f5'; c.font = `${18 * s}px sans-serif`;
    c.fillText('?', bx + 20 * s, by - 12 * s);
  }
}
function draw(t) {
  c.clearRect(0, 0, 260, 240);
  const s = 2.2, gy = 200 - y;
  const bounce = (mood === 'excited' || happy > 0) ? Math.abs(Math.sin(t * 10)) * 12 : Math.sin(t * 2) * 2;
  const by = gy - 34 * s / 2 - bounce * .4 + (nap > 0 ? 14 : 0);
  const bx = x;
  c.save(); c.translate(bx, by); c.scale(s, s);
  // tails
  if (char === 'neko' || char === 'kitsune') {
    c.strokeStyle = char === 'neko' ? '#3a3a40' : '#e07b2a'; c.lineWidth = 4; c.lineCap = 'round';
    c.beginPath(); c.moveTo(10, 8);
    c.quadraticCurveTo(24, 4 + Math.sin(t * 3) * 5, 20, -10); c.stroke();
  }
  // ears
  const ear = char === 'panda' ? '#222' : char === 'kitsune' ? '#e07b2a' : char === 'neko' ? '#3a3a40' : null;
  if (ear) {
    c.fillStyle = ear;
    c.beginPath(); c.moveTo(-14, -8); c.lineTo(-10, -20); c.lineTo(-3, -10); c.fill();
    c.beginPath(); c.moveTo(14, -8); c.lineTo(10, -20); c.lineTo(3, -10); c.fill();
  }
  if (char === 'hoshi') { // star mage hood/hair
    c.fillStyle = '#2b3a67';
    c.beginPath(); c.arc(0, -4, 17, Math.PI * .9, Math.PI * 2.1); c.fill();
    c.fillStyle = '#ffd94d';
    c.save(); c.translate(12, -18); c.rotate(t); c.fillRect(-1.5, -5, 3, 10); c.fillRect(-5, -1.5, 10, 3); c.restore();
  }
  if (char === 'kaito') { // spiky hair + scarf
    c.fillStyle = '#1c1c20';
    for (let i = -3; i <= 3; i++) {
      c.beginPath(); c.moveTo(i * 5 - 2, -10); c.lineTo(i * 5, -22 - (i % 2) * 4); c.lineTo(i * 5 + 3, -10); c.fill();
    }
    c.strokeStyle = '#b3232a'; c.lineWidth = 4;
    c.beginPath(); c.moveTo(-8, 10); c.quadraticCurveTo(-20, 14 + Math.sin(t * 4) * 3, -26, 10); c.stroke();
  }
  // head
  const skin = { neko: '#55555c', panda: '#f0f0f2', kitsune: '#eda24a', hoshi: '#f6cfae', kaito: '#f0c8a8' }[char];
  c.fillStyle = skin;
  c.beginPath(); c.arc(0, 0, 15, 0, 7); c.fill();
  if (char === 'panda') {
    c.fillStyle = '#222';
    c.beginPath(); c.ellipse(-6, 0, 4, 5.5, .3, 0, 7); c.fill();
    c.beginPath(); c.ellipse(6, 0, 4, 5.5, -.3, 0, 7); c.fill();
  }
  if (char === 'neko') { // whiskers
    c.strokeStyle = '#888'; c.lineWidth = .8;
    [-1, 1].forEach(sg => { for (let i = 0; i < 3; i++) {
      c.beginPath(); c.moveTo(sg * 8, -1 + i * 3); c.lineTo(sg * 20, -3 + i * 4); c.stroke(); } });
  }
  eyes(mood, 0, 0, 1, blink);
  // mouth
  c.strokeStyle = '#111'; c.lineWidth = 1.2;
  c.beginPath();
  if (mood === 'happy' || mood === 'excited' || happy > 0) { c.arc(0, 6, 4, .3, Math.PI - .3); }
  else if (mood === 'sleeping' || nap > 0) { c.moveTo(-2, 7); c.lineTo(2, 7); }
  else { c.arc(0, 8, 2.5, Math.PI + .5, -0.5); }
  c.stroke();
  // body
  c.fillStyle = skin === '#f0f0f2' && char === 'panda' ? '#f0f0f2' : skin;
  c.globalAlpha = .95;
  c.beginPath(); c.ellipse(0, 24, 10, 9, 0, 0, 7); c.fill();
  c.globalAlpha = 1;
  if (mood === 'working') { // laptop
    c.fillStyle = '#0a0a0c'; c.strokeStyle = '#888'; c.lineWidth = 1;
    c.fillRect(-14, 20, 28, 12); c.strokeRect(-14, 20, 28, 12);
    c.fillStyle = '#9adcff'; c.fillRect(-12, 22, 24, 2);
  }
  c.restore();
  // shadow
  c.fillStyle = 'rgba(255,255,255,.12)';
  c.beginPath(); c.ellipse(bx, 202, 20 - y * .2, 5, 0, 0, 7); c.fill();
  if (nap > 0 || mood === 'sleeping') {
    c.fillStyle = '#8e8e96'; c.font = '14px sans-serif';
    c.fillText('z', bx + 24, 150 - ((t * 20) % 30)); c.fillText('Z', bx + 32, 140 - ((t * 20) % 30));
  }
  // confetti
  confetti = confetti.filter(p => p.y < 240);
  confetti.forEach(p => {
    p.y += p.v; p.x += Math.sin(t * 5 + p.y / 9) * 1.2;
    c.fillStyle = p.c; c.fillRect(p.x, p.y, 3, 3);
  });
}
function loop(t) {
  t /= 1000;
  // wander (not while napping/working)
  if (mood !== 'working' && nap === 0) {
    x += dir * .35;
    if (x > 220 || x < 40) dir *= -1;
  }
  if (vy !== 0 || y > 0) { y += vy; vy -= 1.2; if (y <= 0) { y = 0; vy = 0; } }
  if (happy > 0) happy -= .016;
  blink = (Math.sin(t * .7) > .985) ? 1 : 0;
  // nap when idle a while
  nap = (mood === 'idle' && Date.now() - lastAct > 90000) || mood === 'sleeping' ? 1 : 0;
  draw(t);
  requestAnimationFrame(loop);
}
let lastAct = Date.now();
async function tick() {
  try {
    const p = await (await fetch('BASE/api/companion')).json();
    mood = p.mood || 'idle'; msg = p.message || p.task || 'idle';
    task = p.task || ''; prog = p.progress || 0;
    document.getElementById('msg').textContent = msg;
    document.querySelector('#prog div').style.width = (prog * 100) + '%';
    const ts = await (await fetch('BASE/api/tasks')).json();
    const done = ts.filter(t => t.status === 'completed' || t.status === 'failed');
    const newest = done.length ? done[done.length - 1].id : '';
    if (newest && newest !== lastDone) {
      lastDone = newest;
      const st = done[done.length - 1].status;
      mood = st === 'completed' ? 'excited' : 'confused'; happy = 3;
      if (st === 'completed') for (let i = 0; i < 60; i++)
        confetti.push({ x: 30 + Math.random() * 200, y: -10 - Math.random() * 40, v: 1 + Math.random() * 2, c: ['#fff', '#ffd94d', '#9adcff'][i % 3] });
      lastAct = Date.now();
    }
    if (mood === 'working') lastAct = Date.now();
  } catch (e) {}
}
cv.onclick = async () => {
  vy = 9; happy = 3; lastAct = Date.now();
  try { await fetch('BASE/api/companion', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ poke: true }) }); } catch (e) {}
};
setInterval(tick, 2000); tick();
requestAnimationFrame(loop);
document.getElementById('m-hide').onclick = () => window.close();
</script></body></html>"""


def open_pet(host: str = "127.0.0.1", port: int = 8765, windowed: bool = False) -> None:
    """windowed=False → overlay (frameless, always on top).
    windowed=True → normal desktop window (lives on the desktop layer)."""
    try:
        import webview  # type: ignore
    except ImportError as e:
        raise RuntimeError("pet needs pywebview (install.sh --native)") from e
    base = f"http://{host}:{port}"
    try:
        urllib.request.urlopen(base + "/api/health", timeout=5)
    except Exception as e:
        raise RuntimeError(f"Mitsu server not running at {base} — start `mitsu` first") from e
    html = HTML.replace("BASE", base)
    webview.create_window("Mitsu", html=html, width=300, height=460,
                          frameless=not windowed, on_top=not windowed,
                          background_color="#000000")
    webview.start(debug=False)
