

def buscar_conocimiento_general(query: str) -> dict:
    headers = {"User-Agent": "ProyectoDojoRAG/1.0 (proyecto de aprendizaje)"}
    try:
        search_url = "https://es.wikipedia.org/w/api.php"
        search_params = {
            "action": "opensearch",
            "search": query,
            "limit": 1,
            "namespace": 0,
            "format": "json",
        }
        r1 = requests.get(search_url, params=search_params, headers=headers, timeout=10)
        r1.raise_for_status()
        data = r1.json()
        titles = data[1]

        if not titles:
            return {"encontrado": False, "contenido": "No se encontro informacion en Wikipedia sobre este tema."}

        title = titles[0]

        summary_url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}"
        r2 = requests.get(summary_url, headers=headers, timeout=10)
        r2.raise_for_status()
        summary_data = r2.json()

        extract = summary_data.get("extract", "")
        page_url = summary_data.get("content_urls", {}).get("desktop", {}).get("page", "")

        return {
            "encontrado": True,
            "contenido": extract,
            "fuente": page_url or f"https://es.wikipedia.org/wiki/{title}",
        }

    except Exception as ex:
        return {"encontrado": False, "contenido": f"Error al consultar Wikipedia: {ex}"}
