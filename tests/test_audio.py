"""Provider-independent audio tests (core.audio + voice_input skill).

Hermetic: audio config is redirected to a temp file; real hardware is
never touched (sounddevice/SpeechRecognition are stubbed where needed).
"""
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile

from core import audio
from core import skills


class AudioSelectionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._cfg = Path(tmp.name) / "audio.json"
        patch.object(audio, "CONFIG_PATH", self._cfg).start()
        self.addCleanup(patch.stopall)

    def test_fresh_install_uses_system_defaults(self):
        self.assertEqual(audio.get_selection(), {"input": None, "output": None})

    def test_set_persists_across_restart(self):
        audio.set_selection(input=2, output=5)
        self.assertEqual(audio.get_selection(), {"input": 2, "output": 5})
        raw = json.loads(self._cfg.read_text())
        self.assertEqual(raw, {"input": 2, "output": 5})

    def test_partial_update_preserves_other_side(self):
        audio.set_selection(input=1, output=3)
        audio.set_selection(output=7)
        self.assertEqual(audio.get_selection(), {"input": 1, "output": 7})

    def test_clear_resets_to_defaults(self):
        audio.set_selection(input=1, output=3)
        audio.clear_selection()
        self.assertEqual(audio.get_selection(), {"input": None, "output": None})

    def test_list_devices_without_sounddevice(self):
        with patch.object(audio, "_sounddevice", return_value=None):
            devices = audio.list_devices()
        self.assertEqual(devices["inputs"], [])
        self.assertIn("error", devices)

    def test_listen_without_stt_reports_clearly(self):
        import sys
        saved = sys.modules.get("speech_recognition", "absent")
        sys.modules["speech_recognition"] = None  # forces ImportError
        try:
            result = audio.listen_once()
        finally:
            if saved == "absent":
                del sys.modules["speech_recognition"]
            else:
                sys.modules["speech_recognition"] = saved
        self.assertFalse(result["ok"])
        self.assertTrue(result["error"])

    def test_play_missing_file_reports_clearly(self):
        result = audio.play_file("/nonexistent-xyz/missing.mp3")
        self.assertFalse(result["ok"])
        self.assertIn("not found", result["error"])

    def test_describe_shape(self):
        info = audio.describe()
        for key in ("inputs", "outputs", "selected_input", "selected_output",
                    "ffmpeg", "stt"):
            self.assertIn(key, info)


class VoiceSkillTests(unittest.TestCase):
    def test_voice_input_has_metadata(self):
        meta = skills.get_skill_metadata("voice_input")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["risk"], skills.RISK_LOW)

    def test_voice_input_reports_unavailable_gracefully(self):
        with patch("core.audio.listen_once",
                   return_value={"ok": False, "error": "no mic"}):
            result = skills.run_skill("voice_input")
        self.assertIn("unavailable", result)

    def test_voice_input_returns_transcript(self):
        with patch("core.audio.listen_once",
                   return_value={"ok": True, "text": "hello mitsu"}):
            self.assertEqual(skills.run_skill("voice_input"), "hello mitsu")


if __name__ == "__main__":
    unittest.main()
