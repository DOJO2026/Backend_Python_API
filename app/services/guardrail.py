from pathlib import Path
from typing import List
import re
from app.services import normalize
# ---------------------------------------------------------------------------
# Guardarraíl (Trip Wire) - corre ANTES de la primera llamada al LLM.
# Si se activa, ni siquiera se decide que herramienta usar: se corta ahí.
# ---------------------------------------------------------------------------
GUARDRAIL_MESSAGE = "Lo siento, no puedo procesar mensajes que contengan lenguaje ofensivo."
BLOCKED_WORDS_FILE = Path(__file__).parent / "blocked_words.txt"


def check_trip_wire(text: str) -> bool:
    """Devuelve True si el mensaje debe bloquearse antes de llegar al LLM."""
    normalized = normalize(text)
    return any(p.search(normalized) for p in BLOCKED_PATTERNS)

def _load_blocked_patterns(path: Path) -> List[re.Pattern]:
    """Lee blocked_words.txt y compila cada línea como patrón (ignora # y vacías)."""
    if not path.exists():
        print(f"[WARN] No se encontró {path}; el guardarraíl no bloqueará nada.")
        return []
    patterns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        word = normalize(line)
        pattern = word if r"\b" in word else rf"\b{word}\b"
        patterns.append(re.compile(pattern))
    return patterns

# Se cargan una sola vez al arrancar el proceso.
BLOCKED_PATTERNS = _load_blocked_patterns(BLOCKED_WORDS_FILE)

def reload_guardrail():
    """Recarga blocked_words.txt sin reiniciar el servidor."""
    global BLOCKED_PATTERNS
    BLOCKED_PATTERNS = _load_blocked_patterns(BLOCKED_WORDS_FILE)