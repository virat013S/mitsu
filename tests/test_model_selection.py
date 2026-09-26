"""Multi-provider + user-selectable model system tests.

Covers: selection persistence, env/explicit precedence (no silent
overrides), runtime propagation (ollama/openrouter/gemini use the
selected model), provider isolation (no cross-provider key demands),
capability gating, fallback policy, live-model precedence, CLI setup,
and the setup/settings UI selectors.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import models
from memory import memory_manager
from core import profile as profile_svc

try:
    import httpx  # noqa: F401
    from core import providers
    _HAS_PROVIDERS = True
except ImportError:
    providers = None
    _HAS_PROVIDERS = False

try:
    import main as mitsu_main
    _HAS_MAIN = True
except ImportError:
    mitsu_main = None
    _HAS_MAIN = False

try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    import ui
    _HAS_UI = True
except ImportError:
    _HAS_UI = False

_ENV_VARS = ("MITSU_PROVIDER", "MITSU_MODEL", "OLLAMA_MODEL",
             "OPENROUTER_MODEL", "GEMINI_API_KEY", "OPENROUTER_API_KEY",
             "GEMINI_LIVE_MODEL")


class _IsoMixin:
    def _isolate(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._tmp = Path(tmp.name)
        self._saved_env = {var: os.environ.get(var) for var in _ENV_VARS}
        for var in _ENV_VARS:
            os.environ.pop(var, None)
        self.addCleanup(self._restore_env)
        patch.object(models, "PROVIDER_PATH",
                     self._tmp / "provider.json").start()
        self.addCleanup(patch.stopall)
        patch.object(memory_manager, "MEMORY_PATH",
                     self._tmp / "long_term.json").start()
        patch.object(profile_svc, "USERNAME_FILE",
                     self._tmp / "username.txt").start()

    def _restore_env(self):
        for var in _ENV_VARS:
            os.environ.pop(var, None)
        for var, val in self._saved_env.items():
            if val is not None:
                os.environ[var] = val


class SelectionTests(unittest.TestCase, _IsoMixin):
    def setUp(self):
        self._isolate()

    def test_set_get_round_trip(self):
        saved = models.set_selection("ollama", "qwen3:1.7b")
        self.assertEqual(saved, {"provider": "ollama", "model": "qwen3:1.7b",
                                 "fallback": "ask"})
        sel = models.get_selection()
        self.assertEqual(sel["provider"], "ollama")
        self.assertEqual(sel["model"], "qwen3:1.7b")

    def test_selection_persists_across_restart(self):
        models.set_selection("openrouter", "qwen/qwen3-32b:free")
        raw = json.loads((self._tmp / "provider.json").read_text())
        self.assertEqual(raw["model"], "qwen/qwen3-32b:free")
        # Simulate a restart: fresh read from disk.
        self.assertEqual(models.get_selection()["model"], "qwen/qwen3-32b:free")

    def test_env_override_wins_without_clobbering_store(self):
        models.set_selection("ollama", "gemma3:1b")
        os.environ["MITSU_MODEL"] = "llama3.2:3b"
        self.assertEqual(models.get_selection()["model"], "llama3.2:3b")
        raw = json.loads((self._tmp / "provider.json").read_text())
        self.assertEqual(raw["model"], "gemma3:1b")

    def test_explicit_argument_always_wins(self):
        models.set_selection("ollama", "gemma3:1b")
        self.assertEqual(models.resolve_model("ollama", explicit="qwen3:1.7b"),
                         "qwen3:1.7b")

    def test_resolve_falls_back_to_provider_default(self):
        self.assertEqual(models.resolve_model("ollama"), "gemma3:1b")

    def test_legacy_env_honored_below_stored_selection(self):
        os.environ["OLLAMA_MODEL"] = "llama3.2:3b"
        self.assertEqual(models.get_selection()["model"], "llama3.2:3b")
        models.set_selection("ollama", "gemma3:1b")
        self.assertEqual(models.get_selection()["model"], "gemma3:1b")

    def test_unknown_provider_rejected(self):
        with self.assertRaises(ValueError):
            models.set_selection("anthropic", "claude")
        with self.assertRaises(ValueError):
            models.set_selection("ollama", "  ")

    def test_fallback_policy_round_trip(self):
        models.set_selection("ollama", "gemma3:1b")
        self.assertEqual(models.get_fallback_policy(), "ask")
        self.assertEqual(models.set_fallback_policy("never"), "never")
        self.assertEqual(models.get_selection()["fallback"], "never")
        with self.assertRaises(ValueError):
            models.set_fallback_policy("sometimes")

    def test_switching_providers_preserves_identity_and_memory(self):
        profile_svc.set_display_name("Alex")
        memory_manager.update_memory({"preferences": {"editor": {"value": "VS Code"}}})
        models.set_selection("openrouter", "qwen/qwen3-32b:free")
        models.set_selection("gemini", "gemini-2.5-flash")
        self.assertEqual(profile_svc.get_display_name(), "Alex")
        mem = memory_manager.load_memory()
        self.assertEqual(mem["preferences"]["editor"]["value"], "VS Code")

    def test_explicit_selection_none_until_user_chooses(self):
        self.assertIsNone(models.explicit_selection())
        models.set_selection("gemini", "gemini-2.5-flash")
        self.assertEqual(models.explicit_selection(),
                         {"provider": "gemini", "model": "gemini-2.5-flash"})

    def test_fallback_defaults_match_provider_registry(self):
        if not _HAS_PROVIDERS:
            self.skipTest("core.providers needs httpx")
        for provider, model in models.FALLBACK_DEFAULT_MODELS.items():
            self.assertEqual(providers.PROVIDERS[provider]["model"], model)

    def test_catalog_rejects_unknown_provider(self):
        with self.assertRaises(ValueError):
            models.catalog("anthropic")


@unittest.skipUnless(_HAS_PROVIDERS, "core.providers needs httpx")
class RuntimePropagationTests(unittest.TestCase, _IsoMixin):
    def setUp(self):
        self._isolate()

    def test_changing_ollama_model_changes_model_used(self):
        models.set_selection("ollama", "qwen3:1.7b")
        with patch.object(providers.httpx, "post") as post:
            post.return_value.json.return_value = {
                "message": {"content": "hi"}}
            providers.call_ollama([{"role": "user", "content": "hi"}])
        self.assertEqual(post.call_args.kwargs["json"]["model"], "qwen3:1.7b")

    def test_changing_openrouter_model_changes_model_used(self):
        models.set_selection("openrouter", "qwen/qwen3-32b:free")
        os.environ["OPENROUTER_API_KEY"] = "or-test"
        with patch.object(providers.httpx, "post") as post:
            post.return_value.json.return_value = {"choices": [
                {"message": {"content": "hi"}}]}
            providers.call_openrouter([{"role": "user", "content": "hi"}])
        self.assertEqual(post.call_args.kwargs["json"]["model"],
                         "qwen/qwen3-32b:free")

    def test_explicit_model_never_silently_overridden(self):
        models.set_selection("ollama", "gemma3:1b")
        with patch.object(providers.httpx, "post") as post:
            post.return_value.json.return_value = {
                "message": {"content": "hi"}}
            providers.chat_with_provider(
                [{"role": "user", "content": "hi"}],
                provider="ollama", model="llama3.2:3b")
        self.assertEqual(post.call_args.kwargs["json"]["model"], "llama3.2:3b")

    def test_gemini_text_model_follows_selection(self):
        models.set_selection("gemini", "gemini-2.5-pro")
        self.assertEqual(models.gemini_text_model(), "gemini-2.5-pro")
        self.assertEqual(models.gemini_text_model("gemini-2.5-flash-lite"),
                         "gemini-2.5-flash-lite")

    def test_ollama_missing_model_error_is_clear_and_local(self):
        with patch.object(models, "list_ollama_models", return_value=[]):
            # Empty list means daemon unreachable or model unknown.
            result = models.check_model("ollama", "qwen3:1.7b")
        self.assertFalse(result["available"])
        self.assertIn("ollama", result["error"].lower())
        self.assertNotIn("GEMINI_API_KEY", result["error"])

    def test_unknown_model_is_not_tool_capable_when_strict(self):
        self.assertFalse(models.model_supports(
            "openrouter", "some/unknown-model:free", models.TOOL_CALLS,
            strict=True))

    def test_catalog_default_is_tool_capable(self):
        self.assertTrue(models.model_supports(
            "ollama", "gemma3:1b", models.TOOL_CALLS, strict=True))

    def test_ollama_catalog_parses_sizes_and_warns_only_when_big(self):
        payload = {"models": [{"name": "qwen3:1.7b"}, {"name": "huge:70b"}]}
        with patch("httpx.get") as get:
            get.return_value.json.return_value = payload
            found = models.list_ollama_models()
        by_id = {m.id: m for m in found}
        self.assertEqual(by_id["qwen3:1.7b"].params_b, 1.7)
        self.assertEqual(by_id["qwen3:1.7b"].warning, "")
        self.assertTrue(by_id["huge:70b"].warning)

    def test_live_model_prefers_explicit_file_over_selection(self):
        from core import live_model
        models.set_selection("gemini", "gemini-2.5-pro")
        cfg = self._tmp / "api_keys.json"
        cfg.write_text(json.dumps({"live_model": "models/test-live"}))
        self.assertEqual(live_model.configured_live_model(cfg),
                         "models/test-live")

    def test_live_model_uses_stored_selection_without_file(self):
        from core import live_model
        models.set_selection(
            "gemini", "models/gemini-2.5-flash-native-audio-preview-12-2025")
        cfg = self._tmp / "api_keys.json"
        cfg.write_text(json.dumps({}))
        self.assertEqual(
            live_model.configured_live_model(cfg),
            "models/gemini-2.5-flash-native-audio-preview-12-2025")


@unittest.skipUnless(_HAS_MAIN, "main needs desktop deps")
class CliSetupTests(unittest.TestCase, _IsoMixin):
    def setUp(self):
        self._isolate()

    def test_noninteractive_setup_keeps_default_model(self):
        with patch("core.models.catalog", return_value=models.ollama_catalog()), \
             patch("builtins.input", side_effect=EOFError), \
             patch("core.providers.ensure_ollama_model", return_value=True):
            self.assertTrue(mitsu_main._setup_model_cli("ollama"))
        sel = models.get_selection()
        self.assertEqual(sel["provider"], "ollama")
        self.assertTrue(sel["model"])

    def test_numeric_choice_selects_listed_model(self):
        infos = models.ollama_catalog()
        with patch("core.models.catalog", return_value=infos), \
             patch("builtins.input", return_value="2"), \
             patch("core.providers.ensure_ollama_model", return_value=True):
            self.assertTrue(mitsu_main._setup_model_cli("ollama"))
        self.assertEqual(models.get_selection()["model"], infos[1].id)

    def test_save_provider_config_merge_preserves_model(self):
        models.set_selection("ollama", "qwen3:1.7b")
        with patch.object(mitsu_main, "PROVIDER_CONFIG",
                          self._tmp / "provider.json"):
            mitsu_main._save_provider_config({"provider": "ollama"})
        raw = json.loads((self._tmp / "provider.json").read_text())
        self.assertEqual(raw["model"], "qwen3:1.7b")


@unittest.skipUnless(_HAS_UI, "UI needs PyQt6")
class ModelUiTests(unittest.TestCase, _IsoMixin):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._isolate()
        self._overlay = None

    def tearDown(self):
        if self._overlay is not None:
            try:
                self._overlay.deleteLater()
            except Exception:
                pass
            self._overlay = None
        self.app.processEvents()

    def test_overlay_resolves_listed_and_custom_ids(self):
        self._overlay = ui.SetupOverlay(initial_provider="ollama")
        infos = [m.to_dict() for m in models.ollama_catalog()]
        self._overlay._on_models_finished(infos)
        self.assertTrue(self._overlay._model_combo.count() > 0)
        resolved = self._overlay._selected_model_id()
        self.assertTrue(resolved)
        # Custom typed id passes through untouched.
        self._overlay._model_infos = []
        self._overlay._model_combo.clear()
        self._overlay._model_combo.addItem("custom:9b", "custom:9b")
        self._overlay._model_combo.setCurrentIndex(0)
        self._overlay._on_model_changed(0)
        # With no catalog entries, raw text is used.
        self.assertIn("custom", self._overlay._selected_model_id())

    def test_setup_done_persists_model_choice(self):
        tmp_api = self._tmp / "api_keys.json"
        with patch.object(ui, "API_FILE", tmp_api):
            window = ui.MainWindow("face.png")
            window.show()
            self.app.processEvents()
            try:
                overlay = ui.SetupOverlay(initial_provider="ollama")
                overlay._selected_provider = "ollama"
                overlay._selected_model = "qwen3:1.7b"
                window._overlay = overlay
                overlay.done.connect(window._on_setup_done)
                overlay.done.emit("", "linux", False)
                self.app.processEvents()
                sel = models.get_selection()
                self.assertEqual(sel["provider"], "ollama")
                self.assertEqual(sel["model"], "qwen3:1.7b")
                # Identity untouched by provider setup.
                self.assertEqual(profile_svc.get_display_name(), "")
            finally:
                window.hide()
                window.deleteLater()
                overlay.deleteLater()
                self.app.processEvents()

    def test_settings_model_switch_updates_env_not_identity(self):
        profile_svc.set_display_name("Alex")
        tmp_api = self._tmp / "api_keys.json"
        with patch.object(ui, "API_FILE", tmp_api):
            window = ui.MainWindow("face.png")
            window.show()
            self.app.processEvents()
            try:
                window._on_settings_model("openrouter", "qwen/qwen3-32b:free")
                self.assertEqual(os.environ.get("MITSU_PROVIDER"), "openrouter")
                self.assertEqual(profile_svc.get_display_name(), "Alex")
            finally:
                window.hide()
                window.deleteLater()
                self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
