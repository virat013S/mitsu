from mitsu.brain.personality import system_prompt
from mitsu.permissions.sudo import plan_privilege
from mitsu.permissions import policy
from mitsu.brain.router import route


def test_personality_names_user():
    p = system_prompt("friendly", "Virat")
    assert "Virat" in p


def test_sudo_prefers_unprivileged(tmp_path):
    plan = plan_privilege(["pip", "install", "requests"], target=str(tmp_path))
    assert plan.mode == "unprivileged"


def test_sudo_required_for_system_target():
    plan = plan_privilege(["rm", "-rf", "/etc/x"], target="/etc/x")
    assert plan.mode == "sudo-required"


def test_ordinary_command_needs_no_sudo():
    plan = plan_privilege(["echo", "hello"])
    assert plan.mode == "unprivileged"


def test_system_package_manager_needs_sudo():
    plan = plan_privilege(["pacman", "-S", "webkit2gtk"])
    assert plan.mode == "sudo-required"


def test_sudo_never_in_history_as_secret():
    policy.log("sudo", "ran: apt install foo", policy.SENSITIVE)
    assert policy.history()[-1]["action"] == "ran: apt install foo"


def test_router_local_for_short_chat():
    assert route("hi")["provider"] == "ollama"


def test_router_coding():
    assert route("build me a website with react")["provider"] == "openrouter"
