
TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "buscar_documentos_internos",
            "description": (
                "Busca informacion en la base de conocimiento interna de la empresa "
                "(documentos propios, PDFs cargados, ej. articulos tecnicos sobre Quarkus). "
                "Usa esta funcion cuando la pregunta sea sobre temas especificos de la empresa "
                "o de los documentos internos ."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La consulta de busqueda, reformulada de forma clara y autocontenida.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_conocimiento_general",
            "description": (
                "Busca informacion general en Wikipedia. Usa esta funcion para preguntas de "
                "cultura general, definiciones basicas, o cualquier tema que NO este relacionado "
                "con los documentos internos de la empresa (ej. '¿que es una casa?', "
                "'¿quien fue Einstein?', '¿que es la fotosintesis?')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "El tema o pregunta a buscar en Wikipedia.",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


def ejecutar_tool(nombre_tool: str, argumentos: dict) -> str:
    """Ejecuta la funcion Python correspondiente segun lo que decida el modelo."""
    if nombre_tool == "buscar_documentos_internos":
        resultado = buscar_documentos_internos(argumentos["query"])
    elif nombre_tool == "buscar_conocimiento_general":
        resultado = buscar_conocimiento_general(argumentos["query"])
    else:
        resultado = {"error": f"Tool desconocida: {nombre_tool}"}

    return json.dumps(resultado, ensure_ascii=False)