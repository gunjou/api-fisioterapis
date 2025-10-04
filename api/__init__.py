from datetime import timedelta
import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager
from flask_restx import Api

from .auth import auth_ns
from .users import users_ns
from .therapist import therapists_ns
from .bookings import bookings_ns
from .reviews import reviews_ns
from .notifications import notifications_ns


api = Flask(__name__)
CORS(api)

load_dotenv()

# JWT Configuration
api.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")
api.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=365)  # waktu login sesi
api.config['JWT_BLACKLIST_ENABLED'] = True
api.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']

jwt = JWTManager(api)

authorizations = {
    'Bearer Auth': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'Masukkan token JWT Anda dengan format: **Bearer &lt;JWT&gt;**'
    }
}

# Swagger API instance
restx_api = Api(
    api, 
    version="1.0", 
    title="Sport Massage API", 
    description="Dokumentasi Sport Massage API", 
    doc="/docs",
    authorizations=authorizations,
    security='Bearer Auth'
)

restx_api.add_namespace(auth_ns, path='/auth')
restx_api.add_namespace(users_ns, path='/users')
restx_api.add_namespace(therapists_ns, path='/therapists')
restx_api.add_namespace(bookings_ns, path='/bookings')
restx_api.add_namespace(reviews_ns, path='/reviews')
restx_api.add_namespace(notifications_ns, path='/notifications')