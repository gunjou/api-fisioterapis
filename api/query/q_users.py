from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from ..utils.config import get_connection

def get_all_users():
    engine = get_connection()
    try:
        with engine.connect() as connection:
            results = connection.execute(
                text("""
                    SELECT id, name, email, phone, role, status, created_at
                    FROM users
                    WHERE role = 'user' AND status = 1
                    ORDER BY created_at DESC;
                """)
            ).mappings().fetchall()
            users = []
            for row in results:
                users.append({
                    "id_user": row["id"],
                    "name": row["name"],
                    "email": row["email"],
                    "phone": row["phone"],
                    "role": row["role"],
                    "status": row["status"],
                    "created_at": str(row["created_at"])
                })
            return users
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def create_user(payload):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            with connection.begin():  # otomatis commit/rollback
                result = connection.execute(
                    text("""
                        INSERT INTO users (name, email, password, phone, role, status, created_at)
                        VALUES (:name, :email, :password, :phone, :role, 1, NOW())
                        RETURNING id, name, email, phone, role, status, created_at;
                    """),
                    {
                        "name": payload["name"],
                        "email": payload["email"],
                        "password": generate_password_hash(payload["password"]),
                        "phone": payload.get("phone"),
                        "role": payload["role"]
                    }
                ).mappings().fetchone()
                if result:
                    return {
                        "id_user": result["id"],
                        "name": result["name"],
                        "email": result["email"],
                        "phone": result["phone"],
                        "role": result["role"],
                        "status": result["status"],
                        "created_at": str(result["created_at"])
                    }
                return None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None

def get_user_by_id(id_user):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT id, name, email, phone, role, status, created_at
                    FROM users
                    WHERE id = :id_user AND role = 'user'
                    LIMIT 1;
                """),
                {"id_user": id_user}
            ).mappings().fetchone()
            if not result:
                return None
            return {
                "id_user": result["id"],
                "name": result["name"],
                "email": result["email"],
                "phone": result["phone"],
                "role": result["role"],
                "status": result["status"],
                "created_at": str(result["created_at"])
            }
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None

def update_user_by_id(id_user, payload):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            with connection.begin():  # transaksi otomatis commit/rollback
                # Pastikan user ada dan masih aktif
                result = connection.execute(
                    text("SELECT id FROM users WHERE id = :id_user AND status = 1"),
                    {"id_user": id_user}
                ).mappings().fetchone()
                if not result:
                    return None
                # Build query dinamis hanya untuk field yang boleh diupdate
                fields = []
                params = {"id_user": id_user}
                if "name" in payload and payload["name"]:
                    fields.append("name = :name")
                    params["name"] = payload["name"]
                if "phone" in payload and payload["phone"]:
                    fields.append("phone = :phone")
                    params["phone"] = payload["phone"]
                if "password" in payload and payload["password"]:
                    fields.append("password = :password")
                    params["password"] = generate_password_hash(payload["password"])
                # Pastikan ada field yang diupdate
                if not fields:
                    return None  # tidak ada data untuk update
                query = f"""
                    UPDATE users
                    SET {", ".join(fields)}
                    WHERE id = :id_user
                    RETURNING id, name, email, phone, role, status, created_at;
                """
                updated = connection.execute(text(query), params).mappings().fetchone()
                if updated:
                    return {
                        "id_user": updated["id"],
                        "name": updated["name"],
                        "email": updated["email"],
                        "phone": updated["phone"],
                        "role": updated["role"],
                        "status": updated["status"],
                        "created_at": str(updated["created_at"])
                    }
                return None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def soft_delete_user_by_id(id_user):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            with connection.begin():  # otomatis commit/rollback
                result = connection.execute(
                    text("""
                        UPDATE users
                        SET status = 0
                        WHERE id = :id_user AND status = 1
                        RETURNING id, name, email, phone, role, status, created_at;
                    """),
                    {"id_user": id_user}
                ).mappings().fetchone()
                if result:
                    return {
                        "id_user": result["id"],
                        "name": result["name"],
                        "email": result["email"],
                        "phone": result["phone"],
                        "role": result["role"],
                        "status": result["status"],  # sekarang 0
                        "created_at": str(result["created_at"])
                    }
                return None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
