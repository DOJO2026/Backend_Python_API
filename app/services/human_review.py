
from typing import Dict, Optional
from app.services.normalize import normalize

AFFIRMATIVE_ANSWERS = {"s", "si", "sí", "yes", "y", "claro", "dale", "ok", "vale"}
NEGATIVE_ANSWERS = {"n", "no", "nel", "nop"}
TOOLS_REQUIRING_CONFIRMATION = {"buscar_conocimiento_general"}
PENDING_CONFIRMATIONS: Dict[str, dict] = {}


def parse_confirmation(text: str) -> Optional[bool]:
    """True si es afirmativo, False si es negativo, None si no se entendio."""
    normalized = normalize(text).strip().strip("¿?!. ")
    if normalized in AFFIRMATIVE_ANSWERS:
        return True
    if normalized in NEGATIVE_ANSWERS:
        return False
    return None