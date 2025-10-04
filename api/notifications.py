from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy.exc import SQLAlchemyError

from .utils.response import success_response, error_response
from .query.q_notifications import create_notification, get_notifications_by_user, mark_notification_as_read


notifications_ns = Namespace('notifications', description='Endpoint Notifikasi User/Terapis')

notification_model = notifications_ns.model('Notification', {
    "user_id": fields.Integer(required=True, description="ID user atau terapis yang menerima notifikasi"),
    "message": fields.String(required=True, description="Isi notifikasi")
})

@notifications_ns.route('')
class NotificationResource(Resource):
    @jwt_required()
    @notifications_ns.expect(notification_model)
    def post(self):
        """Buat notifikasi baru (admin/event system)"""
        claims = get_jwt()
        if claims.get("role") != "admin":
            return error_response("Forbidden: only admin can create notification", 403)

        payload = request.get_json()
        if not payload or not payload.get("user_id") or not payload.get("message"):
            return error_response("user_id and message are required", 400)

        try:
            new_notification = create_notification(payload)
            return success_response("Notification created successfully", new_notification, 201)
        except SQLAlchemyError as e:
            notifications_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)

    @jwt_required()
    def get(self):
        """List notifikasi untuk user/terapis saat ini"""
        user_id = get_jwt_identity()
        try:
            notifications = get_notifications_by_user(user_id)
            return success_response("Notifications retrieved successfully", notifications, 200)
        except SQLAlchemyError as e:
            notifications_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)
        
        
@notifications_ns.route('/<int:id_notification>/read')
@notifications_ns.param('id_notification', 'ID notifikasi yang akan ditandai sudah dibaca')
class NotificationReadResource(Resource):
    @jwt_required()
    def put(self, id_notification):
        """Tandai notifikasi sudah dibaca"""
        user_id = get_jwt_identity()
        try:
            updated = mark_notification_as_read(id_notification, user_id)
            if not updated:
                return error_response("Notification not found or cannot update", 404)
            return success_response("Notification marked as read", updated, 200)
        except SQLAlchemyError as e:
            notifications_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)