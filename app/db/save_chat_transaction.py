from app.db.get_db_connection import get_db_connection


def save_chat_transaction(c_id: int, c_title: str, c_category: str, c_model_used: str, c_cited_sources_count: int
                          ):
    conn = get_db_connection()
    if conn:
        conn.autocommit = False
        cursor = conn.cursor()
        try:
            # 1. Guardar o actualizar la conversación
            cursor.execute("""
                         IF NOT EXISTS(SELECT 1 FROM DBO.CONVERSATION WHERE C_ID = ?)
                           INSERT INTO DBO.CONVERSATION (C_ID,C_USER_ID,C_TITLE,C_DATE_GROUP,C_MESSAGE_COUNT,C_CATEGORY,C_MODEL_USED,C_CITED_SOURCES_COUNT,C_CREATED_AT,C_UPDATED_AT) 
                           VALUES (?, 'USER', ?,'Hoy', 1, ?, ?, ?, SYSDATETIME(),SYSDATETIME())
                        ELSE
                           UPDATE DBO.CONVERSATION SET C_USER_ID='USER',C_MESSAGE_COUNT=C_MESSAGE_COUNT+1,C_CITED_SOURCES_COUNT=?,
                           C_UPDATED_AT=SYSDATETIME() WHERE C_ID=?
                           """, (c_id, c_id, c_title, c_category, c_model_used, c_cited_sources_count, c_cited_sources_count, c_id))
            # 2. Guardar el mensaje del usuario en DBO.MESSAGE
            cursor.execute("""
                           INSERT INTO DBO.MESSAGE(M_ID,M_CONVERSATION_ID,M_USER_ID,M_SEQ,M_ROLE,M_CONTENT,M_)
                           """)
            
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()

    else:
        raise ValueError(
            "No se pudo establecer la conexión a la base de datos.")
