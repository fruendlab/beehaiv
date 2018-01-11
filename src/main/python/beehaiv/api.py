import hug
from pony import orm
import falcon

from .models import db, Experiment, Trial, User
from . import crypto

basic_auth = hug.http(requires=hug.authentication.basic(crypto.verify_user))
token_auth = hug.http(requires=hug.authentication.token(crypto.verify_token))
admin_auth = hug.http(requires=hug.authentication.token(crypto.verify_admin))


@hug.response_middleware()
def CORS(request, response, resource):
    response.set_header('Access-Control-Allow-Origin', '*')
    response.set_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.set_header(
        'Access-Control-Allow-Headers',
        'Authorization,Keep-Alive,User-Agent,'
        'If-Modified-Since,Cache-Control,Content-Type'
    )
    response.set_header(
        'Access-Control-Expose-Headers',
        'Authorization,Keep-Alive,User-Agent,'
        'If-Modified-Since,Cache-Control,Content-Type'
    )
    if request.method == 'OPTIONS':
        response.set_header('Access-Control-Max-Age', '1728000')
        response.set_header('Content-Type', 'text/plain charset=UTF-8')
        response.set_header('Content-Length', 0)
        response.status_code = hug.HTTP_204


# End point /experiments/
@admin_auth.get('/experiments/', versions=1)
def get_all_experiments():
    with orm.db_session():
        owners_experiments = orm.select(e for e in Experiment)
        return [expr.summary()
                for expr in owners_experiments]


@admin_auth.get('/experiments/{exp_id}/', versions=1)
def get_experiments(exp_id: int, response):
    with orm.db_session():
        try:
            return Experiment[exp_id].summary()
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404


@admin_auth.post('/experiments/', versions=1)
def post_experiments(body, response, user: hug.directives.user):
    with orm.db_session():
        owner = User.get(username=user)
        try:
            expr = Experiment(owner=owner,
                              name=body['name'],
                              variable_names=body['variable_names'])
        except KeyError:
            response.status = falcon.HTTP_400
            return
    with orm.db_session():
        return expr.summary()


@admin_auth.put('/experiments/{exp_id}/', versions=1)
def put_experiments(exp_id: int, body, response):
    with orm.db_session():
        try:
            expr = Experiment[exp_id]
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404
            return
        if 'name' in body:
            expr.name = body['name']
        if 'owner' in body:
            expr.owner = User[body['owner']]
        return expr.summary()


# End point /experiments/<id>/trials/
@admin_auth.get('/experiments/{exp_id}/trials/', versions=1)
def get_all_experiments_trials(exp_id: int, response):
    with orm.db_session():
        try:
            expr = Experiment[exp_id]
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404
            return
        return [trial.summary() for trial in expr.trials]


@basic_auth.post('/experiments/{exp_id}/trials/', versions=1)
def post_experiments_trials(exp_id: int,
                            body,
                            response,
                            user: hug.directives.user):
    with orm.db_session():
        try:
            expr = Experiment[exp_id]
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404
            return

        try:
            observer = User.get(username=user)
            trial_data = ','.join([str(body.pop(key))
                                   for key in expr.variable_names.split(',')])
        except KeyError:
            response.status = falcon.HTTP_400
            return

        if len(body):
            response.status = falcon.HTTP_400
            return

        trial = expr.trials.create(observer=observer, trial_data=trial_data)

        orm.commit()
        return trial.summary()


@admin_auth.get('/experiments/{exp_id}/trials/{trial_id}/', versions=1)
def get_experiments_trials(exp_id: int, trial_id: int, response):
    with orm.db_session():
        try:
            expr = Experiment[exp_id]
            trial = Trial[trial_id]
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404
            return
        if trial in expr.trials:
            return trial.summary()
        else:
            response.status = falcon.HTTP_404


# End point /users/
@hug.post('/users/', versions=1)
def post_users(body, response):
    try:
        with orm.db_session():
            user = User(username=body['username'], password=body['password'])
        return user.safe_json()
    except orm.TransactionIntegrityError:
        response.status = falcon.HTTP_409
        return


@admin_auth.get('/users/', versions=1)
def get_all_users():
    with orm.db_session():
        return [user.safe_json() for user in orm.select(user for user in User)]


@token_auth.put('/users/{user_id}/', versions=1)
def put_users(user_id: int, body, response, user: hug.directives.user):
    with orm.db_session():
        try:
            active_user = User.get(username=user)
            user_ = User[user_id]
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404
            return

        if not check_admin_privileges(user, user_):
            response.status = falcon.HTTP_401
            return

        if not set(body.keys()).issubset({'username', 'password', 'isadmin'}):
            response.status = falcon.HTTP_400
            return

        if 'isadmin' in body and not active_user.isadmin:
            response.status = falcon.HTTP_401
            return

        for key, value in body.items():
            setattr(user_, key, value)
        return user_.safe_json()


@token_auth.get('/users/{user_id}/', versions=1)
def get_users(user_id: int, response, user: hug.directives.user):
    with orm.db_session():
        try:
            user_ = User[user_id]
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404
            return
        if check_admin_privileges(user, user_):
            return user_.safe_json()
        response.status = falcon.HTTP_401


@basic_auth.get('/token/', versions=1)
def get_token(user: hug.directives.user):
    return crypto.create_token(user)


@orm.db_session()
def check_admin_privileges(username, user):
    try:
        active_user = User.get(username=username)
    except orm.ObjectNotFound:
        return False
    if username == user.username or active_user.isadmin:
        return True
    else:
        return False
