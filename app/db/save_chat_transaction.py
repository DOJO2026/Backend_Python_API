
import pyodbc
import json
from app.db.get_db_connection import get_db_connection
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.get_sources_count import get_sources_count


def save_chat_transaction(user_msg: ChatRequest, assistant_msg: ChatMessage):
    try:
        conn = get_db_connection()
        if conn:
            conn.autocommit = False
            cursor = conn.cursor()
            
            if user_msg.conversation_id :
                m_seq=cursor.execute("SELECT ISNULL(MAX(M_SEQ),0)+1 FROM DBO.MESSAGE WHERE M_CONVERSATION_ID = ?", (user_msg.conversation_id,)).fetchval()
                m_sources=json.dumps(user_msg.sources) if user_msg.sources is not None else None
                m_attached_docs=json.dumps(user_msg.attached_docs) if user_msg.attached_docs is not None else None
                cursor.execute("""
                    INSERT INTO DBO.MESSAGE(M_CONVERSATION_ID,M_USER_ID,M_SEQ,M_ROLE,M_CONTENT,M_SOURCES,
                    M_MODEL_USED,M_TEMPERATURE,M_REASONING_DEPTH,M_ATTACHED_DOCS,M_CREATED_AT)
                    VALUES (?, 'USER', ?, 'user', ?, ?, ?, ?, ?, ?, SYSDATETIME())
                                           """,
                    (
                        user_msg.conversation_id,m_seq,user_msg.content,
                        m_sources,user_msg.model_used,
                        user_msg.temperature,user_msg.reasoning_depth,
                        m_attached_docs
                    ))
                m_seq=cursor.execute("SELECT ISNULL(MAX(M_SEQ),0)+1 FROM DBO.MESSAGE WHERE M_CONVERSATION_ID = ?", (user_msg.conversation_id,)).fetchval()
                m_sources=json.dumps(assistant_msg.sources) if assistant_msg.sources is not None else None
                m_tools_used=json.dumps(assistant_msg.tools_used) if assistant_msg.tools_used is not None else None
                sources_count = get_sources_count()
                cursor.execute("""
                    INSERT INTO DBO.MESSAGE(M_CONVERSATION_ID,M_USER_ID,M_SEQ,M_ROLE,M_CONTENT,M_SOURCES,M_STATUS,
                    M_FEEDBACK,M_MODEL_USED,M_INTERACTIVE_TYPE,M_CLAIM_DETAILS,M_BLOCKED,M_TOOLS_USED,M_CREATED_AT)
                    VALUES (?, '', ?, 'assistant', ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSDATETIME())
                                           """,
                    (
                        conv_id,m_seq,assistant_msg.content,
                        m_sources,assistant_msg.status,assistant_msg.feedback,
                        assistant_msg.model_used,assistant_msg.interactive_type,
                        assistant_msg.claim_details,assistant_msg.blocked,m_tools_used
                    ))
                cursor.execute("""
                    UPDATE DBO.CONVERSATION
                    SET C_MESSAGE_COUNT=C_MESSAGE_COUNT+1,C_CITED_SOURCES_COUNT= ?,C_UPDATED_AT = SYSDATETIME()
                    WHERE C_ID = ?
                   """, (sources_count, conv_id))
                
            else
            
            
            cursor.execute("SELECT ISNULL(MAX(M_SEQ),0) FROM DBO.MESSAGE WHERE M_CONVERSATION_ID =?", (c_id,))
            c_seq = cursor.fetchone()[0] + 1
            # 1. Guardar o actualizar la conversación
            cursor.execute("""
                         IF NOT EXISTS(SELECT 1 FROM DBO.CONVERSATION WHERE C_ID = ?)
                           INSERT INTO DBO.CONVERSATION (C_USER_ID,C_TITLE,C_DATE_GROUP,C_MESSAGE_COUNT,C_CATEGORY,C_MODEL_USED,C_CITED_SOURCES_COUNT,C_CREATED_AT,C_UPDATED_AT) 
                           VALUES ('USER', ?,'Hoy', 1, ?, ?, ?, SYSDATETIME(),SYSDATETIME())
                        ELSE
                           UPDATE DBO.CONVERSATION SET C_USER_ID='USER',C_MESSAGE_COUNT=C_MESSAGE_COUNT+1,C_CITED_SOURCES_COUNT=?,
                           C_UPDATED_AT=SYSDATETIME() WHERE C_ID=?
                           """, (c_id, c_title, c_category, c_model_used, c_cited_sources_count, c_cited_sources_count, c_id))
            # 2. Guardar el mensaje del usuario en DBO.MESSAGE
            cursor.execute("""
                           INSERT INTO DBO.MESSAGE(M_CONVERSATION_ID,M_USER_ID,M_SEQ,M_ROLE,M_CONTENT,M_CREATED_AT)
                           VALUES (?, ?, 'USER', ?, 'user', ?, SYSDATETIME())
                           """, (c_id, c_seq, user_msg.content))
            
            conn.commit()
    except pyodbc.Error as db_ex:
        conn.rollback()
        raise db_ex
    finally:
        cursor.close()
        conn.close()
