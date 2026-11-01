from app.core.config import settings
from app.services.llm import get_embedding
import requests

def search_internal_documents(query: str, top: int = 5) -> dict:
    query_vector = get_embedding(query)

    url = f"{settings.search_endpoint}/indexes/{settings.azure_search_index}/docs/search?api-version=2023-11-01"
    headers = {"Content-Type": "application/json", "api-key": settings.azure_search_key}
    body = {
        "search": query,
        "vectorQueries": [
            {"kind": "vector", "vector": query_vector, "fields": "text_vector", "k": top}
        ],
        "select": "chunk,title,chunk_id",
        "top": top,
    }
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    results = resp.json().get("value", [])

    if not results:
        return {"encontrado": False, "contenido": "No se encontro informacion relevante en los documentos internos."}

    parts = []
    titles = set()
    for i, r in enumerate(results, start=1):
        title = r.get("title", "Sin titulo")
        chunk = r.get("chunk", "")
        parts.append(f"[Fuente {i} - {title}]\n{chunk}")
        titles.add(title)

    return {"encontrado": True, "contenido": "\n\n".join(parts), "fuentes": list(titles)}
