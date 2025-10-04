from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy.exc import SQLAlchemyError

from .utils.response import success_response, error_response
from .query.q_reviews import create_review, get_review_by_id, get_reviews_by_therapist

reviews_ns = Namespace('reviews', description='Endpoint untuk manajemen review')

review_model = reviews_ns.model('CreateReview', {
    "booking_id": fields.Integer(required=True, description="ID Booking yang akan direview"),
    "rating": fields.Integer(required=True, description="Rating (1-5)"),
    "comment": fields.String(required=False, description="Komentar tambahan")
})

@reviews_ns.route('')
class ReviewCreateResource(Resource):
    @jwt_required()
    @reviews_ns.expect(review_model)
    def post(self):
        """User buat review untuk booking yang sudah completed"""
        claims = get_jwt()
        user_id = get_jwt_identity()
        role = claims.get("role")

        if role != "user":
            return error_response("Forbidden: only users can create reviews", 403)

        payload = request.get_json()
        if not payload:
            return error_response("No input data provided", 400)

        booking_id = payload.get("booking_id")
        rating = payload.get("rating")
        comment = payload.get("comment")

        if not booking_id or not rating:
            return error_response("booking_id and rating are required", 400)

        if rating < 1 or rating > 5:
            return error_response("Rating must be between 1 and 5", 400)

        try:
            new_review = create_review(user_id, booking_id, rating, comment)
            if not new_review:
                return error_response("Booking not found, not completed, or already reviewed", 400)
            return success_response("Review created successfully", new_review, 201)
        except SQLAlchemyError as e:
            reviews_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)


@reviews_ns.route('/therapist/<int:therapist_id>')
class ReviewListByTherapistResource(Resource):
    @jwt_required()
    def get(self, therapist_id):
        """List review untuk terapis tertentu"""
        try:
            reviews = get_reviews_by_therapist(therapist_id)
            if not reviews:
                return success_response("No reviews found", [], 200)
            return success_response("Reviews retrieved successfully", reviews, 200)
        except SQLAlchemyError as e:
            reviews_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)


@reviews_ns.route('/<int:id_review>')
class ReviewDetailResource(Resource):
    @jwt_required()
    def get(self, id_review):
        """Get detail review tertentu"""
        try:
            review = get_review_by_id(id_review)
            if not review:
                return error_response("Review not found", 404)
            return success_response("Review retrieved successfully", review, 200)
        except SQLAlchemyError as e:
            reviews_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)
