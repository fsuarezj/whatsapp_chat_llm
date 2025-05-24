from functools import wraps
from flask import current_app, g, request
import jwt
from werkzeug.exceptions import Unauthorized

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', None)
        if not auth_header or not auth_header.startswith('Bearer '):
            raise Unauthorized("Authorization header missing or invalid")

        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            g.user_id = payload['sub']  # Optionally store in Flask's global context
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError) as e:
            raise Unauthorized("Invalid or expired token")

        return f(*args, user_id=payload['sub'], **kwargs)
    return decorated
