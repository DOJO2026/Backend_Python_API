
import pyodbc
import json
from app.db.get_db_connection import get_db_connection
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.get_sources_count import get_sources_count
from app.services.infer_title_and_category import infer_title_and_category

def save_chat_transaction(user_msg: ChatRequest, assistant_msg: ChatMessage):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            raise Exception("No se pudo establecer la conexión con la base de datos.")
                
        conn.autocommit = False
        cursor = conn.cursor()
            
        sources_count = get_sources_count()
        m_attached_docs=json.dumps(user_msg.attached_docs) if user_msg.attached_docs is not None else None
        #m_sources=json.dumps(assistant_msg.sources) if assistant_msg.sources is not None else None
        m_sources = (
            json.dumps([s.model_dump() for s in assistant_msg.sources], ensure_ascii=False)
            if assistant_msg.sources else None
        )
        m_tools_used=json.dumps(assistant_msg.tools_used) if assistant_msg.tools_used is not None else None
        if user_msg.conversation_id :
            m_seq=cursor.execute("SELECT ISNULL(MAX(M_SEQ),0)+1 FROM DBO.MESSAGE WHERE M_CONVERSATION_ID = ?", (user_msg.conversation_id,)).fetchval()
            cursor.execute("""
                INSERT INTO DBO.MESSAGE(M_CONVERSATION_ID,M_USER_ID,M_SEQ,M_ROLE,M_CONTENT,
                M_MODEL_USED,M_TEMPERATURE,M_REASONING_DEPTH,M_ATTACHED_DOCS,M_CREATED_AT)
                VALUES (?, 'USER', ?, 'user', ?, ?, ?, ?, ?, SYSDATETIME())
                                        """,
                (
                    user_msg.conversation_id,m_seq,user_msg.content,user_msg.model_id,
                    user_msg.temperature,user_msg.reasoning_depth,
                    m_attached_docs
                ))    
            m_seq=m_seq+1
            cursor.execute("""
                INSERT INTO DBO.MESSAGE(M_CONVERSATION_ID,M_USER_ID,M_SEQ,M_ROLE,M_CONTENT,M_SOURCES,M_STATUS,
                M_FEEDBACK,M_MODEL_USED,M_TEMPERATURE,M_REASONING_DEPTH,M_INTERACTIVE_TYPE,M_CLAIM_DETAILS,
                M_BLOCKED,M_TOOLS_USED,M_CREATED_AT)
                VALUES (?, '', ?, 'assistant', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?, SYSDATETIME())
                                        """,
                (
                    user_msg.conversation_id,m_seq,assistant_msg.content,m_sources,assistant_msg.status,
                    assistant_msg.feedback,user_msg.model_id,user_msg.temperature,user_msg.reasoning_depth,
                    assistant_msg.interactive_type,
                    assistant_msg.claim_details,assistant_msg.blocked,m_tools_used
                ))
            cursor.execute("""
                UPDATE DBO.CONVERSATION
                SET C_MESSAGE_COUNT=C_MESSAGE_COUNT+2,C_CITED_SOURCES_COUNT= ?,C_UPDATED_AT = SYSDATETIME()
                WHERE C_ID = ?
                """, (sources_count, user_msg.conversation_id))
            conn.commit()
            return str(user_msg.conversation_id)
        else:
            title, category = infer_title_and_category(user_msg.content)
            cursor.execute("""
                INSERT INTO DBO.CONVERSATION(C_USER_ID,C_TITLE,C_DATE_GROUP,C_MESSAGE_COUNT,
                C_CATEGORY,C_MODEL_USED,C_CITED_SOURCES_COUNT,C_CREATED_AT,C_UPDATED_AT)
                OUTPUT INSERTED.C_ID
                VALUES('user',?,'Hoy',2,?,?,?,SYSDATETIME(),SYSDATETIME())
                            """,(title, category,user_msg.model_id, sources_count))
            #conv_id=cursor.execute("SELECT SCOPE_IDENTITY()").fetchval()
            conv_id = cursor.fetchval()
            cursor.execute("""
                INSERT INTO DBO.MESSAGE(M_CONVERSATION_ID,M_USER_ID,M_SEQ,M_ROLE,M_CONTENT,
                M_MODEL_USED,M_TEMPERATURE,M_REASONING_DEPTH,M_ATTACHED_DOCS,M_CREATED_AT)
                VALUES (?, 'USER', 1, 'user', ?, ?, ?, ?, ?, SYSDATETIME())
                        """,(
                                conv_id,user_msg.content,user_msg.model_id,
                                user_msg.temperature,user_msg.reasoning_depth,
                                m_attached_docs
                            ))
            cursor.execute("""
                INSERT INTO DBO.MESSAGE(M_CONVERSATION_ID,M_USER_ID,M_SEQ,M_ROLE,M_CONTENT,M_SOURCES,
                M_STATUS,M_FEEDBACK,M_MODEL_USED,M_TEMPERATURE,M_REASONING_DEPTH,M_INTERACTIVE_TYPE,M_CLAIM_DETAILS,M_BLOCKED,
                M_TOOLS_USED,M_CREATED_AT)
                VALUES (?, '', 2, 'assistant', ?, ?, ?, ?, ?,?,?, ?, ?, ?, ?, SYSDATETIME())
                        """,(
                                conv_id,assistant_msg.content,m_sources,assistant_msg.status,
                                assistant_msg.feedback,user_msg.model_id,user_msg.temperature,
                                user_msg.reasoning_depth,assistant_msg.interactive_type,
                                assistant_msg.claim_details,assistant_msg.blocked,m_tools_used
                                ))
            conn.commit()
            return str(conv_id)
    except pyodbc.Error as db_ex:
        if conn:
            conn.rollback()
        raise db_ex
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
