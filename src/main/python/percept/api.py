import hug
from pony import orm
import falcon

from .models import db, Experiment, Trial, User
from . import crypto

basic_auth = hug.http(requires=hug.authentication.basic(crypto.verify_user))
token_auth = hug.http(requires=hug.authentication.token(crypto.verify_token))
admin_auth = hug.http(requires=hug.authentication.token(crypto.verify_admin))


# End point /experiments/
@admin_auth.get('/experiments/')
def get_all_experiments():
    with orm.db_session():
        owners_experiments = orm.select(e for e in Experiment)
        return [expr.summary()
                for expr in owners_experiments]


@admin_auth.get('/experiments/{exp_id}/')
def get_experiments(exp_id: int, response):
    with orm.db_session():
        try:
            return Experiment[exp_id].summary()
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404


@admin_auth.post('/experiments/')
def post_experiments(body, response):
    if not ('owner' in body and 'name' in body):
        response.status = falcon.HTTP_400
        return
    with orm.db_session():
        owner = User[body['owner']]
        expr = Experiment(owner=owner,
                          name=body['name'],
                          variable_names=body['variable_names'])
    with orm.db_session():
        return expr.summary()


@admin_auth.put('/experiments/{exp_id}/')
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
@admin_auth.get('/experiments/{exp_id}/trials/')
def get_all_experiments_trials(exp_id: int, response):
    with orm.db_session():
        try:
            expr = Experiment[exp_id]
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404
            return
        return [trial.summary() for trial in expr.trials]


@token_auth.post('/experiments/{exp_id}/trials/')
def post_experiments_trials(exp_id: int, body, response):
    with orm.db_session():
        try:
            expr = Experiment[exp_id]
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404
            return

        try:
            observer = User[body.pop('observer')]
            trial_data = ','.join([body.pop(key)
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


@admin_auth.get('/experiments/{exp_id}/trials/{trial_id}/')
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
@hug.post('/users/')
def post_users(body, response):
    try:
        with orm.db_session():
            user = User(username=body['username'], password=body['password'])
        return user.safe_json()
    except orm.TransactionIntegrityError:
        response.status = falcon.HTTP_409
        return


@admin_auth.get('/users/')
def get_all_users():
    with orm.db_session():
        return [user.safe_json() for user in orm.select(user for user in User)]


@token_auth.put('/users/{user_id}/')
def put_users(user_id: int, body, response, user: hug.directives.user):
    with orm.db_session():
        user_ = User[user_id]
        if not set(body.keys()).issubset({'username', 'password'}):
            response.status = falcon.HTTP_400
            return
        for key, value in body.items():
            setattr(user_, key, value)
        if check(user, user_):
            return user_.safe_json()
        else:
            response.status = falcon.HTTP_401


@token_auth.get('/users/{user_id}/')
def get_users(user_id: int, response, user: hug.directives.user):
    with orm.db_session():
        try:
            user_ = User[user_id]
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404
            return
        if check(user, user_):
            return user_.safe_json()
        response.status = falcon.HTTP_401


@basic_auth.get('/token/')
def get_token(user: hug.directives.user):
    return crypto.create_token(user)


@orm.db_session()
def check(username, user):
    try:
        active_user = User.get(username=username)
    except orm.ObjectNotFound:
        return False
    if username == user.username or active_user.isadmin:
        return True
    else:
        return False
