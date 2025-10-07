from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection
from ..utils.helper import serialize_row


def create_review(user_id, booking_id, rating, comment=None):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            # Validasi booking
            booking = connection.execute(
                text("""
                    SELECT id, user_id, therapist_id, status_booking
                    FROM bookings
                    WHERE id = :booking_id AND status = 1
                """),
                {"booking_id": booking_id}
            ).mappings().fetchone()

            if not booking:
                return None
            if booking["user_id"] != int(user_id):
                return None  # user tidak boleh review booking orang lain
            if booking["status_booking"] != "completed":
                return None  # hanya bisa review booking completed

            # Cek apakah sudah ada review
            existing = connection.execute(
                text("SELECT id FROM reviews WHERE booking_id = :booking_id AND status = 1"),
                {"booking_id": booking_id}
            ).mappings().fetchone()
            if existing:
                return None  # sudah ada review

            # Insert review baru
            result = connection.execute(
                text("""
                    INSERT INTO reviews (booking_id, user_id, therapist_id, rating, comment, created_at)
                    VALUES (:booking_id, :user_id, :therapist_id, :rating, :comment, NOW())
                    RETURNING id, booking_id, user_id, therapist_id, rating, comment, created_at
                """),
                {
                    "booking_id": booking_id,
                    "user_id": user_id,
                    "therapist_id": booking["therapist_id"],
                    "rating": rating,
                    "comment": comment
                }
            ).mappings().fetchone()

            # Update average rating & total reviews di therapist_profiles
            connection.execute(
                text("""
                    UPDATE therapist_profiles
                    SET average_rating = (
                        SELECT COALESCE(AVG(rating),0) FROM reviews 
                        WHERE therapist_id = :therapist_id AND status = 1
                    ),
                    total_reviews = (
                        SELECT COUNT(*) FROM reviews 
                        WHERE therapist_id = :therapist_id AND status = 1
                    ),
                    updated_at = NOW()
                    WHERE user_id = :therapist_id
                """),
                {"therapist_id": booking["therapist_id"]}
            )

            return {
                "id_review": result["id"],
                "booking_id": result["booking_id"],
                "user_id": result["user_id"],
                "therapist_id": result["therapist_id"],
                "rating": result["rating"],
                "comment": result["comment"],
                "created_at": str(result["created_at"])
            }
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None

def get_reviews_by_therapist(therapist_id):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT 
                        r.id AS id_review,
                        r.booking_id,
                        r.user_id,
                        u.name AS user_name,
                        r.therapist_id,
                        r.rating,
                        r.comment,
                        r.created_at
                    FROM reviews r
                    JOIN users u ON r.user_id = u.id
                    WHERE r.therapist_id = :therapist_id
                      AND r.status = 1
                    ORDER BY r.created_at DESC
                """),
                {"therapist_id": therapist_id}
            ).mappings().all()
            return [serialize_row(row) for row in result]
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None

def get_review_by_id(id_review):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT r.id, r.booking_id, r.user_id, r.therapist_id,
                           r.rating, r.comment, r.created_at, r.updated_at
                    FROM reviews r
                    WHERE r.id = :id_review AND r.status = 1
                """),
                {"id_review": id_review}
            ).mappings().fetchone()
            if result:
                return {
                    "id_review": result["id"],
                    "booking_id": result["booking_id"],
                    "user_id": result["user_id"],
                    "therapist_id": result["therapist_id"],
                    "rating": result["rating"],
                    "comment": result["comment"],
                    "created_at": str(result["created_at"]),
                    "updated_at": str(result["updated_at"])
                }
            return None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None