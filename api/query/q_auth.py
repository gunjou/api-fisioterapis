from sqlalchemy import text
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from ..utils.config import get_connection

def get_login(payload):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            # Ambil user berdasarkan email
            result = connection.execute(
                text("""
                    SELECT id, name, email, password, role, status
                    FROM users
                    WHERE email = :email
                      AND status = 1
                    LIMIT 1;
                """),
                {"email": payload['email']}
            ).mappings().fetchone()
            # Cek password
            if result and result['password']:
                if check_password_hash(result['password'], payload['password']):
                    # Buat token JWT
                    access_token = create_access_token(
                        identity=str(result['id']),
                        additional_claims={"role": result['role']}
                    )
                    return {
                        'access_token': access_token,
                        'id_user': result['id'],
                        'name': result['name'],
                        'email': result['email'],
                        'role': result['role'],
                    }
            return None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def register_user(payload):
    engine = get_connection()
    try:
        with engine.begin() as connection:  # pakai begin supaya auto commit/rollback
            # Cek apakah email sudah ada
            existing = connection.execute(
                text("SELECT id FROM users WHERE email = :email AND status = 1"),
                {"email": payload['email']}
            ).fetchone()
            if existing:
                return {"error": "Email already registered"}

            hashed_password = generate_password_hash(payload['password'], method='pbkdf2:sha256')

            result = connection.execute(
                text("""
                    INSERT INTO users (name, email, password, phone, role, status, created_at)
                    VALUES (:name, :email, :password, :phone, :role, 1, NOW())
                    RETURNING id, name, email, role;
                """),
                {
                    "name": payload['name'],
                    "email": payload['email'],
                    "password": hashed_password,
                    "phone": payload.get('phone'),
                    "role": payload.get('role', 'user')  # default user
                }
            ).mappings().fetchone()
            return {
                "id_user": result["id"],
                "name": result["name"],
                "email": result["email"],
                "role": result["role"]
            }
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def register_therapist(payload):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            # Cek apakah email sudah ada
            existing = connection.execute(
                text("SELECT id FROM users WHERE email = :email AND status = 1"),
                {"email": payload['email']}
            ).fetchone()
            if existing:
                return {"error": "Email already registered"}
            # generate password hash 
            hashed_password = generate_password_hash(payload['password'])
            # Insert ke users (role = therapist)
            user_result = connection.execute(
                text("""
                    INSERT INTO users (name, email, password, phone, role, status, created_at)
                    VALUES (:name, :email, :password, :phone, 'therapist', 1, NOW())
                    RETURNING id, name, email, role;
                """),
                {
                    "name": payload['name'],
                    "email": payload['email'],
                    "password": hashed_password,
                    "phone": payload.get('phone')
                }
            ).mappings().fetchone()
            # Insert ke therapist_profiles
            connection.execute(
                text("""
                    INSERT INTO therapist_profiles (user_id, bio, experience_years, specialization, 
                        average_rating, total_reviews, status_therapist, status, created_at, updated_at)
                    VALUES (:user_id, '', 0, '', 0.0, 0, 'available', 1, NOW(), NOW())
                """),
                {"user_id": user_result["id"]}
            )
            return {
                "id_user": user_result["id"],
                "name": user_result["name"],
                "email": user_result["email"],
                "role": user_result["role"]
            }
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None

def get_user_profile(user_id):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT 
                        u.id, u.name, u.email, u.phone, u.role, u.status,
                        tp.bio, tp.experience_years, tp.specialization, 
                        tp.average_rating, tp.total_reviews, tp.status_therapist, tp.working_hours
                    FROM users u
                    LEFT JOIN therapist_profiles tp ON u.id = tp.user_id AND tp.status = 1
                    WHERE u.id = :user_id AND u.status = 1
                    LIMIT 1;
                """),
                {"user_id": user_id}
            ).mappings().fetchone()
            if not result:
                return None
            # Bentuk response
            profile = {
                "id_user": result["id"],
                "name": result["name"],
                "email": result["email"],
                "phone": result["phone"],
                "role": result["role"]
            }
            if result["role"] == "therapist":
                profile["therapist_profile"] = {
                    "bio": result["bio"],
                    "experience_years": result["experience_years"],
                    "specialization": result["specialization"],
                    "average_rating": float(result["average_rating"] or 0),
                    "total_reviews": result["total_reviews"],
                    "status_therapist": result["status_therapist"],
                    "working_hours": result["working_hours"]
                }
            return profile
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None

def get_my_profile(id_user):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            # Ambil dulu data user
            user = connection.execute(
                text("""
                    SELECT id, name, email, phone, role, status, created_at, updated_at
                    FROM users
                    WHERE id = :id_user AND status = 1
                    LIMIT 1;
                """),
                {"id_user": id_user}
            ).mappings().fetchone()

            if not user:
                return None

            # Jika user adalah therapist, tambahkan profilnya
            if user["role"] == "therapist":
                profile = connection.execute(
                    text("""
                        SELECT id AS profile_id, bio, experience_years, specialization,
                               average_rating, total_reviews, status_therapist,
                               working_hours, created_at AS profile_created, updated_at AS profile_updated
                        FROM therapist_profiles
                        WHERE user_id = :id_user AND status = 1
                        LIMIT 1;
                    """),
                    {"id_user": id_user}
                ).mappings().fetchone()
                return {
                    "id_user": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "phone": user["phone"],
                    "role": user["role"],
                    "status": user["status"],
                    "created_at": str(user["created_at"]),
                    "updated_at": str(user["updated_at"]),
                    "therapist_profile": {
                        "id_profile": profile["profile_id"] if profile else None,
                        "bio": profile["bio"] if profile else None,
                        "experience_years": profile["experience_years"] if profile else None,
                        "specialization": profile["specialization"] if profile else None,
                        "average_rating": float(profile["average_rating"]) if profile and profile["average_rating"] is not None else 0.0,
                        "total_reviews": profile["total_reviews"] if profile else 0,
                        "status_therapist": profile["status_therapist"] if profile else None,
                        "working_hours": profile["working_hours"] if profile else None,
                        "created_at": str(profile["profile_created"]) if profile else None,
                        "updated_at": str(profile["profile_updated"]) if profile else None
                    } if profile else None
                }
            # Jika user biasa (bukan therapist)
            return {
                "id_user": user["id"],
                "name": user["name"],
                "email": user["email"],
                "phone": user["phone"],
                "role": user["role"],
                "status": user["status"],
                "created_at": str(user["created_at"]),
                "updated_at": str(user["updated_at"])
            }
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None