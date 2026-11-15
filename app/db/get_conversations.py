import pyodbc
from app.db.get_db_connection import get_db_connection

#version OLD
# def get_list_conversations():
#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         if not conn:
#             raise Exception("No se pudo establecer la conexión con la base de datos.")
        
#         cursor=conn.cursor()
#         cursor.execute("""
#             SELECT 'chat-'+CAST(C_ID AS VARCHAR(20)) AS C_ID, C_TITLE,C_UPDATED_AT,C_DATE_GROUP,C_PINNED,C_ARCHIVED,
#             C_MESSAGE_COUNT,C_CATEGORY,C_MODEL_USED,C_CITED_SOURCES_COUNT,C_TOKEN_USED 
#             FROM DBO.CONVERSATION
#             ORDER BY C_UPDATED_AT DESC
#         """)
#         columns = [col[0] for col in cursor.description]
#         return [dict(zip(columns, row)) for row in cursor.fetchall()]

#     except pyodbc.Error as db_ex:
#         if conn:
#             raise db_ex
#     finally:
#         if cursor:
#             cursor.close()
#         if conn:
#             conn.close()    

def get_list_conversations(archived: bool | None = None,
                           category: str | None = None,
                           title: str | None = None):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            raise Exception("No se pudo establecer la conexión con la base de datos.")

        # Solo se agregan los filtros que realmente vienen
        conditions = []
        params = []

        if archived is not None:
            conditions.append("C_ARCHIVED = ?")
            params.append(1 if archived else 0)

        if category:
            conditions.append("C_CATEGORY = ?")
            params.append(category)

        if title:
            conditions.append("C_TITLE LIKE ?")
            params.append(f"%{title}%")   # el % va en el valor, no en el SQL

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT 'chat-'+CAST(C_ID AS VARCHAR(20)) AS id, C_TITLE title, C_UPDATED_AT updatedAt,
                   C_DATE_GROUP dateGroup, C_PINNED pinned, C_ARCHIVED archived, C_MESSAGE_COUNT messageCount, C_CATEGORY category,
                   C_MODEL_USED modelUsed, C_CITED_SOURCES_COUNT citedSourcesCount, C_TOKEN_USED tokensUsed
            FROM DBO.CONVERSATION
            {where}
            ORDER BY C_UPDATED_AT DESC
        """, params)

        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()