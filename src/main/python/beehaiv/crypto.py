import os
from datetime import datetime, timedelta
from base64 import b64encode
from pony import orm
import jwt

from .models import User

SECRET_KEY = os.getenv('BEEHAIV_SECRET', 'secret')


def get_basic_token(username, password):
    return 'Basic ' + b64encode(
        '{}:{}'.format(username, password).encode('utf8')
    ).decode('utf8')


def verify_user(username, password):
    with orm.db_session():
        user = User.get(username=username)
        if user.password == password:
            return {'username': user.username,
                    'id': user.id,
                    'isadmin': user.isadmin}
        else:
            return False


@orm.db_session()
def create_token(username):
    user = User.get(username=username)
    return jwt.encode({'username': username,
                       'isadmin': user.isadmin,
                       'id': user.id,
                       'exp': datetime.utcnow() + timedelta(minutes=5)},
                      SECRET_KEY,
                      algorithm='HS256')


def verify_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithm='HS256')
    except jwt.DecodeError:
        return False
    except jwt.ExpiredSignatureError:
        return False


def verify_admin(token):
    try:
        info = jwt.decode(token, SECRET_KEY, algorithm='HS256')
    except jwt.DecodeError:
        return False
    except jwt.ExpiredSignatureError:
        return False
    if info['isadmin']:
        return info
    else:
        return False
