from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection


def create_notification(payload):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    INSERT INTO notifications (user_id, message, is_read, status, created_at)
                    VALUES (:user_id, :message, 0, 1, NOW())
                    RETURNING id, user_id, message, is_read, status, created_at;
                """),
                {"user_id": payload["user_id"], "message": payload["message"]}
            ).mappings().fetchone()
            if result:
                return {
                    "id_notification": result["id"],
                    "user_id": result["user_id"],
                    "message": result["message"],
                    "is_read": bool(result["is_read"]),
                    "status": result["status"],
                    "created_at": str(result["created_at"])
                }
            return None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def get_notifications_by_user(user_id):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            results = connection.execute(
                text("""
                    SELECT id, message, is_read, created_at
                    FROM notifications
                    WHERE user_id = :user_id AND status = 1
                    ORDER BY created_at DESC
                """),
                {"user_id": user_id}
            ).mappings().fetchall()
            return [
                {
                    "id_notification": row["id"],
                    "message": row["message"],
                    "is_read": bool(row["is_read"]),
                    "created_at": str(row["created_at"])
                }
                for row in results
            ]
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def mark_notification_as_read(id_notification, user_id):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    UPDATE notifications
                    SET is_read = 1
                    WHERE id = :id_notification AND user_id = :user_id AND status = 1
                    RETURNING id, message, is_read, created_at
                """),
                {"id_notification": id_notification, "user_id": user_id}
            ).mappings().fetchone()
            if result:
                return {
                    "id_notification": result["id"],
                    "message": result["message"],
                    "is_read": bool(result["is_read"]),
                    "created_at": str(result["created_at"])
                }
            return None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None