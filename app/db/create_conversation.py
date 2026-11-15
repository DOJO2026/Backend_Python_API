
import pyodbc
from app.db.get_db_connection import get_db_connection
from app.schemas.chat import ChatRequest
from app.services.infer_title_and_category import infer_title_and_category
from app.services.get_sources_count import get_sources_count

def create_conversation(user_message:ChatRequest):
    try:
        conn = get_db_connection()
        if conn:
            conn.autocommit = False
            cursor = conn.cursor()
            
            title, category = infer_title_and_category(user_message.content)
            sources_count = get_sources_count()
            cursor.execute("""
                INSERT INTO DBO.CONVERSATION (C_USER_ID,C_TITLE,C_DATE_GROUP,C_MESSAGE_COUNT,C_CATEGORY,C_MODEL_USED,C_CITED_SOURCES_COUNT,C_CREATED_AT,C_UPDATED_AT) 
                VALUES ('USER', ?,'Hoy', 1, ?, ?, ?, SYSDATETIME(),SYSDATETIME())
            """, (title, category, user_message.model, sources_count))
            
            conv_id=cursor.execute("SELECT SCOPE_IDENTITY()")
            cursor.execute("""
                           INSERT INTO DBO.MESSAGE(M_CONVERSATION_ID,M_USER_ID,M_SEQ,M_ROLE,M_CONTENT,M_MODEL_USED,M_CREATED_AT)
                           VALUES (?, 'USER', 1, 'user',?,?,SYSDATETIME())
                           """, (conv_id, user_message.content, user_message.model))
            
            conn.commit()
    except pyodbc.Error as db_ex:
        conn.rollback()
        raise db_ex
    finally:
        cursor.close()
        conn.close()