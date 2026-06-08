PHONE_PREFIX_MAP = {
    "+58": ("es", "venezolano_full", "Venezuela"),
    "+57": ("es", "latam_neutral", "Colombia"),
    "+52": ("es", "latam_neutral", "Mexico"),
    "+54": ("es", "latam_neutral", "Argentina"),
    "+56": ("es", "latam_neutral", "Chile"),
    "+51": ("es", "latam_neutral", "Peru"),
    "+593": ("es", "latam_neutral", "Ecuador"),
    "+591": ("es", "latam_neutral", "Bolivia"),
    "+595": ("es", "latam_neutral", "Paraguay"),
    "+598": ("es", "latam_neutral", "Uruguay"),
    "+506": ("es", "latam_neutral", "Costa Rica"),
    "+507": ("es", "latam_neutral", "Panama"),
    "+503": ("es", "latam_neutral", "El Salvador"),
    "+502": ("es", "latam_neutral", "Guatemala"),
    "+504": ("es", "latam_neutral", "Honduras"),
    "+505": ("es", "latam_neutral", "Nicaragua"),
    "+34": ("es", "spanish_formal", "Spain"),
    "+1": ("en", "international_en", "US/Canada"),
    "+44": ("en", "international_en", "UK"),
    "+61": ("en", "international_en", "Australia"),
    "+55": ("pt", "international_pt", "Brazil"),
    "+351": ("pt", "international_pt", "Portugal"),
    "+33": ("fr", "international_fr", "France"),
    "+49": ("de", "international_de", "Germany"),
    "+43": ("de", "international_de", "Austria"),
    "+41": ("de", "international_de", "Switzerland"),
    "+39": ("it", "international_it", "Italy"),
}

VENEZUELAN_MARKERS = [
    "chamo", "chama", "pana", "marico", "verga", "vaina", "chevere", "chévere",
    "burda", "ladilla", "arrecho", "arrechisimo", "coño", "vale", "mardito",
    "pajuo", "guaro", "arepa", "hallaca", "patria", "broma"
]

LANGUAGE_MARKERS = {
    "es": ["hola", "que", "como", "donde", "quiero", "puedo", "necesito", "gracias", "por favor", "tengo", "estoy", "voy", "para", "cuando", "cuanto"],
    "en": ["hello", "hi", "how", "where", "what", "want", "can", "need", "thanks", "please", "have", "going", "would", "looking", "tell"],
    "pt": ["olá", "oi", "como", "onde", "quero", "posso", "preciso", "obrigado", "por favor", "tenho", "estou", "vou", "para", "quando", "quanto"],
    "fr": ["bonjour", "salut", "comment", "où", "veux", "peux", "besoin", "merci", "s'il vous plaît", "suis", "vais", "pour", "quand", "combien"],
    "de": ["hallo", "wie", "wo", "was", "möchte", "kann", "brauche", "danke", "bitte", "habe", "bin", "gehe", "wann", "wieviel"],
    "it": ["ciao", "come", "dove", "cosa", "voglio", "posso", "bisogno", "grazie", "per favore", "ho", "sono", "vado", "quando", "quanto"]
}


def detect_from_phone(phone_number: str) -> dict | None:
    if not phone_number:
        return None
    clean = phone_number.replace("whatsapp:", "").replace(" ", "").replace("-", "")
    for prefix, (lang, register, origin) in sorted(PHONE_PREFIX_MAP.items(), key=lambda x: -len(x[0])):
        if clean.startswith(prefix):
            return {"language": lang, "register": register, "origin": origin}
    return None


def detect_from_message(text: str) -> dict:
    lower = text.lower()

    for marker in VENEZUELAN_MARKERS:
        if marker in lower:
            return {"language": "es", "register": "venezolano_full", "origin": "Venezuela (detected from language)"}

    scores = {}
    for lang, markers in LANGUAGE_MARKERS.items():
        scores[lang] = sum(1 for m in markers if m in lower.split())

    if not any(scores.values()):
        for lang, markers in LANGUAGE_MARKERS.items():
            scores[lang] = sum(1 for m in markers if m in lower)

    best_lang = max(scores, key=scores.get) if any(scores.values()) else "es"

    register_map = {
        "es": "latam_neutral",
        "en": "international_en",
        "pt": "international_pt",
        "fr": "international_fr",
        "de": "international_de",
        "it": "international_it"
    }

    return {
        "language": best_lang,
        "register": register_map.get(best_lang, "latam_neutral"),
        "origin": f"Unknown (detected {best_lang} from message)"
    }


def detect_language_and_register(phone_number: str, message: str, existing_session: dict | None = None) -> dict:
    if existing_session and existing_session.get("register"):
        msg_detection = detect_from_message(message)
        if msg_detection["language"] != existing_session["language"]:
            return msg_detection
        return existing_session

    phone_detection = detect_from_phone(phone_number)
    if phone_detection:
        return phone_detection

    return detect_from_message(message)
