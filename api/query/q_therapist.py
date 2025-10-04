from flask import json
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from ..utils.config import get_connection


def get_therapists(status_therapist=None):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = """
                SELECT 
                    tp.id, tp.user_id, u.name, u.email, u.phone,
                    tp.bio, tp.experience_years, tp.specialization,
                    tp.average_rating, tp.total_reviews,
                    tp.status_therapist, tp.working_hours,
                    tp.created_at, tp.updated_at
                FROM therapist_profiles tp
                JOIN users u ON tp.user_id = u.id
                WHERE tp.status = 1 AND u.status = 1
            """
            params = {}
            # filter opsional
            if status_therapist:
                query += " AND tp.status_therapist = :status_therapist"
                params["status_therapist"] = status_therapist

            query += " ORDER BY tp.average_rating DESC NULLS LAST, tp.created_at DESC"

            result = connection.execute(text(query), params).mappings().all()

            return [
                {
                    "id_therapist": row["id"],
                    "user_id": row["user_id"],
                    "name": row["name"],
                    "email": row["email"],
                    "phone": row["phone"],
                    "bio": row["bio"],
                    "experience_years": row["experience_years"],
                    "specialization": row["specialization"],
                    "average_rating": float(row["average_rating"]) if row["average_rating"] else None,
                    "total_reviews": row["total_reviews"],
                    "status_therapist": row["status_therapist"],
                    "working_hours": row["working_hours"],
                    "created_at": str(row["created_at"]),
                    "updated_at": str(row["updated_at"]) if row["updated_at"] else None
                }
                for row in result
            ]
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []

def add_therapist(payload):
    engine = get_connection()
    try:
        with engine.begin() as connection:  # otomatis commit/rollback
            # Insert ke users
            user_result = connection.execute(
                text("""
                    INSERT INTO users (name, email, password, phone, role, status, created_at)
                    VALUES (:name, :email, :password, :phone, 'therapist', 1, NOW())
                    RETURNING id, name, email, phone, role, status, created_at;
                """),
                {
                    "name": payload["name"],
                    "email": payload["email"],
                    "password": generate_password_hash(payload["password"]),
                    "phone": payload.get("phone")
                }
            ).mappings().fetchone()
            if not user_result:
                return None
            # Insert ke therapist_profiles
            profile_result = connection.execute(
                text("""
                    INSERT INTO therapist_profiles
                    (user_id, bio, experience_years, specialization, status_therapist, average_rating, total_reviews, status, created_at, updated_at)
                    VALUES (:user_id, :bio, :experience_years, :specialization, :status_therapist, 0.0, 0, 1, NOW(), NOW())
                    RETURNING id, bio, experience_years, specialization, status_therapist, average_rating, total_reviews, created_at, updated_at;
                """),
                {
                    "user_id": user_result["id"],
                    "bio": payload.get("bio"),
                    "experience_years": payload.get("experience_years", 0),
                    "specialization": payload.get("specialization"),
                    "status_therapist": payload.get("status_therapist", "available")
                }
            ).mappings().fetchone()
            return {
                "id_user": user_result["id"],
                "name": user_result["name"],
                "email": user_result["email"],
                "phone": user_result["phone"],
                "role": user_result["role"],
                "status": user_result["status"],
                "created_at": str(user_result["created_at"]),
                "therapist_profile": {
                    "id_profile": profile_result["id"],
                    "bio": profile_result["bio"],
                    "experience_years": profile_result["experience_years"],
                    "specialization": profile_result["specialization"],
                    "status_therapist": profile_result["status_therapist"],
                    "average_rating": float(profile_result["average_rating"]),
                    "total_reviews": profile_result["total_reviews"],
                    "created_at": str(profile_result["created_at"]),
                    "updated_at": str(profile_result["updated_at"])
                }
            }
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def get_therapist_by_id(id_therapist):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT u.id, u.name, u.email, u.phone, u.role, u.status, u.created_at,
                           tp.id AS profile_id, tp.bio, tp.experience_years, tp.specialization,
                           tp.average_rating, tp.total_reviews, tp.status_therapist,
                           tp.working_hours, tp.created_at AS profile_created, tp.updated_at AS profile_updated
                    FROM users u
                    JOIN therapist_profiles tp ON u.id = tp.user_id AND tp.status = 1
                    WHERE u.id = :id_therapist AND u.role = 'therapist' AND u.status = 1
                    LIMIT 1;
                """),
                {"id_therapist": id_therapist}
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
                "created_at": str(result["created_at"]),
                "therapist_profile": {
                    "id_profile": result["profile_id"],
                    "bio": result["bio"],
                    "experience_years": result["experience_years"],
                    "specialization": result["specialization"],
                    "average_rating": float(result["average_rating"]),
                    "total_reviews": result["total_reviews"],
                    "status_therapist": result["status_therapist"],
                    "working_hours": result["working_hours"],
                    "created_at": str(result["profile_created"]),
                    "updated_at": str(result["profile_updated"])
                }
            }
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None

def update_therapist_by_id(id_therapist, payload):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            # cek apakah data ada
            result = connection.execute(
                text("SELECT id FROM therapist_profiles WHERE user_id = :id AND status = 1"),
                {"id": id_therapist}
            ).mappings().fetchone()
            if not result:
                return None
            # build field yang boleh diupdate
            fields = []
            params = {"id": id_therapist}
            
            if "bio" in payload and payload["bio"]:
                fields.append("bio = :bio")
                params["bio"] = payload["bio"]
            if "experience_years" in payload:
                fields.append("experience_years = :experience_years")
                params["experience_years"] = payload["experience_years"]
            if "specialization" in payload and payload["specialization"]:
                fields.append("specialization = :specialization")
                params["specialization"] = payload["specialization"]
            if "status_therapist" in payload and payload["status_therapist"]:
                fields.append("status_therapist = :status_therapist")
                params["status_therapist"] = payload["status_therapist"]
            if "working_hours" in payload and payload["working_hours"]:
                if isinstance(payload["working_hours"], (dict, list)):
                    params["working_hours"] = json.dumps(payload["working_hours"])
                else:
                    params["working_hours"] = payload["working_hours"]
                fields.append("working_hours = :working_hours")
            # jika tidak ada field yang bisa diupdate
            if not fields:
                return None
            query = f"""
                UPDATE therapist_profiles
                SET {", ".join(fields)}, updated_at = NOW()
                WHERE user_id = :id AND status = 1
                RETURNING id, user_id, bio, experience_years, specialization,
                          average_rating, total_reviews, status_therapist,
                          working_hours, status, created_at, updated_at;
            """
            updated = connection.execute(text(query), params).mappings().fetchone()
            if updated:
                return {
                    "id_therapist": updated["id"],
                    "user_id": updated["user_id"],
                    "bio": updated["bio"],
                    "experience_years": updated["experience_years"],
                    "specialization": updated["specialization"],
                    "average_rating": float(updated["average_rating"]),
                    "total_reviews": updated["total_reviews"],
                    "status_therapist": updated["status_therapist"],
                    "working_hours": updated["working_hours"],
                    "status": updated["status"],
                    "created_at": str(updated["created_at"]),
                    "updated_at": str(updated["updated_at"])
                }
            return None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def soft_delete_therapist_by_id(id_therapist):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            # Ambil user_id dulu biar bisa update table users
            therapist = connection.execute(
                text("""
                    SELECT id, user_id FROM therapist_profiles
                    WHERE user_id = :id_therapist AND status = 1
                    LIMIT 1
                """),
                {"id_therapist": id_therapist}
            ).mappings().fetchone()
            if not therapist:
                return None
            # Soft delete di therapist_profiles
            result = connection.execute(
                text("""
                    UPDATE therapist_profiles
                    SET status = 0, updated_at = NOW()
                    WHERE user_id = :id_therapist
                    RETURNING id, user_id, bio, experience_years, specialization,
                              average_rating, total_reviews, status_therapist,
                              working_hours, status, created_at, updated_at;
                """),
                {"id_therapist": id_therapist}
            ).mappings().fetchone()
            # Soft delete juga di users
            connection.execute(
                text("""
                    UPDATE users
                    SET status = 0
                    WHERE id = :user_id
                """),
                {"user_id": therapist["user_id"]}
            )
            if result:
                return {
                    "id_therapist": result["id"],
                    "user_id": result["user_id"],
                    "bio": result["bio"],
                    "experience_years": result["experience_years"],
                    "specialization": result["specialization"],
                    "average_rating": float(result["average_rating"]),
                    "total_reviews": result["total_reviews"],
                    "status_therapist": result["status_therapist"],
                    "working_hours": result["working_hours"],
                    "status": result["status"],  # sekarang 0
                    "created_at": str(result["created_at"]),
                    "updated_at": str(result["updated_at"])
                }
            return None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None

def update_therapist_status(id_therapist, status_therapist):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    UPDATE therapist_profiles
                    SET status_therapist = :status_therapist, updated_at = NOW()
                    WHERE user_id = :id_therapist AND status = 1
                    RETURNING id, user_id, bio, experience_years, specialization,
                              average_rating, total_reviews, status_therapist,
                              working_hours, status, created_at, updated_at;
                """),
                {"id_therapist": id_therapist, "status_therapist": status_therapist}
            ).mappings().fetchone()
            if result:
                return {
                    "id_therapist": result["id"],
                    "user_id": result["user_id"],
                    "bio": result["bio"],
                    "experience_years": result["experience_years"],
                    "specialization": result["specialization"],
                    "average_rating": float(result["average_rating"]),
                    "total_reviews": result["total_reviews"],
                    "status_therapist": result["status_therapist"],
                    "working_hours": result["working_hours"],
                    "status": result["status"],
                    "created_at": str(result["created_at"]),
                    "updated_at": str(result["updated_at"])
                }
            return None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
