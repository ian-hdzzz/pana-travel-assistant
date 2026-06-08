import json
import time

_sessions: dict[str, dict] = {}


def get_session(user_id: str) -> dict | None:
    session = _sessions.get(user_id)
    if session and time.time() - session.get("last_active", 0) > 7200:
        del _sessions[user_id]
        return None
    return session


def update_session(user_id: str, language: str, register: str, origin: str, message: str, response: str):
    session = _sessions.get(user_id, {
        "language": language,
        "register": register,
        "origin": origin,
        "history": [],
        "created_at": time.time()
    })

    session["language"] = language
    session["register"] = register
    session["origin"] = origin
    session["last_active"] = time.time()

    session["history"].append({"role": "user", "content": message})
    session["history"].append({"role": "assistant", "content": response})

    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]

    _sessions[user_id] = session


def get_history(user_id: str) -> list[dict]:
    session = _sessions.get(user_id)
    if not session:
        return []
    return session.get("history", [])


def clear_session(user_id: str):
    _sessions.pop(user_id, None)
