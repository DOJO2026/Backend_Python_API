import pyodbc
import json
from app.schemas.chat import ChatMessage
from app.db.get_db_connection import get_db_connection
from app.services.get_sources_count import get_sources_count

def new_assistant_message(conv_id: int, assistant_message: ChatMessage):
    try:
        conn = get_db_connection()
        if conn:
            conn.autocommit = False
            cursor = conn.cursor()
            m_seq=cursor.execute("SELECT ISNULL(MAX(M_SEQ),0)+1 FROM DBO.MESSAGE WHERE M_CONVERSATION_ID = ?", (conv_id,)).fetchval()
            m_sources=json.dumps(assistant_message.sources) if assistant_message.sources is not None else None
            m_tools_used=json.dumps(assistant_message.tools_used) if assistant_message.tools_used is not None else None
            sources_count = get_sources_count()
            cursor.execute("""
                INSERT INTO DBO.MESSAGE(M_CONVERSATION_ID,M_USER_ID,M_SEQ,M_ROLE,M_CONTENT,M_SOURCES,M_STATUS,
                M_FEEDBACK,M_MODEL_USED,M_INTERACTIVE_TYPE,M_CLAIM_DETAILS,M_BLOCKED,M_TOOLS_USED,M_CREATED_AT)
                VALUES (?, '', ?, 'assistant', ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSDATETIME())
                           """,
                (
                  conv_id,m_seq,assistant_message.content,
                  m_sources,assistant_message.status,assistant_message.feedback,
                  assistant_message.model_used,assistant_message.interactive_type,
                  assistant_message.claim_details,assistant_message.blocked,m_tools_used
                 ))
            cursor.execute("""
                UPDATE DBO.CONVERSATION
                SET C_MESSAGE_COUNT=C_MESSAGE_COUNT+1,C_CITED_SOURCES_COUNT= ?,C_UPDATED_AT = SYSDATETIME()
                WHERE C_ID = ?
               """, (sources_count, conv_id))
            
            conn.commit()
        
    except pyodbc.Error as db_ex:
        conn.rollback()
        raise db_ex
    finally:
        cursor.close()
        conn.close()