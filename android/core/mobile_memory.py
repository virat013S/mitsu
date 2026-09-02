"""MITSU Mobile — Simple memory system for Android."""
import json
import time
from pathlib import Path
from datetime import datetime


MEMORY_DIR = Path.home() / ".mitsu" / "memory"
CONVERSATION_FILE = MEMORY_DIR / "conversations.json"
USER_FILE = MEMORY_DIR / "user.json"


def _ensure_dir():
    try:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save_json(path, data):
    try:
        _ensure_dir()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def save_conversation(message: str, response: str, mood: str = "chill"):
    """Save a conversation exchange to history."""
    data = _load_json(CONVERSATION_FILE, {"messages": []})
    messages = data.get("messages", [])

    messages.append({
        "user": message,
        "mitsu": response,
        "mood": mood,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    # Keep last 50 messages
    if len(messages) > 50:
        messages = messages[-50:]

    data["messages"] = messages
    _save_json(CONVERSATION_FILE, data)


def get_recent_conversations(limit: int = 10) -> list:
    """Get recent conversation history for context."""
    data = _load_json(CONVERSATION_FILE, {"messages": []})
    messages = data.get("messages", [])
    return messages[-limit:]


def save_user_info(key: str, value: str):
    """Save a user info field."""
    data = _load_json(USER_FILE, {})
    data[key] = {
        "value": value,
        "updated": datetime.now().strftime("%Y-%m-%d"),
    }
    _save_json(USER_FILE, data)


def get_user_info(key: str = None) -> str | dict | None:
    """Get user info. If key is None, return all."""
    data = _load_json(USER_FILE, {})
    if key is None:
        return data
    entry = data.get(key)
    if isinstance(entry, dict):
        return entry.get("value")
    return entry


def save_preference(key: str, value: str):
    """Save a user preference."""
    data = _load_json(MEMORY_DIR / "preferences.json", {})
    data[key] = value
    _save_json(MEMORY_DIR / "preferences.json", data)


def get_preferences() -> dict:
    """Get all preferences."""
    return _load_json(MEMORY_DIR / "preferences.json", {})


def format_conversation_context(limit: int = 5) -> str:
    """Format recent conversations for AI context."""
    recent = get_recent_conversations(limit)
    if not recent:
        return ""

    lines = ["Recent conversation history:"]
    for conv in recent:
        lines.append(f"User: {conv.get('user', '')}")
        lines.append(f"Mitsu: {conv.get('mitsu', '')}")
    return "\n".join(lines)
