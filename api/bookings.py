from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy.exc import SQLAlchemyError

from .utils.response import success_response, error_response
from .query.q_bookings import create_booking, get_booking_by_id_and_role, get_bookings_by_role, soft_delete_booking_by_id, update_booking_status


bookings_ns = Namespace('bookings', description='Endpoint untuk manajemen booking')

booking_model = bookings_ns.model('CreateBooking', {
    "therapist_id": fields.Integer(required=True, description="ID therapist"),
    "location": fields.String(required=True, description="Lokasi booking"),
    "booking_time": fields.DateTime(required=True, description="Waktu booking (YYYY-MM-DD HH:MM:SS)"),
    "notes": fields.String(required=False, description="Catatan tambahan"),
})

status_parser = bookings_ns.parser()
status_parser.add_argument(
    "status_booking", type=str, required=True,
    help="Status booking (accepted, rejected, completed)", location="args"
)

@bookings_ns.route('')
class BookingsResource(Resource):
    @jwt_required()
    @bookings_ns.expect(booking_model)
    def post(self):
        """Buat booking baru (user only)"""
        claims = get_jwt()
        user_id = get_jwt_identity()
        
        # hanya user biasa yang bisa create booking
        if claims.get("role") != "user":
            return error_response("Forbidden: only user can create booking", 403)

        payload = request.get_json()
        if not payload:
            return error_response("No input data provided", 400)

        try:
            new_booking = create_booking(user_id, payload)
            if not new_booking:
                return error_response("Failed to create booking", 400)
            return success_response("Booking created successfully", new_booking, 201)
        except SQLAlchemyError as e:
            bookings_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)
        
    @jwt_required()
    def get(self):
        """List semua booking (admin bisa lihat semua, user hanya miliknya, therapist hanya yang masuk ke dia)"""
        claims = get_jwt()
        user_id = get_jwt_identity()
        role = claims.get("role")
        try:
            bookings = get_bookings_by_role(role, user_id)
            return success_response("Bookings retrieved successfully", bookings, 200)
        except SQLAlchemyError as e:
            bookings_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)


@bookings_ns.route('/<int:id_booking>')
@bookings_ns.param('id_booking', 'ID booking yang ingin diambil')
class BookingDetailResource(Resource):
    @jwt_required()
    def get(self, id_booking):
        """Detail booking tertentu (admin, user, therapist)"""
        claims = get_jwt()
        user_id = get_jwt_identity()
        role = claims.get("role")
        try:
            booking = get_booking_by_id_and_role(id_booking, role, user_id)
            if not booking:
                return error_response("Booking not found or forbidden", 404)
            return success_response("Booking detail retrieved successfully", booking, 200)
        except SQLAlchemyError as e:
            bookings_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)
        
    @jwt_required()
    def delete(self, id_booking):
        """Soft delete booking (admin, user sendiri, therapist sendiri)"""
        claims = get_jwt()
        user_id = get_jwt_identity()
        role = claims.get("role")
        try:
            deleted = soft_delete_booking_by_id(id_booking, role, user_id)
            if not deleted:
                return error_response("Booking not found or forbidden", 404)
            return success_response("Booking deleted successfully", deleted, 200)
        except SQLAlchemyError as e:
            bookings_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)


@bookings_ns.route('/<int:id_booking>/status')
@bookings_ns.param('id_booking', 'ID booking yang ingin diupdate statusnya')
class BookingStatusResource(Resource):
    @jwt_required()
    @bookings_ns.expect(status_parser)
    def put(self, id_booking):
        """Update status booking (therapist only atau admin)"""
        claims = get_jwt()
        user_id = get_jwt_identity()
        role = claims.get("role")

        args = status_parser.parse_args()
        new_status = args.get("status_booking")

        if not new_status:
            return error_response("status_booking is required", 400)

        try:
            updated = update_booking_status(id_booking, role, user_id, new_status)
            if not updated:
                return error_response("Booking not found or forbidden", 404)
            return success_response("Booking status updated successfully", updated, 200)
        except SQLAlchemyError as e:
            bookings_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)