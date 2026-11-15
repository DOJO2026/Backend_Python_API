
from app.db.get_db_connection import get_db_connection


def get_list_messages_by_conversation(conversation_id: str):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn:
            raise Exception("No se pudo establecer la conexión con la base de datos.")

        cursor = conn.cursor()
        cursor.execute("""
            SELECT 'msg-'+CAST(M_SEQ AS VARCHAR(20)) AS id,
            'chat-'+CAST(M_CONVERSATION_ID AS VARCHAR(20)) AS conversationId,
            M_ROLE role, M_CONTENT content,M_CREATED_AT timestamp,M_MODEL_USED modelUsed,
            M_STATUS status, M_FEEDBACK feedback,M_INTERACTIVE_TYPE interactiveType,
            M_CLAIM_DETAILS claimDetails,M_SOURCES sources 
            FROM DBO.MESSAGE
            WHERE M_CONVERSATION_ID = ?
            ORDER BY M_SEQ ASC
        """, (conversation_id,))

        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()