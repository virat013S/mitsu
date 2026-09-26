"""Critical provider isolation tests.

Non-Gemini modes must NEVER require a Gemini API key:
- LOCAL/Ollama works (or clearly reports Ollama unavailable), never a
  Gemini key prompt.
- OpenRouter with its own key works, never a Gemini key prompt.
- Only Gemini-selected mode may report missing Gemini credentials.
"""
import os
import unittest
from unittest.mock import patch

try:
    from core.providers import (
        check_provider_status,
        get_provider,
        missing_credential_message,
        provider_requires_key,
        translate_tool_error,
    )
except ImportError as _import_error:  # optional deps (httpx) missing
    check_provider_status = get_provider = None
    missing_credential_message = provider_requires_key = None
    translate_tool_error = None
    _IMPORT_REASON = f"core.providers unimportable: {_import_error}"
else:
    _IMPORT_REASON = None


def _clean_env():
    for var in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "MITSU_PROVIDER"):
        os.environ.pop(var, None)


@unittest.skipIf(_IMPORT_REASON is not None, _IMPORT_REASON or "skip")


class ProviderIsolationTests(unittest.TestCase):
    def setUp(self):
        self._saved = {
            var: os.environ.get(var) for var in
            ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "MITSU_PROVIDER")
        }
        _clean_env()

    def tearDown(self):
        _clean_env()
        for var, val in self._saved.items():
            if val is not None:
                os.environ[var] = val

    def test_local_mode_requires_no_key(self):
        os.environ["MITSU_PROVIDER"] = "ollama"
        self.assertIsNone(provider_requires_key("ollama"))
        self.assertIsNone(provider_requires_key())

    def test_openrouter_requires_only_its_own_key(self):
        self.assertEqual(provider_requires_key("openrouter"), "OPENROUTER_API_KEY")
        self.assertNotEqual(provider_requires_key("openrouter"), "GEMINI_API_KEY")

    def test_gemini_is_the_only_provider_needing_a_gemini_key(self):
        self.assertEqual(provider_requires_key("gemini"), "GEMINI_API_KEY")

    def test_local_status_never_mentions_gemini_key(self):
        os.environ["MITSU_PROVIDER"] = "ollama"
        with patch("core.providers.httpx.get", side_effect=RuntimeError("no server")):
            status = check_provider_status("ollama")
        self.assertFalse(status["available"])
        self.assertNotIn("GEMINI", (status.get("error") or "").upper())

    def test_openrouter_status_with_own_key_needs_no_gemini(self):
        os.environ["OPENROUTER_API_KEY"] = "or-test-key"
        status = check_provider_status("openrouter")
        self.assertTrue(status["available"])
        self.assertIsNone(status.get("error"))

    def test_openrouter_missing_key_error_mentions_only_openrouter(self):
        msg = missing_credential_message("openrouter")
        self.assertIn("OPENROUTER_API_KEY", msg)
        # May reassure that no Gemini key is needed, but must never
        # demand a Gemini key.
        self.assertNotIn("GEMINI_API_KEY", msg.replace("NO GEMINI KEY IS NEEDED", ""))
        self.assertIn("NO GEMINI KEY IS NEEDED", msg.upper())

    def test_local_unavailable_message_mentions_no_gemini(self):
        msg = missing_credential_message("ollama")
        self.assertIn("Ollama", msg)
        self.assertNotIn("GEMINI", msg.upper())

    def test_gemini_missing_key_error_is_gemini_only(self):
        status = check_provider_status("gemini")
        self.assertFalse(status["available"])
        self.assertIn("GEMINI_API_KEY", status.get("error") or "")
        self.assertIn("GEMINI", missing_credential_message("gemini"))

    def test_tool_error_without_gemini_key_names_active_provider(self):
        err = ValueError("Gemini API key not found. Set GEMINI_API_KEY.")
        msg = translate_tool_error("web_search", err, provider="ollama")
        self.assertIn("ollama", msg)
        self.assertIn("has not been changed", msg)

    def test_tool_error_in_gemini_mode_points_at_gemini_setup(self):
        err = ValueError("GEMINI_API_KEY environment variable not set.")
        msg = translate_tool_error("code_helper", err, provider="gemini")
        self.assertIn("Gemini is not configured", msg)

    def test_unrelated_tool_errors_pass_through(self):
        err = RuntimeError("browser crashed")
        self.assertEqual(
            translate_tool_error("browser_control", err, provider="ollama"),
            "Tool 'browser_control' failed: browser crashed",
        )

    def test_get_provider_prefers_explicit_selection(self):
        os.environ["MITSU_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = "or-test-key"
        self.assertEqual(get_provider(), "openrouter")


class SetupGateNamingTests(unittest.TestCase):
    def test_wait_for_setup_alias_exists(self):
        try:
            from ui import MitsuUI
        except ImportError as e:
            self.skipTest(f"ui unimportable: {e}")
        self.assertTrue(callable(getattr(MitsuUI, "wait_for_setup", None)))
        self.assertTrue(callable(getattr(MitsuUI, "wait_for_api_key", None)))


if __name__ == "__main__":
    unittest.main()
