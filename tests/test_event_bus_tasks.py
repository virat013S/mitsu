"""Event bus, task lifecycle (pause/resume/events), skills metadata,
permission risk levels.

Hermetic: task history recording is stubbed; no real task files are
written and no LLM is called (fake runners only).
"""
import threading
import time
import unittest
from unittest.mock import patch

from agent import task_queue as tq_module
from agent.executor import AgentExecutor
from agent.task_queue import TaskQueue, TaskStatus
from core import events as bus
from core import permissions
from core import skills


def _fast_runner(cancel_flag, update_progress):
    update_progress(50, "Halfway")
    return "done"


class EventBusTests(unittest.TestCase):
    def setUp(self):
        self.bus = bus.EventBus()

    def test_emit_delivers_to_subscriber(self):
        seen = []
        self.bus.subscribe(seen.append)
        evt = self.bus.emit(bus.TASK_CREATED, task_id="abc", goal="g")
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0], evt)
        self.assertEqual(evt.type, bus.TASK_CREATED)
        self.assertEqual(evt.task_id, "abc")

    def test_type_filter_limits_delivery(self):
        seen = []
        self.bus.subscribe(seen.append, event_types=[bus.TASK_COMPLETED])
        self.bus.emit(bus.TASK_STARTED, task_id="x")
        self.bus.emit(bus.TASK_COMPLETED, task_id="x")
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].type, bus.TASK_COMPLETED)

    def test_unsubscribe_stops_delivery(self):
        seen = []
        token = self.bus.subscribe(seen.append)
        self.assertTrue(self.bus.unsubscribe(token))
        self.bus.emit(bus.TASK_CREATED)
        self.assertEqual(seen, [])
        self.assertFalse(self.bus.unsubscribe(token))

    def test_recent_filters_by_type_and_task(self):
        self.bus.emit(bus.TASK_CREATED, task_id="a")
        self.bus.emit(bus.TASK_STARTED, task_id="a")
        self.bus.emit(bus.TASK_CREATED, task_id="b")
        self.assertEqual(len(self.bus.recent(bus.TASK_CREATED)), 2)
        self.assertEqual(len(self.bus.recent(task_id="a")), 2)
        self.assertEqual(len(self.bus.recent(bus.TASK_CREATED, task_id="b")), 1)

    def test_failing_subscriber_does_not_break_bus(self):
        def bad(evt):
            raise RuntimeError("boom")
        good = []
        self.bus.subscribe(bad)
        self.bus.subscribe(good.append)
        self.bus.emit(bus.TASK_CREATED)
        self.assertEqual(len(good), 1)


class TaskLifecycleTests(unittest.TestCase):
    def setUp(self):
        self._record = patch.object(
            tq_module, "record_task", return_value=None)
        self._record.start()
        self.addCleanup(patch.stopall)
        self.queue = TaskQueue(max_concurrent=2)
        self.queue.start()
        self.addCleanup(self.queue.stop)

    def _wait_for(self, task_id, statuses, timeout=10.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.queue.get_status(task_id)
            if status and status["status"] in statuses:
                return status
            time.sleep(0.05)
        return self.queue.get_status(task_id)

    def test_run_emits_created_started_completed(self):
        seen = []
        token = bus.subscribe(seen.append)
        self.addCleanup(bus.unsubscribe, token)
        task_id = self.queue.submit_job("fake work", _fast_runner, kind="agent")
        status = self._wait_for(task_id, ("completed", "failed", "cancelled"))
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["result"], "done")
        types = [e.type for e in seen if e.task_id == task_id]
        self.assertIn(bus.TASK_CREATED, types)
        self.assertIn(bus.TASK_STARTED, types)
        self.assertIn(bus.TASK_COMPLETED, types)

    def test_pause_resume_pending_task(self):
        gate = threading.Event()
        started = threading.Event()

        def runner(cancel_flag, update_progress):
            started.set()
            gate.wait(timeout=10)
            return "done"

        idle = TaskQueue()  # not started: submit stays PENDING
        task_id = idle.submit_job("pausable", runner, kind="agent")
        self.assertTrue(idle.pause(task_id))
        status = idle.get_status(task_id)
        self.assertEqual(status["status"], "paused")
        self.assertTrue(status["paused"])
        idle.start()
        self.addCleanup(idle.stop)
        # Worker must not pick it up while paused.
        time.sleep(0.4)
        self.assertFalse(started.is_set())
        self.assertTrue(idle.resume(task_id))
        gate.set()
        deadline = time.time() + 10.0
        while time.time() < deadline:
            status = idle.get_status(task_id)
            if status and status["status"] in ("completed", "failed"):
                break
            time.sleep(0.05)
        self.assertEqual(idle.get_status(task_id)["status"], "completed")

    def test_pause_resume_events_emitted(self):
        seen = []
        token = bus.subscribe(seen.append)
        self.addCleanup(bus.unsubscribe, token)
        idle = TaskQueue()  # not started for determinism
        task_id = idle.submit_job("pausable", _fast_runner, kind="agent")
        self.assertTrue(idle.pause(task_id))
        self.assertTrue(idle.resume(task_id))
        types = [e.type for e in seen if e.task_id == task_id]
        self.assertIn(bus.TASK_PAUSED, types)
        self.assertIn(bus.TASK_RESUMED, types)

    def test_pause_terminal_task_fails(self):
        task_id = self.queue.submit_job("quick", _fast_runner, kind="agent")
        self._wait_for(task_id, ("completed", "failed", "cancelled"))
        self.assertFalse(self.queue.pause(task_id))
        self.assertFalse(self.queue.resume(task_id))

    def test_cancel_clears_pause(self):
        idle = TaskQueue()  # not started for determinism
        task_id = idle.submit_job("stuck", _fast_runner, kind="agent")
        self.assertTrue(idle.pause(task_id))
        self.assertTrue(idle.cancel(task_id))
        status = idle.get_status(task_id)
        self.assertEqual(status["status"], "cancelled")
        self.assertFalse(status["paused"])

    def test_executor_wait_if_paused_blocks_until_resume(self):
        pause = threading.Event()
        cancel = threading.Event()
        pause.set()
        threading.Timer(0.3, pause.clear).start()
        start = time.time()
        AgentExecutor._wait_if_paused(cancel, pause)
        self.assertGreaterEqual(time.time() - start, 0.25)

    def test_executor_wait_if_paused_aborts_on_cancel(self):
        pause = threading.Event()
        cancel = threading.Event()
        pause.set()
        cancel.set()
        start = time.time()
        AgentExecutor._wait_if_paused(cancel, pause)
        self.assertLess(time.time() - start, 0.2)


class SkillsMetadataTests(unittest.TestCase):
    def test_every_skill_has_metadata(self):
        for name in skills.SKILLS:
            with self.subTest(skill=name):
                meta = skills.get_skill_metadata(name)
                self.assertIsNotNone(meta)
                self.assertIn("category", meta)
                self.assertIn("risk", meta)
                self.assertIn(meta["risk"], (skills.RISK_LOW, skills.RISK_MEDIUM))

    def test_unknown_skill_is_unavailable(self):
        result = skills.skill_availability("nope")
        self.assertEqual(result["state"], skills.UNAVAILABLE)

    def test_stdlib_skills_are_available(self):
        for name in ("calculator", "datetime", "json_parse", "read_file"):
            with self.subTest(skill=name):
                self.assertEqual(
                    skills.skill_availability(name)["state"], skills.AVAILABLE)

    def test_missing_dependency_reported(self):
        with patch("importlib.util.find_spec", return_value=None):
            result = skills.skill_availability("web_fetch")
            self.assertEqual(result["state"], skills.REQUIRES_DEPENDENCY)
            self.assertIn("httpx", result["reason"])


class PermissionRiskTests(unittest.TestCase):
    def test_read_only_tools_are_low(self):
        for tool in ("web_search", "deep_research", "task_status"):
            self.assertEqual(permissions.tool_risk(tool), permissions.RISK_LOW)

    def test_sending_and_shell_tools_need_approval(self):
        for tool in ("send_message", "email_control", "computer_control"):
            self.assertTrue(permissions.needs_approval(tool))

    def test_low_risk_needs_no_approval(self):
        self.assertFalse(permissions.needs_approval("web_search"))

    def test_destructive_params_escalate_to_critical(self):
        self.assertEqual(
            permissions.tool_risk("computer_settings", {"action": "shutdown now"}),
            permissions.RISK_CRITICAL)
        self.assertTrue(
            permissions.needs_approval("computer_settings", {"action": "restart"}))


if __name__ == "__main__":
    unittest.main()
