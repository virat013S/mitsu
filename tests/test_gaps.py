import time
from mitsu.automation.scheduler import Scheduler
from mitsu.tasks.manager import TaskManager


def test_event_task_done_fires_once(tmp_path, monkeypatch):
    import mitsu.core.paths as C
    monkeypatch.setattr(C, "data_dir", lambda: tmp_path)
    s = Scheduler()
    tm = TaskManager()
    t = tm.create("deploy site")
    r = s.add("watch deploy", "event", "notify", {"body": "done!", "event": {"type": "task_done", "task": "deploy"}})
    assert s.due_events(tm) == []  # arms, does not fire on creation
    t.status = "completed"
    fired = s.due_events(tm)
    assert [x.id for x in fired] == [r.id]
    assert s.due_events(tm) == []  # fire-once
    s.remove(r.id)


def test_event_file_change(tmp_path, monkeypatch):
    import mitsu.core.paths as C
    monkeypatch.setattr(C, "data_dir", lambda: tmp_path)
    s = Scheduler()
    f = tmp_path / "w.txt"
    f.write_text("a")
    r = s.add("watch file", "event", "notify", {"body": "changed", "event": {"type": "file_change", "path": str(f)}})
    assert s.due_events() == []
    time.sleep(0.05)
    f.write_text("b")
    # mtime granularity: force if fs is coarse
    import os
    os.utime(f, (time.time() + 2, time.time() + 2))
    assert [x.id for x in s.due_events()] == [r.id]
    s.remove(r.id)


def test_event_idle(tmp_path, monkeypatch):
    import mitsu.core.paths as C
    monkeypatch.setattr(C, "data_dir", lambda: tmp_path)
    s = Scheduler()
    r = s.add("idle nudge", "event", "notify", {"body": "hi", "event": {"type": "idle", "minutes": 30}})
    assert s.due_events(idle_minutes=0.0) == []
    assert [x.id for x in s.due_events(idle_minutes=45.0)] == [r.id]


def test_memory_item_edit_delete():
    from mitsu.brain.memory.store import MemoryStore
    m = MemoryStore()
    m.long_term = [{"fact": "likes tea", "ts": 0}]
    assert len(m.long_term) == 1


def test_research_domain_status():
    from mitsu.research.engine import Report
    r = Report(question="q", summary="s",
               findings=[{"claim": "c", "status": "supported", "sources": ["a", "b"], "domains": ["x", "y"]}])
    assert r.findings[0]["status"] == "supported"
