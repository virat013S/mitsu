"""FastAPI server: REST + WebSocket, serves ui/ (§23). No secrets ever returned."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..brain.chat import reply
from ..core.paths import APP_HOST, APP_PORT
from ..brain.memory.store import MemoryStore
from ..permissions import policy
from ..permissions.sudo import ensure_elevated, plan_privilege
from ..core.profile import UserProfile
from ..providers.registry import configured_providers, get_provider, list_configured, save_provider
from ..providers.secrets import delete_key, has_key, save_key
from ..tasks.manager import TaskManager
from ..voice.tts import BrowserTTS, VoiceSpec

def _ui_dir() -> Path:
    import sys as _sys
    cands = []
    if getattr(_sys, "frozen", False):
        base = Path(getattr(_sys, "_MEIPASS", "")) if hasattr(_sys, "_MEIPASS") else None
        if base:
            cands += [base / "ui", base.parent / "ui"]
        cands.append(Path(_sys.executable).resolve().parent / "ui")
    cands.append(Path(__file__).resolve().parent.parent.parent / "ui")
    for c in cands:
        if c and (c / "index.html").exists():
            return c
    return cands[-1]


UI_DIR = _ui_dir()
app = FastAPI(title="Mitsu")
tasks = TaskManager()
_profile = UserProfile.load()
_mem = MemoryStore.load()
_sudo_password_provider = None  # set when UI connects (masked field flow)


class ChatIn(BaseModel):
    text: str
    provider: str | None = None
    model: str | None = None
    auto_route: bool = True
    speak: bool = True


class ProfileIn(BaseModel):
    display_name: str = ""
    voice: str = "default"
    server_voice: str = "lessac"
    speak_up: bool = True
    language: str = "en"
    speech_rate: int = 175
    personality: str = "friendly"
    theme: str = "dark"
    default_provider: str = "ollama"
    default_model: str = "gemma3:1b"
    notifications: bool = True
    workspace_dir: str = ""


class ProviderIn(BaseModel):
    name: str
    kind: str
    base_url: str = ""
    api_key: str = ""
    default_model: str = ""


@app.get("/api/health")
async def health():
    online, ollama_ok = False, False
    try:
        import httpx as _hx
        async with _hx.AsyncClient(timeout=5) as _c:
            _r = await _c.get("https://1.1.1.1")
            online = _r.status_code < 500
    except Exception:
        online = False
    try:
        from ..providers.builtin import OllamaProvider
        ollama_ok = await OllamaProvider().health()
    except Exception:
        pass
    return {"ok": True, "mode": "ONLINE" if online else "OFFLINE — LOCAL MODE",
            "online": online, "ollama": ollama_ok,
            "onboarding": not _profile.completed_onboarding}


@app.get("/api/profile")
async def get_profile():
    return _profile.__dict__


@app.post("/api/profile")
async def set_profile(p: ProfileIn):
    global _profile
    for k, v in p.model_dump().items():
        setattr(_profile, k, v)
    _profile.completed_onboarding = True
    _profile.save()
    return _profile.__dict__


@app.get("/api/providers")
async def providers(probe: int = 0):
    """probe=1 → verify each provider with one tiny real request;
    usable=False (locked/no key/dead) is filtered out in the picker."""
    from ..providers.registry import list_configured, usable_providers
    if probe:
        return await usable_providers()
    return list_configured()


@app.get("/api/defaults")
async def smart_defaults():
    """Resolved public default (auto → ollama-if-present else keyless cloud)."""
    from ..providers.registry import smart_default
    return smart_default()


@app.post("/api/providers")
async def upsert_provider(p: ProviderIn):
    save_provider(p.name, {"kind": p.kind, "base_url": p.base_url,
                           "default_model": p.default_model})
    if p.api_key:
        save_key(p.name, p.api_key)
    from ..providers.registry import clear_probe
    clear_probe(p.name)  # re-probe on next picker load
    return {"ok": True}


@app.delete("/api/providers/{name}/key")
async def del_key(name: str):
    delete_key(name)
    return {"ok": True}


@app.get("/api/models")
async def models(provider: str):
    try:
        ms = await get_provider(provider).list_models()
        return [{"id": m.id, "name": m.name, "installed": m.installed,
                 "free": m.free} for m in ms]
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/memory")
async def get_memory():
    return {"short": _mem.short[-20:], "project": _mem.project, "long_term": _mem.long_term}


@app.post("/api/memory/clear")
async def clear_memory():
    _mem.forget_all()
    return {"ok": True}


class MemItemIn(BaseModel):
    kind: str = "long_term"  # long_term | project-key delete
    index: int = -1
    fact: str = ""  # new text for edit; empty + index = delete
    key: str = ""  # project dict key to delete


@app.put("/api/memory/item")
async def memory_edit(m: MemItemIn):
    if m.kind == "long_term" and 0 <= m.index < len(_mem.long_term):
        if m.fact:
            _mem.long_term[m.index]["fact"] = m.fact
        else:
            _mem.long_term.pop(m.index)
        _mem.save()
        return {"ok": True}
    return {"ok": False, "error": "unknown memory item"}


@app.delete("/api/memory/item")
async def memory_delete(kind: str = "long_term", index: int = -1, key: str = ""):
    if kind == "long_term" and 0 <= index < len(_mem.long_term):
        _mem.long_term.pop(index)
        _mem.save()
        return {"ok": True}
    if kind == "project" and key and key in _mem.project:
        _mem.project.pop(key)
        _mem.save()
        return {"ok": True}
    return {"ok": False, "error": "unknown memory item"}


@app.get("/api/tasks")
async def list_tasks():
    return tasks.list()


@app.post("/api/tasks/{tid}/cancel")
async def cancel_task(tid: str):
    tasks.cancel(tid)
    return {"ok": True}


@app.post("/api/tasks/{tid}/pause")
async def pause_task(tid: str):
    tasks.pause(tid)
    return {"ok": True}


@app.post("/api/tasks/{tid}/resume")
async def resume_task(tid: str):
    tasks.resume(tid)
    return {"ok": True}


@app.post("/api/stop")
async def stop_all():
    tasks.stop_all()
    policy.stop_everything()
    await asyncio.sleep(0.1)
    policy.reset_kill()
    return {"ok": True}


@app.get("/api/permissions/history")
async def perm_history():
    return policy.history()


@app.post("/api/sudo/plan")
async def sudo_plan(body: dict):
    plan = plan_privilege(body.get("command", []), body.get("target"))
    return {"mode": plan.mode, "reason": plan.reason, "command": plan.command}


# ---- super user access (v2) — pass-phase gated, logged, never silent sudo ----
@app.get("/api/su/status")
async def su_status():
    from ..security import su
    return su.status()


@app.post("/api/su/setup")
async def su_setup(body: dict):
    from ..security import su
    return su.setup(body.get("passphrase", ""), allow_shell=body.get("allow_shell", True))


@app.post("/api/su/unlock")
async def su_unlock(body: dict):
    from ..security import su
    return su.unlock(body.get("passphrase", ""), int(body.get("minutes", 5)))


@app.post("/api/su/disable")
async def su_disable():
    from ..security import su
    return su.disable()


@app.post("/api/su/exec")
async def su_exec(body: dict):
    from ..security import su
    return su.run(body.get("command", ""), int(body.get("timeout", 30)))


@app.post("/api/chat")
async def chat(c: ChatIn):
    r = await reply(c.text, _profile, _mem, c.provider, c.model, c.auto_route)
    out = {"text": r.text, "provider": r.provider, "model": r.model, "route": r.route_reason}
    if c.speak:
        out["speak"] = BrowserTTS().directive(
            r.text, VoiceSpec(_profile.voice, _profile.language, _profile.speech_rate)).get("text")
    return out


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    await ws.accept()
    connected.add(ws)
    global _sudo_password_provider
    loop = asyncio.get_running_loop()
    pending: dict[str, asyncio.Future] = {}

    async def ui_password(prompt: str) -> str:
        fut = loop.create_future()
        token = str(id(fut))
        pending[token] = fut
        await ws.send_text(json.dumps({"type": "sudo.prompt", "token": token, "prompt": prompt}))
        try:
            return await asyncio.wait_for(fut, 120)
        finally:
            pending.pop(token, None)

    _sudo_password_provider = ui_password
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if msg.get("type") == "sudo.password":
                fut = pending.get(msg.get("token", ""))
                if fut and not fut.done():
                    fut.set_result(msg.get("password", ""))
                continue
            if msg.get("type") == "chat":
                await ws.send_text(json.dumps({"type": "activity", "text": "Thinking…"}))
                r = await reply(msg.get("text", ""), _profile, _mem,
                                msg.get("provider"), msg.get("model"),
                                msg.get("auto_route", True))
                await ws.send_text(json.dumps({"type": "message", "text": r.text,
                                               "provider": r.provider, "model": r.model,
                                               "route": r.route_reason}))
                if msg.get("speak", True):
                    await ws.send_text(json.dumps({"type": "speak", "text": r.text,
                                                   "voice": _profile.voice,
                                                   "rate": _profile.speech_rate,
                                                   "lang": _profile.language}))
                await ws.send_text(json.dumps({"type": "idle"}))
    except WebSocketDisconnect:
        connected.discard(ws)
    finally:
        _sudo_password_provider = None
        connected.discard(ws)


from ..agents.registry import list_agents
from ..tools import files as file_tools
from ..tools import git as git_tools
from ..tools import shell as shell_tool
from ..workspace.projects import scaffold as scaffold_project

connected: set[WebSocket] = set()


async def broadcast(msg: dict) -> None:
    dead = []
    for ws in connected:
        try:
            await ws.send_text(json.dumps(msg))
        except Exception:
            dead.append(ws)
    for ws in dead:
        connected.discard(ws)


@app.get("/api/agents")
async def agents():
    return list_agents()


class ApproveIn(BaseModel):
    action: str = ""


@app.post("/api/approve")
async def approve(a: ApproveIn):
    import uuid
    token = uuid.uuid4().hex
    policy.grant(token)
    policy.log("ui", f"approved: {a.action}", policy.classify(a.action))
    return {"token": token}


@app.get("/api/workspace/tree")
async def ws_tree(root: str):
    return {"files": file_tools.tree(root)}


@app.get("/api/workspace/file")
async def ws_file(root: str, path: str):
    return {"path": path, "content": file_tools.read(root, path)}


class WriteIn(BaseModel):
    root: str
    path: str
    content: str
    token: str


@app.post("/api/workspace/write")
async def ws_write(w: WriteIn):
    return {"ok": True, "msg": file_tools.write(w.root, w.path, w.content, w.token)}


@app.post("/api/workspace/delete")
async def ws_delete(w: WriteIn):
    return {"ok": True, "msg": file_tools.remove(w.root, w.path, w.token)}


class TermIn(BaseModel):
    cmd: str
    cwd: str = "."
    token: str = ""


@app.post("/api/terminal/run")
async def term_run(t: TermIn):
    return await shell_tool.run(t.cmd, cwd=t.cwd, granted_token=t.token,
                                password_provider=_sudo_password_provider)


class GitIn(BaseModel):
    args: list[str] = []
    cwd: str = "."
    token: str = ""


@app.post("/api/git")
async def git_op(g: GitIn):
    return await git_tools.run_git(g.args, cwd=g.cwd, granted_token=g.token)


class BuildIn(BaseModel):
    goal: str
    dest: str
    provider: str | None = None
    model: str | None = None
    stages: dict | None = None  # {"plan": {"provider","model"}, ...} (§27)


@app.post("/api/build")
async def build(b: BuildIn):
    from ..agents.pipeline import build_project
    prov = b.provider or _profile.default_provider
    mod = b.model or _profile.default_model
    sm = {}
    for k, v in (b.stages or {}).items():
        if isinstance(v, dict):
            sm[k] = (v.get("provider", prov), v.get("model", mod))
    task, runner = await build_project(b.goal, b.dest, _profile, _mem, tasks,
                                       prov, mod, on_event=broadcast, stage_models=sm or None)
    import asyncio as _a
    _a.create_task(runner())
    return {"task_id": task.id, "status": task.status}


# ---- Phase 3: research / browser / desktop ----

from ..automation.scheduler import Scheduler as _Scheduler
from ..pet.pet import Companion as _Companion
from .. import background as _bg
from .. import notifications as _notif

_sched = _Scheduler()
_pet = _Companion()


class ResearchIn(BaseModel):
    question: str
    local_root: str = ""
    docs: list[str] = []
    provider: str | None = None
    model: str | None = None


@app.post("/api/research")
async def research_op(r: ResearchIn):
    from ..research import engine as R
    t = tasks.create(f"Research: {r.question[:60]}", agent="research",
                     model=f"{r.provider or _profile.default_provider}/{r.model or _profile.default_model}")

    async def steps():
        async def gather():
            rep = await R.research(r.question, _profile, _mem,
                                   r.provider or _profile.default_provider,
                                   r.model or _profile.default_model,
                                   r.local_root, r.docs,
                                   on_step=lambda s: broadcast({"type": "activity", "task": t.id, "text": s}))
            t.output = rep.summary
            await broadcast({"type": "research.done", "task": t.id})
            return f"{len(rep.sources)} sources"
        await tasks.run(t, [("research", gather)])
    import asyncio as _a
    _a.create_task(steps())
    return {"task_id": t.id}


@app.get("/api/research/{tid}")
async def research_result(tid: str):
    t = tasks.get(tid)
    return {"status": t.status if t else "missing", "logs": t.logs if t else [],
            "report": t.output if t else ""}


@app.post("/api/browser/fetch")
async def browser_fetch(body: dict):
    from ..browser.agent import fetch
    return await fetch(body.get("url", ""), body.get("token", ""))


@app.get("/api/desktop/caps")
async def desktop_caps():
    from ..desktop.control import capabilities
    from ..desktop.workspaces import detect
    return {"control": capabilities(), "workspaces": detect()}


@app.post("/api/desktop/plan")
async def desktop_plan(body: dict):
    from ..desktop.control import plan
    return plan(body.get("action", ""), body.get("target", ""))


@app.post("/api/desktop/act")
async def desktop_act(body: dict):
    from ..desktop.control import act
    return await act(body.get("action", ""), body.get("target", ""),
                     granted_token=body.get("token", ""))


@app.post("/api/desktop/work-focus")
async def work_focus():
    from ..desktop.workspaces import focus_work
    return focus_work()


@app.get("/api/desktop/windows")
async def desktop_windows():
    from ..desktop.control import _windows
    from ..permissions import policy as _pol
    _pol.log("desktop", "list windows", _pol.SAFE)
    return _windows()


@app.post("/api/desktop/shot")
async def desktop_shot(body: dict):
    from ..desktop.control import act
    return await act("screenshot", "", granted_token=body.get("token", ""))


@app.post("/api/desktop/describe")
async def desktop_describe(body: dict):
    """Voice-OS eyes: look at the screen and answer a question about it."""
    from fastapi import HTTPException
    from ..desktop import see as _see
    try:
        return await _see.describe(
            body.get("question") or "What is on my screen?",
            body.get("provider") or _profile.default_provider,
            body.get("model") or _profile.default_model)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ---- Phase 4: companion / automations / skills / memory-search / notifications ----

@app.get("/api/companion")
async def companion_state():
    _pet.heartbeat(sum(1 for t in tasks.tasks.values() if t.status == "running"))
    return _pet.state()


@app.post("/api/companion")
async def companion_set(body: dict):
    if "enabled" in body:
        _pet.enabled = bool(body["enabled"])
    if body.get("poke"):
        return {"line": _pet.poke()}
    if "notify" in body:
        _pet.notify(body["notify"], body.get("task", ""), body.get("progress", 0.0))
    return _pet.state()


@app.get("/api/automations")
async def automations_list():
    return [r.__dict__ for r in _sched.rules.values()]


@app.post("/api/automations")
async def automations_add(body: dict):
    r = _sched.add(body.get("name", "rule"), body.get("kind", "interval"),
                   body.get("action", "notify"), body.get("payload", {}),
                   int(body.get("every_sec", 3600)), body.get("at", ""))
    return r.__dict__


@app.delete("/api/automations/{rid}")
async def automations_del(rid: str):
    _sched.remove(rid)
    return {"ok": True}


@app.get("/api/skills")
async def skills_list():
    from ..skills.loader import discover
    return discover()


@app.post("/api/skills/{name}")
async def skills_toggle(name: str, body: dict):
    from ..skills.loader import set_enabled
    set_enabled(name, bool(body.get("enabled", True)))
    return {"ok": True}


@app.get("/api/memory/search")
async def memory_search(q: str):
    from ..brain.memory.search import search
    return search(_mem, q)


@app.get("/api/notifications")
async def notif_list():
    return _notif.feed()


@app.post("/api/notify")
async def notify(body: dict):
    item = _notif.notify(body.get("title", "Mitsu"), body.get("body", ""))
    await broadcast({"type": "notify", **item})
    return item


@app.post("/api/background")
async def background_set(body: dict):
    _bg.set_enabled(bool(body.get("enabled", True)))
    return {"ok": True, "enabled": body.get("enabled", True)}


@app.get("/api/voice/status")
async def voice_status():
    from ..voice import server_tts as ST
    return {"server": ST.status()}


@app.get("/api/tts")
async def tts(text: str, rate: int = 175, voice: str = "lessac"):
    from fastapi.responses import Response
    from ..voice import server_tts as ST
    try:
        wav = await ST.synthesize(text, rate, voice)
        return Response(content=wav, media_type="audio/wav")
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/stt/status")
async def stt_status():
    from ..voice import server_stt as SST
    return SST.status()


@app.get("/api/stt/doctor")
async def stt_doctor():
    from ..voice import server_stt as SST
    return SST.doctor()


@app.get("/api/setup")
async def setup_status():
    from ..setup import deps as D
    return D.status()


@app.get("/api/setup/os")
async def setup_os():
    from ..setup import deps as D
    return D.platform()


@app.post("/api/setup/install")
async def setup_install(body: dict):
    """Install missing deps as a tracked task (Ollama binary excluded → sudo)."""
    from ..setup import deps as D
    ids = set(body.get("ids", []))
    t = tasks.create("Install dependencies", agent="system", model="setup")
    pips = [i.split("pip:", 1)[1] for i in ids if i.startswith("pip:")]

    async def steps():
        async def pip_step():
            if pips:
                return D.pip_install(pips)
            return "python deps already ok"

        async def piper_step():
            if any(i == "piper" or i.startswith("voice:") for i in ids):
                return D.install_piper()
            return "voices already ok"

        async def whisper_step():
            if "whisper" in ids:
                await broadcast({"type": "activity", "task": t.id, "text": "Downloading whisper… (~145MB)"})
                return D.install_whisper()
            return "whisper already ok"

        async def omodel_step():
            mods = [i.split(":", 1)[1] for i in ids if i.startswith("ollama-model:")]
            outs = []
            for m in mods:
                from ..providers import shop as S
                outs.append(await S.pull(m, lambda line: broadcast(
                    {"type": "activity", "task": t.id, "text": line[-120]})))
            return "; ".join(outs) if outs else "ollama models already ok"
        await tasks.run(t, [("python packages", pip_step), ("voices", piper_step),
                            ("whisper", whisper_step), ("ollama models", omodel_step)])
        await broadcast({"type": "activity", "task": t.id, "kind": "done",
                         "text": f"setup {t.status}"})
    import asyncio as _a
    _a.create_task(steps())
    return {"task_id": t.id}


@app.post("/api/setup/ollama")
async def setup_ollama():
    """Install the Ollama engine itself — the one step that needs sudo."""
    from ..setup import deps as D
    try:
        msg = await D.install_ollama_binary(password_provider=_sudo_password_provider)
        return {"ok": True, "msg": msg}
    except PermissionError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e)[:500])


@app.get("/api/ollama/library")
async def ollama_library(q: str = ""):
    from ..providers import shop as S
    return {"library": S.search(q), "local": S.local()}


@app.post("/api/ollama/pull")
async def ollama_pull(body: dict):
    from ..providers import shop as S
    name = body.get("name", "").strip()
    if not name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="model name required")
    t = tasks.create(f"Pull {name}", agent="system", model="ollama")

    async def steps():
        async def go():
            return await S.pull(name, lambda line: broadcast(
                {"type": "activity", "task": t.id, "text": line[-120]}))
        await tasks.run(t, [("pull", go)])
    import asyncio as _a
    _a.create_task(steps())
    return {"task_id": t.id}


@app.delete("/api/ollama/local")
async def ollama_rm(name: str):
    from ..providers import shop as S
    return {"ok": True, "msg": await S.remove(name)}


@app.get("/api/wake")
async def wake_status():
    from ..voice import wake as W
    return W.status()


@app.post("/api/wake")
async def wake_set(body: dict):
    import asyncio as _a
    from ..voice import wake as W
    if body.get("enabled"):
        loop = _a.get_running_loop()

        def fire(tag: str):
            word, _, sc = tag.partition(":")
            try:
                score = round(float(sc), 2)
            except ValueError:
                score = 1.0
            _a.run_coroutine_threadsafe(
                broadcast({"type": "wake", "word": word, "score": score}), loop)
        try:
            W.start(on_wake=fire)
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail=str(e))
    else:
        W.stop()
    return W.status()


@app.post("/api/wake/enroll")
async def wake_enroll(body: dict):
    """Enroll one 'mitsu' sample from the server mic. Repeat 3x."""
    import asyncio as _a
    from ..voice import enroll as E
    from ..voice import server_stt as SST
    try:
        path = await _a.get_running_loop().run_in_executor(
            None, SST.record, int(body.get("seconds", 4)))
        audio = await _a.get_running_loop().run_in_executor(None, SST.decode, path)
        import os as _os
        try:
            _os.unlink(path)
        except OSError:
            pass
        return E.add_sample(audio)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/wake/templates")
async def wake_templates():
    from ..voice import enroll as E
    st = E.load()
    return {"count": len(st.get("templates", [])), "ready": len(st.get("templates", [])) >= 3,
            "threshold": st.get("threshold", 0.0)}


@app.delete("/api/wake/templates")
async def wake_clear():
    from ..voice import enroll as E
    E.clear()
    return {"ok": True}


class ListenIn(BaseModel):
    seconds: int = 30  # cap for VAD mode
    send_chat: bool = False
    vad: bool = True  # stop automatically on silence (DeepSeek-style)


@app.post("/api/stt/record")
async def stt_record(l: ListenIn):
    """Record from the server mic and transcribe — voice input for app + terminal."""
    import asyncio as _a
    import os as _os
    from ..voice import server_stt as SST
    try:
        if l.vad:
            cap = await _a.get_running_loop().run_in_executor(None, SST.record_vad, l.seconds)
            path, diag = cap["path"], {"stream_sec": cap["stream_sec"],
                                       "heard_speech": cap["heard_speech"]}
            if not cap["heard_speech"]:
                try:
                    _os.unlink(path)
                except OSError:
                    pass
                return {"text": "", "heard_speech": False, **diag}
        else:
            path = await _a.get_running_loop().run_in_executor(None, SST.record, l.seconds)
            diag = {}
        res = await _a.get_running_loop().run_in_executor(None, SST.transcribe_file, path)
        try:
            _os.unlink(path)
        except OSError:
            pass
        res = {**res, **diag}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(e))
    if l.send_chat and res["text"]:
        r = await reply(res["text"], _profile, _mem)
        return {**res, "reply": r.text, "provider": r.provider, "model": r.model}
    return res


@app.on_event("startup")
async def _start_background():
    import asyncio as _a

    async def chat_fn(prompt: str) -> str:
        r = await reply(prompt, _profile, _mem)
        return r.text

    def context():
        import time as _t
        last = _mem.short[-1].get("ts", 0) if _mem.short else 0
        idle_min = (_t.time() - last) / 60 if last else 0.0
        return tasks, idle_min

    _a.create_task(_bg.loop(_sched, lambda t, b: _notif.notify(t, b), chat_fn, context=context))


if UI_DIR.exists():
    @app.get("/")
    async def index():
        return FileResponse(UI_DIR / "index.html")

    app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")


def run() -> None:
    import uvicorn
    print(f"Mitsu on http://{APP_HOST}:{APP_PORT}")
    uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="info")
