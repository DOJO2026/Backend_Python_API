import unicodedata

def normalize(text: str) -> str:
    """minúsculas + sin acentos, para que 'Ofénsivo' == 'ofensivo'."""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))