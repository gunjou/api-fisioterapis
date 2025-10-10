from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection


def create_booking(user_id, payload):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            query = text("""
                INSERT INTO bookings (user_id, therapist_id, location, booking_time, status_booking, notes, status, created_at, updated_at)
                VALUES (:user_id, :therapist_id, :location, :booking_time, 'pending', :notes, 1, NOW(), NOW())
                RETURNING id, user_id, therapist_id, location, booking_time, status_booking, notes, status, created_at, updated_at;
            """)
            result = connection.execute(query, {
                "user_id": user_id,
                "therapist_id": payload["therapist_id"],
                "location": payload["location"],
                "booking_time": payload["booking_time"],
                "notes": payload.get("notes", None),
            }).mappings().fetchone()

            if result:
                return {
                    "id_booking": result["id"],
                    "user_id": result["user_id"],
                    "therapist_id": result["therapist_id"],
                    "location": result["location"],
                    "booking_time": str(result["booking_time"]),
                    "status_booking": result["status_booking"],
                    "notes": result["notes"],
                    "status": result["status"],
                    "created_at": str(result["created_at"]),
                    "updated_at": str(result["updated_at"]),
                }
            return None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None

def get_bookings_by_role(role, user_id):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            base_query = """
                SELECT 
                    b.id, b.user_id, u.name AS user_name, b.therapist_id, tu.name AS therapist_name, b.location,
                    b.booking_time, b.status_booking, b.notes, b.status, b.created_at, b.updated_at, r.id AS id_review
                FROM bookings b
                JOIN users u 
                    ON b.user_id = u.id AND u.status = 1
                JOIN therapist_profiles tp 
                    ON b.therapist_id = tp.id AND tp.status = 1
                JOIN users tu 
                    ON tp.user_id = tu.id AND tu.status = 1
                LEFT JOIN reviews r 
                    ON r.booking_id = b.id AND r.status = 1
                WHERE b.status = 1
            """
            params = {}
            if role == "admin":
                # Admin → lihat semua booking
                query = base_query
            elif role == "user":
                # User → hanya booking miliknya
                query = base_query + " AND b.user_id = :user_id"
                params["user_id"] = user_id
            elif role == "therapist":
                # Therapist → hanya booking yang masuk ke dia
                query = base_query + " AND tp.user_id = :user_id"
                params["user_id"] = user_id
            else:
                return []
            result = connection.execute(text(query), params).mappings().fetchall()
            bookings = []
            for row in result:
                bookings.append({
                    "id_booking": row["id"],
                    "user_id": row["user_id"],
                    "id_review": row["id_review"],  # ✅ tambahkan ID review
                    "user_name": row["user_name"],
                    "therapist_id": row["therapist_id"],
                    "therapist_name": row["therapist_name"],
                    "location": row["location"],
                    "booking_time": str(row["booking_time"]),
                    "status_booking": row["status_booking"],
                    "notes": row["notes"],
                    "status": row["status"],
                    "created_at": str(row["created_at"]),
                    "updated_at": str(row["updated_at"])
                })
            return bookings
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []


def get_booking_by_id_and_role(id_booking, role, user_id):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            base_query = """
                SELECT 
                    b.id, b.user_id, u.name AS user_name,
                    b.therapist_id, t.user_id AS therapist_user_id,
                    b.location, b.booking_time, b.status_booking,
                    b.notes, b.status, b.created_at, b.updated_at
                FROM bookings b
                JOIN users u ON b.user_id = u.id AND u.status = 1
                JOIN therapist_profiles t ON b.therapist_id = t.id AND t.status = 1
                WHERE b.status = 1 AND b.id = :id_booking
            """
            params = {"id_booking": id_booking}
            # role based filter
            if role == "admin":
                query = base_query
            elif role == "user":
                query = base_query + " AND b.user_id = :user_id"
                params["user_id"] = user_id
            elif role == "therapist":
                query = base_query + " AND t.user_id = :user_id"
                params["user_id"] = user_id
            else:
                return None
            # eksekusi query
            row = connection.execute(text(query), params).mappings().fetchone()
            if not row:
                return None
            return {
                "id_booking": row["id"],
                "user_id": row["user_id"],
                "user_name": row["user_name"],
                "therapist_id": row["therapist_id"],
                "location": row["location"],
                "booking_time": str(row["booking_time"]),
                "status_booking": row["status_booking"],
                "notes": row["notes"],
                "status": row["status"],
                "created_at": str(row["created_at"]),
                "updated_at": str(row["updated_at"])
            }
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None

def soft_delete_booking_by_id(id_booking, role, user_id):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            # Cek dulu apakah booking ada dan sesuai role
            base_query = """
                SELECT b.id, b.user_id, t.user_id AS therapist_user_id
                FROM bookings b
                JOIN therapist_profiles t ON b.therapist_id = t.id AND t.status = 1
                WHERE b.id = :id_booking AND b.status = 1
            """
            row = connection.execute(text(base_query), {"id_booking": id_booking}).mappings().fetchone()
            if not row:
                return None
            # Role-based access
            if role == "user" and row["user_id"] != user_id:
                return None
            if role == "therapist" and row["therapist_user_id"] != user_id:
                return None
            # admin boleh hapus semua
            # Soft delete → ubah status jadi 0
            deleted = connection.execute(
                text("""
                    UPDATE bookings
                    SET status = 0, updated_at = NOW()
                    WHERE id = :id_booking
                    RETURNING id, user_id, therapist_id, location, booking_time,
                              status_booking, notes, status, created_at, updated_at;
                """),
                {"id_booking": id_booking}
            ).mappings().fetchone()
            if deleted:
                return {
                    "id_booking": deleted["id"],
                    "user_id": deleted["user_id"],
                    "therapist_id": deleted["therapist_id"],
                    "location": deleted["location"],
                    "booking_time": str(deleted["booking_time"]),
                    "status_booking": deleted["status_booking"],
                    "notes": deleted["notes"],
                    "status": deleted["status"],  # sekarang 0
                    "created_at": str(deleted["created_at"]),
                    "updated_at": str(deleted["updated_at"])
                }
            return None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def update_booking_status(id_booking, role, user_id, new_status):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            # Cek booking
            row = connection.execute(
                text("""
                    SELECT b.id, b.user_id, t.user_id AS therapist_user_id
                    FROM bookings b
                    JOIN therapist_profiles t ON b.therapist_id = t.id AND t.status = 1
                    WHERE b.id = :id_booking AND b.status = 1
                """),
                {"id_booking": id_booking}
            ).mappings().fetchone()
            if not row:
                return None
            # Role-based access:
            # - Therapist hanya bisa update booking miliknya
            # - Admin bisa update semua
            if role == "therapist" and row["therapist_user_id"] != user_id:
                return None
            if role == "user":
                return None  # user tidak boleh ubah status booking
            # Update status booking
            updated = connection.execute(
                text("""
                    UPDATE bookings
                    SET status_booking = :new_status, updated_at = NOW()
                    WHERE id = :id_booking
                    RETURNING id, user_id, therapist_id, location, booking_time,
                              status_booking, notes, status, created_at, updated_at;
                """),
                {"id_booking": id_booking, "new_status": new_status}
            ).mappings().fetchone()
            if updated:
                return {
                    "id_booking": updated["id"],
                    "user_id": updated["user_id"],
                    "therapist_id": updated["therapist_id"],
                    "location": updated["location"],
                    "booking_time": str(updated["booking_time"]),
                    "status_booking": updated["status_booking"],
                    "notes": updated["notes"],
                    "status": updated["status"],
                    "created_at": str(updated["created_at"]),
                    "updated_at": str(updated["updated_at"])
                }
            return None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
