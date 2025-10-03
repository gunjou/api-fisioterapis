from flask import request
from flask_restx import Namespace, Resource, fields
from sqlalchemy.exc import SQLAlchemyError

from .utils.response import success_response, error_response
from .query.q_auth import get_login, register_user

auth_ns = Namespace('auth', description='Endpoint Autentikasi (User, Therapist, Admin)')

login_model = auth_ns.model('Login', {
    'email': fields.String(required=True, description="Email user"),
    'password': fields.String(required=True, description="Password user")
})

register_model = auth_ns.model('Register', {
    'name': fields.String(required=True, description="Nama lengkap"),
    'email': fields.String(required=True, description="Email"),
    'password': fields.String(required=True, description="Password"),
    'phone': fields.String(required=False, description="Nomor telepon"),
    'role': fields.String(required=False, description="Role user (default=user)", enum=['user', 'therapist', 'admin'])
})

@auth_ns.route('/login')
class LoginResource(Resource):
    @auth_ns.expect(login_model)
    def post(self):
        """Login menggunakan email + password"""
        payload = request.get_json()

        if not payload.get('email') or not payload.get('password'):
            return error_response("Email and password are required", 400)

        try:
            jwt_response = get_login(payload)
            if jwt_response is None:
                return error_response("Invalid email or password", 401)
            return success_response("Login success", jwt_response, 200)
        except SQLAlchemyError as e:
            auth_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)
        

@auth_ns.route('/register')
class RegisterResource(Resource):
    @auth_ns.expect(register_model)
    def post(self):
        """Register user baru (User/Therapist/Admin)"""
        payload = request.get_json()

        if not payload.get('name') or not payload.get('email') or not payload.get('password'):
            return error_response("Name, email and password are required", 400)

        try:
            new_user = register_user(payload)
            if not new_user:
                return error_response("Failed to register user", 500)
            if "error" in new_user:
                return error_response(new_user["error"], 400)
            return success_response("Register success", new_user, 201)
        except SQLAlchemyError as e:
            auth_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)