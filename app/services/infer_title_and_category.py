
def infer_title_and_category(message):
    title = message[:40] + "..." if len(message) > 40 else message
    
    texto_lower = message.lower()
    if any(k in texto_lower for k in ["seguridad", "hack", "password", "clave"]):
        category = "Ciberseguridad"
    elif any(k in texto_lower for k in ["ley", "legal", "norma", "reglamento"]):
        category = "Legal"
    elif any(k in texto_lower for k in ["operacion", "proceso", "procedimiento"]):
        category = "Operaciones"
    elif any(k in texto_lower for k in ["finanza", "presupuesto", "inversion", "costo"]):
        category = "Finanzas"
    elif any(k in texto_lower for k in ["observabilidad", "monitoreo", "metrica"]):
        category = "Observabilidad"
    elif any(k in texto_lower for k in ["infraestructura", "servidor", "red", "hardware"]):
        category = "Infraestructura"
    elif any(k in texto_lower for k in ["base de datos", "database", "sql", "no sql"]):
        category = "Bases de Datos"
    else:
        category = "General"
    
    return title, category