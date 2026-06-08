from app.personality import EMERGENCY_KEYWORDS


def check_emergency(message: str) -> bool:
    lower = message.lower()
    for lang_keywords in EMERGENCY_KEYWORDS.values():
        for keyword in lang_keywords:
            if keyword in lower:
                return True
    return False
