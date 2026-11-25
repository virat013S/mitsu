import asyncio
from mitsu.agents.registry import list_agents, get_agent
from mitsu.tools import files as F
from mitsu.permissions import policy
from mitsu.workspace.projects import scaffold


def test_agents_list():
    ids = [a["id"] for a in list_agents()]
    assert {"general", "coding", "planning", "debugging"} <= set(ids)
    assert get_agent("coding").system_addendum != ""


def test_workspace_escape_blocked(tmp_path):
    try:
        F.read(str(tmp_path), "../../etc/passwd")
        assert False, "should have raised"
    except PermissionError:
        pass


def test_write_needs_grant(tmp_path):
    try:
        F.write(str(tmp_path), "x.txt", "hi", "")
        assert False, "should have raised"
    except PermissionError:
        pass


def test_scaffold_and_read(tmp_path):
    import uuid
    tok = uuid.uuid4().hex
    policy.grant(tok)
    dest = scaffold(str(tmp_path), "python", "demo", tok)
    assert "pyproject.toml" in F.tree(dest)
    assert "demo" in F.read(dest, "README.md")
    policy.revoke(tok)


def test_shell_needs_grant():
    async def go():
        from mitsu.tools import shell
        try:
            await shell.run("echo hi", granted_token="bad")
            assert False
        except PermissionError:
            pass
    asyncio.run(go())
