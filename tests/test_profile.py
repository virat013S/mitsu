"""Single identity source-of-truth tests (core.profile).

All tests are hermetic: memory path and username file are redirected
into a temp directory, so the developer's real state is never touched.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory import memory_manager
from core import profile


class ProfileServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._mem = Path(self._tmp.name) / "long_term.json"
        self._user = Path(self._tmp.name) / "username.txt"
        patch.object(memory_manager, "MEMORY_PATH", self._mem).start()
        self.addCleanup(patch.stopall)
        patch.object(profile, "USERNAME_FILE", self._user).start()

    def test_fresh_install_has_no_identity(self):
        self.assertEqual(profile.get_display_name(), "")
        self.assertTrue(profile.is_guest())
        self.assertEqual(
            profile.profile_snapshot(),
            {"display_name": "", "guest": True},
        )

    def test_set_persists_across_reload(self):
        profile.set_display_name("Alex")
        # Simulate a restart: re-resolve from disk-backed stores.
        self.assertEqual(profile.get_display_name(), "Alex")
        self.assertFalse(profile.is_guest())
        self.assertEqual(self._user.read_text(encoding="utf-8"), "Alex")

    def test_memory_is_preferred_over_stale_file(self):
        self._user.write_text("Sam", encoding="utf-8")
        profile.set_display_name("Alex")
        self.assertEqual(profile.get_display_name(), "Alex")

    def test_file_fallback_when_memory_empty(self):
        self._user.write_text("Sam", encoding="utf-8")
        self.assertEqual(profile.get_display_name(), "Sam")

    def test_sync_repairs_diverged_stores(self):
        self._user.write_text("Sam", encoding="utf-8")
        self.assertEqual(profile.sync_stores(), "Sam")
        self.assertEqual(profile.get_display_name(), "Sam")
        # Memory now agrees with the file.
        mem_name = memory_manager.load_memory()["identity"]["name"]
        value = mem_name.get("value") if isinstance(mem_name, dict) else mem_name
        self.assertEqual(value, "Sam")

    def test_reserved_names_are_rejected(self):
        for bad in ("", "  ", "sir", "Madam", "FRIEND", "there"):
            with self.subTest(name=bad):
                with self.assertRaises(ValueError):
                    profile.set_display_name(bad)
        self.assertTrue(profile.is_guest())

    def test_change_name_updates_every_store(self):
        profile.set_display_name("Alex")
        profile.set_display_name("Sam")
        self.assertEqual(profile.get_display_name(), "Sam")
        self.assertEqual(self._user.read_text(encoding="utf-8"), "Sam")

    def test_clear_forgets_every_store(self):
        profile.set_display_name("Alex")
        profile.clear_display_name()
        self.assertEqual(profile.get_display_name(), "")
        self.assertTrue(profile.is_guest())
        self.assertFalse(self._user.exists())

    def test_corrupt_memory_does_not_crash_resolution(self):
        self._mem.write_text("{broken", encoding="utf-8")
        self._user.write_text("Sam", encoding="utf-8")
        self.assertEqual(profile.get_display_name(), "Sam")


if __name__ == "__main__":
    unittest.main()
