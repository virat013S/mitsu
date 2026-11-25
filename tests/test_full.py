import asyncio
from mitsu.automation.scheduler import Scheduler
from mitsu.pet.pet import Companion
from mitsu.desktop.control import capabilities, plan
from mitsu.desktop.workspaces import detect, focus_work
from mitsu.brain.memory.search import search
from mitsu.brain.memory.store import MemoryStore
from mitsu import notifications as N
from mitsu.research import engine as R
from mitsu.skills.loader import discover, set_enabled, active_instructions


def test_research_offline_graceful():
    async def go():
        rep = await R.research("test question", local_root="", pasted_docs=["doc says X"])
        assert rep.question == "test question"
        assert isinstance(rep.summary, str) and len(rep.summary) > 0
    asyncio.run(go())


def test_desktop_plan_never_executes():
    p = plan("type", "hello")
    assert p["level"] == "sensitive"
    caps = capabilities()
    assert "launch" in caps


def test_workspaces_safe():
    assert "work_view" in detect()
    assert focus_work()["ok"] is True


def test_companion_lightweight():
    pet = Companion()
    assert pet.state()["mood"] == "idle"
    pet.notify("build done")
    assert pet.state()["mood"] in ("excited", "working")
    pet.poke()
    pet.heartbeat(0)


def test_automation_lifecycle(tmp_path, monkeypatch):
    import mitsu.core.paths as C
    monkeypatch.setattr(C, "data_dir", lambda: tmp_path)
    from mitsu.automation.scheduler import Scheduler as S
    s = S()
    r = s.add("t", "interval", "notify", {"body": "hi"}, every_sec=0)
    assert s.due()[0].id == r.id
    s.mark_ran(r)
    s.remove(r.id)
    assert r.id not in s.rules


def test_skills_discover_toggle():
    ds = discover()
    names = [d["name"] for d in ds]
    assert "notes" in names and "sysinfo" in names
    set_enabled("notes", False)
    assert "notes" not in active_instructions()
    set_enabled("notes", True)


def test_memory_search():
    m = MemoryStore()
    m.short = [{"role": "user", "content": "I love building minecraft mods", "ts": 0}]
    assert search(m, "minecraft")[0]["score"] > 0
    assert search(m, "zzz-no-match") == []


def test_notify_feed():
    N.notify("t", "b")
    assert N.feed()[-1]["title"] == "t"
