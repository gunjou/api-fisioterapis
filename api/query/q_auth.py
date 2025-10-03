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