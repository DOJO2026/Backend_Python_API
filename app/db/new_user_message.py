import pyodbc
import json
from app.schemas.chat import ChatRequest
from app.db.get_db_connection import get_db_connection
from app.services.get_sources_count import get_sources_count

def new_user_message(user_message: ChatRequest):
    try:
        conn = get_db_connection()
        if conn:
            conn.autocommit = False
            cursor = conn.cursor()
            m_seq=cursor.execute("SELECT MAX(M_SEQ)+1 FROM DBO.MESSAGE WHERE M_CONVERSATION_ID = ?", (user_message.conversation_id,)).fetchval()
            m_sources=json.dumps(user_message.sources) if user_message.sources is not None else None
            cursor.execute("""
                INSERT INTO DBO.MESSAGE(M_CONVERSATION_ID,M_USER_ID,M_SEQ,M_ROLE,M_CONTENT,M_SOURCES,
                M_MODEL_USED,M_TEMPERATURE,M_REASONING_DEPTH,M_ATTACHED_DOCS,M_CREATED_AT)
                VALUES (?, 'USER', ?, 'user', ?, ?, ?, ?, ?, ?, SYSDATETIME())
                           """,
                (
                  user_message.conversation_id,m_seq,user_message.content,
                  m_sources,user_message.model_used,
                  user_message.temperature,user_message.reasoning_depth,
                  user_message.attached_docs
                 ))
            cursor.execute("""
                UPDATE DBO.CONVERSATION
                SET C_MESSAGE_COUNT=C_MESSAGE_COUNT+1,C_UPDATED_AT = SYSDATETIME()
                WHERE C_ID = ?
               """, (user_message.conversation_id,))
            
            conn.commit()
        
    except pyodbc.Error as db_ex:
        conn.rollback()
        raise db_ex
    finally:
        cursor.close()
        conn.close()