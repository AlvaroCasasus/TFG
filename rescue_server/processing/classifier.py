import re

VALID_TAGS = ["[VICTIMA]", "[OPERARIO]", "[NO_RELEVANTE]"]

def extract_first_block(raw: str) -> str:
    """Extrae desde la primera etiqueta válida hasta la siguiente."""
    match = re.search(r"\[(VICTIMA|OPERARIO|NO_RELEVANTE)\]", raw)
    if not match:
        return ""
    start = match.start()
    rest = raw[start:]
    stop = re.search(
        r"\n\s*(\[VICTIMA\]|\[OPERARIO\]|\[NO_RELEVANTE\]|###|```)",
        rest[1:]
    )
    return rest[: stop.start() + 1].strip() if stop else rest.strip()

def classify(response: str) -> str:
    """Devuelve: 'victima', 'operario' o 'no_relevante'."""
    upper = response.upper()
    if "[VICTIMA]" in upper:
        return "victima"
    if "[OPERARIO]" in upper:
        return "operario"
    return "no_relevante"
