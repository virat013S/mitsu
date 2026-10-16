import asyncio
from mitsu.tasks.manager import TaskManager


def test_tasks_run_and_cancel():
    async def go():
        tm = TaskManager()
        t = tm.create("demo")
        async def step():
            return "ok"
        await tm.run(t, [("a", step), ("b", step)])
        assert t.status == "completed"
        assert t.progress == 1.0
        t2 = tm.create("x")
        tm.cancel(t2.id)
        assert tm.get(t2.id).status == "cancelled"
    asyncio.run(go())
