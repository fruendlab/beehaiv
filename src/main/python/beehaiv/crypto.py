import os
from base64 import b64encode
from pony import orm
import jwt

from .models import User

SECRET_KEY = os.getenv('BEEHAIV_SECRET', 'secret')


def get_basic_token(username, password):
    return b64encode(
        '{}:{}'.format(username, password).encode('utf8')
    ).decode('utf8')


def verify_user(username, password):
    with orm.db_session():
        try:
            user = User.get(username=username)
        except orm.ObjectNotFound:
            return False
        if user.password == password:
            return user.username
        else:
            return False


@orm.db_session()
def create_token(username):
    user = User.get(username=username)
    return jwt.encode({'username': username, 'isadmin': user.isadmin},
                      SECRET_KEY,
                      algorithm='HS256')


def verify_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithm='HS256')['username']
    except jwt.DecodeError:
        return False


def verify_admin(token):
    try:
        info = jwt.decode(token, SECRET_KEY, algorithm='HS256')
    except jwt.DecodeError:
        return False
    if info['isadmin']:
        return info['username']
    else:
        return False
