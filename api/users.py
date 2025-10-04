from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from flask_restx import Namespace, Resource, fields
from sqlalchemy.exc import SQLAlchemyError

from .utils.response import success_response, error_response
from .query.q_users import create_user, get_all_users, get_user_by_id, soft_delete_user_by_id, update_user_by_id
from .query.q_auth import get_user_profile

users_ns = Namespace('users', description='Endpoint untuk manajemen users (admin only)')

# Model Swagger untuk create user
user_create_model = users_ns.model('UserCreate', {
    'name': fields.String(required=True, description="Nama lengkap"),
    'email': fields.String(required=True, description="Email user"),
    'password': fields.String(required=True, description="Password user"),
    'phone': fields.String(required=False, description="Nomor telepon"),
    'role': fields.String(required=True, description="Role user", enum=['user', 'therapist', 'admin'])
})

# Model Swagger untuk update user
user_update_model = users_ns.model('UserUpdate', {
    'name': fields.String(required=False, description="Nama user"),
    'phone': fields.String(required=False, description="Nomor telepon user"),
    'password': fields.String(required=False, description="Password baru (opsional)")
})

@users_ns.route('')
class UsersResource(Resource):
    @jwt_required()
    def get(self):
        """List semua user (admin only)"""
        claims = get_jwt()
        role = claims.get("role")
        # Hanya admin yang boleh mengakses
        if role != "admin":
            return error_response("Unauthorized: Admin only", 403)
        try:
            users = get_all_users()
            if users is None:
                return error_response("Failed to fetch users", 500)
            return success_response("Users fetched successfully", users, 200)
        except SQLAlchemyError as e:
            users_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)
        
    @jwt_required()
    @users_ns.expect(user_create_model)
    def post(self):
        """Add user baru (admin only)"""
        claims = get_jwt()
        # Hanya admin yang boleh mengakses
        if claims.get("role") != "admin":
            return error_response("Forbidden: only admin can create user", 403)
        # Ambil data dari request
        payload = request.get_json()
        if not payload:
            return error_response("No input data provided", 400)
        try:
            new_user = create_user(payload)
            if not new_user:
                return error_response("Failed to create user", 400)
            return success_response("User created successfully", new_user, 201)
        except SQLAlchemyError as e:
            users_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)


@users_ns.route('/<int:id_user>')
@users_ns.param('id_user', 'ID user yang ingin diambil/diedit/dihapus')
class UserResource(Resource):
    @jwt_required()
    def get(self, id_user):
        """Detail user by ID (admin only)"""
        try:
            user = get_user_by_id(id_user)
            if not user:
                return error_response("User not found", 404)
            return success_response("User detail fetched successfully", user, 200)
        except SQLAlchemyError as e:
            users_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)

    @jwt_required()
    @users_ns.expect(user_update_model)
    def put(self, id_user):
        """Edit user by ID (admin only atau user sendiri)"""
        payload = request.get_json()
        if not payload:
            return error_response("No input data provided", 400)
        try:
            updated_user = update_user_by_id(id_user, payload)
            if not updated_user:
                return error_response("User not found or update failed", 404)
            return success_response("User updated successfully", updated_user, 200)
        except SQLAlchemyError as e:
            users_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)

    @jwt_required()
    def delete(self, id_user):
        """Soft delete user by ID (ubah status = 0)"""
        try:
            deleted_user = soft_delete_user_by_id(id_user)
            if not deleted_user:
                return error_response("User not found or already deleted", 404)
            return success_response("User deleted successfully", deleted_user, 200)
        except SQLAlchemyError as e:
            users_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)