from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy.exc import SQLAlchemyError

from .utils.response import success_response, error_response
from .query.q_therapist import add_therapist, get_therapist_by_id, get_therapists, soft_delete_therapist_by_id, update_therapist_by_id, update_therapist_status

therapists_ns = Namespace('therapists', description='Endpoint untuk manajemen therapist')

# Parser untuk filter opsional (string, bukan dropdown)
therapist_parser = reqparse.RequestParser()
therapist_parser.add_argument(
    'status_therapist',
    type=str,
    required=False,
    help="Filter therapist by status (contoh: available, busy, off)"
)


therapist_model = therapists_ns.model('Therapist', {
    "name": fields.String(required=True, description="Nama terapis"),
    "email": fields.String(required=True, description="Email terapis"),
    "password": fields.String(required=True, description="Password"),
    "phone": fields.String(required=False, description="Nomor telepon"),
    "bio": fields.String(required=False, description="Deskripsi singkat terapis"),
    "experience_years": fields.Integer(required=False, description="Pengalaman (tahun)"),
    "specialization": fields.String(required=False, description="Spesialisasi"),
    "status_therapist": fields.String(required=False, description="Status therapist (available/busy/off)")
})

update_therapist_model = therapists_ns.model('UpdateTherapist', {
    "bio": fields.String(required=False, description="Bio therapist"),
    "experience_years": fields.Integer(required=False, description="Pengalaman (tahun)"),
    "specialization": fields.String(required=False, description="Spesialisasi therapist"),
    "status_therapist": fields.String(
        required=False,
        description="Status therapist",
        enum=['available', 'busy', 'off']
    ),
    "working_hours": fields.Raw(required=False, description="Jam kerja therapist (JSON/String)")
})

therapist_status_model = therapists_ns.model('UpdateTherapistStatus', {
    "status_therapist": fields.String(
        required=True,
        description="Status therapist",
        enum=['available', 'busy', 'off']
    )
})

@therapists_ns.route('')
class TherapistResource(Resource):
    @therapists_ns.expect(therapist_parser)
    @jwt_required()
    def get(self):
        """List semua therapist (opsional filter by status_therapist)"""
        args = therapist_parser.parse_args()
        try:
            therapists = get_therapists(status_therapist=args.get("status_therapist"))
            return success_response("Therapists fetched successfully", therapists, 200)
        except SQLAlchemyError as e:
            therapists_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)
        
    @therapists_ns.expect(therapist_model)
    @jwt_required()
    def post(self):
        """Tambah therapist baru (admin only)"""
        claims = get_jwt()
        if claims.get("role") != "admin":
            return error_response("Only admin can add therapists", 403)
        payload = request.get_json()
        try:
            new_therapist = add_therapist(payload)
            if not new_therapist:
                return error_response("Failed to create therapist", 400)
            return success_response("Therapist created successfully", new_therapist, 201)
        except SQLAlchemyError as e:
            therapists_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)
        
        
@therapists_ns.route('/<int:id_therapist>')
@therapists_ns.param('id_therapist', 'ID user therapist yang ingin diambil')
class TherapistDetailResource(Resource):
    @jwt_required()
    def get(self, id_therapist):
        """Detail profil therapist by ID (admin & user)"""
        try:
            therapist = get_therapist_by_id(id_therapist)
            if not therapist:
                return error_response("Therapist not found", 404)
            return success_response("Therapist detail fetched successfully", therapist, 200)
        except SQLAlchemyError as e:
            therapists_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)
        
    @jwt_required()
    @therapists_ns.expect(update_therapist_model)
    def put(self, id_therapist):
        """Update profil terapis (admin only atau terapis sendiri)"""
        claims = get_jwt()
        user_id = get_jwt_identity()
        
        payload = request.get_json()
        if not payload:
            return error_response("No input data provided", 400)

        try:
            # hanya admin atau terapis sendiri yang boleh update
            if claims.get("role") != "admin":
                therapist = get_therapist_by_id(id_therapist)
                if not therapist or int(therapist["user_id"]) != int(user_id):
                    return error_response("Forbidden: you can only update your own profile", 403)

            updated = update_therapist_by_id(id_therapist, payload)
            if not updated:
                return error_response("Therapist not found or update failed", 404)
            
            return success_response("Therapist updated successfully", updated, 200)
        except SQLAlchemyError as e:
            therapists_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)

    @jwt_required()
    def delete(self, id_therapist):
        """Soft delete therapist by ID (admin only)"""
        claims = get_jwt()
        if claims.get("role") != "admin":
            return error_response("Forbidden: only admin can delete therapist", 403)
        try:
            deleted = soft_delete_therapist_by_id(id_therapist)
            if not deleted:
                return error_response("Therapist not found or already deleted", 404)
            return success_response("Therapist deleted successfully", deleted, 200)
        except SQLAlchemyError as e:
            therapists_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)
        

@therapists_ns.route('/<int:id_therapist>/status')
@therapists_ns.param('id_therapist', 'ID therapist yang ingin diupdate statusnya')
class TherapistStatusResource(Resource):
    @jwt_required()
    @therapists_ns.expect(therapist_status_model)
    def put(self, id_therapist):
        """Update status therapist (admin only atau therapist sendiri)"""
        claims = get_jwt()
        user_id = get_jwt_identity()
        payload = request.get_json()

        if not payload or "status_therapist" not in payload:
            return error_response("status_therapist is required", 400)

        try:
            # hanya admin atau terapis sendiri yang boleh update
            if claims.get("role") != "admin":
                therapist = get_therapist_by_id(id_therapist)
                # print(therapist)
                if not therapist or int(therapist["id_user"]) != int(user_id):
                    return error_response("Forbidden: you can only update your own status", 403)

            updated = update_therapist_status(id_therapist, payload["status_therapist"])
            if not updated:
                return error_response("Therapist not found or update failed", 404)

            return success_response("Therapist status updated successfully", updated, 200)
        except SQLAlchemyError as e:
            therapists_ns.logger.error(f"Database error: {str(e)}")
            return error_response("Internal server error", 500)
