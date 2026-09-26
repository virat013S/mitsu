"""Platform capability detection + doctor tests.

Detection functions take injected OS/env parameters so any platform can
be simulated without touching the real machine.
"""
import unittest

from core import platform as plat
from scripts import doctor


class DetectOsTests(unittest.TestCase):
    def test_canonical_ids(self):
        self.assertEqual(plat.detect_os("Windows"), "windows")
        self.assertEqual(plat.detect_os("Darwin"), "mac")
        self.assertEqual(plat.detect_os("Linux"), "linux")
        self.assertEqual(plat.detect_os("FreeBSD"), "unknown")

    def test_desktop_detection(self):
        self.assertEqual(
            plat.detect_desktop({"XDG_CURRENT_DESKTOP": "KDE", "DESKTOP_SESSION": ""}),
            "kde")
        self.assertEqual(
            plat.detect_desktop({"XDG_CURRENT_DESKTOP": "ubuntu:GNOME"}), "gnome")
        self.assertEqual(plat.detect_desktop({}), "unknown")

    def test_display_detection(self):
        self.assertEqual(
            plat.detect_display({"WAYLAND_DISPLAY": "wayland-0"}), "wayland")
        self.assertEqual(plat.detect_display({"DISPLAY": ":0"}), "x11")
        self.assertEqual(plat.detect_display({}), "unknown")


class CapabilityTests(unittest.TestCase):
    def test_windows_reports_native_window_management(self):
        caps = plat.detect_capabilities(os_id="windows", env={})
        self.assertEqual(caps["window_management"].state, plat.SUPPORTED)
        self.assertEqual(caps["virtual_desktops"].state, plat.SUPPORTED)

    def test_mac_reports_partial_spaces(self):
        caps = plat.detect_capabilities(os_id="mac", env={})
        self.assertEqual(caps["virtual_desktops"].state, plat.PARTIAL)

    def test_wayland_is_never_claimed_supported(self):
        caps = plat.detect_capabilities(
            os_id="linux", env={"WAYLAND_DISPLAY": "wayland-0"})
        self.assertNotEqual(caps["window_management"].state, plat.SUPPORTED)

    def test_every_capability_has_state_and_reason(self):
        for name, cap in plat.detect_capabilities().items():
            with self.subTest(capability=name):
                self.assertIn(cap.state, (plat.SUPPORTED, plat.PARTIAL,
                                          plat.REQUIRES_PERMISSION,
                                          plat.REQUIRES_DEPENDENCY,
                                          plat.UNAVAILABLE))
                self.assertIsInstance(cap.reason, str)

    def test_summary_is_json_safe(self):
        import json
        summary = plat.capability_summary()
        json.dumps(summary)
        self.assertIn("os", summary)
        self.assertIn("capabilities", summary)


class DoctorTests(unittest.TestCase):
    def test_checks_have_status_reason_action_shape(self):
        for check in doctor.run_checks():
            with self.subTest(check=check.get("name")):
                self.assertIn(check["status"], ("PASS", "SKIP", "FAIL"))
                self.assertIsInstance(check["reason"], str)
                self.assertIn("action", check)

    def test_expected_check_groups_present(self):
        names = {c["name"] for c in doctor.run_checks()}
        self.assertIn("python", names)
        self.assertIn("identity", names)
        self.assertIn("platform", names)
        self.assertIn("ai_selection", names)
        self.assertIn("ai_connection", names)
        self.assertIn("memory", names)
        # Provider detail checks, or a single SKIP when deps are missing.
        self.assertTrue(any(n.startswith("provider:") for n in names)
                        or "providers" in names or "provider_selection" in names)

    def test_model_report_shape(self):
        names = {c["name"] for c in doctor.run_checks()}
        for expected in ("ai_selection", "ai_connection", "ai_tool_calling",
                         "ai_vision", "memory"):
            self.assertIn(expected, names)


if __name__ == "__main__":
    unittest.main()
