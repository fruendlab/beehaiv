import hug
from pony import orm
import json
import falcon

from .models import db, Experiment, Trial, User, State
from . import crypto

basic_auth = hug.http(requires=hug.authentication.basic(crypto.verify_user))
token_auth = hug.http(requires=hug.authentication.token(crypto.verify_token))
admin_auth = hug.http(requires=hug.authentication.token(crypto.verify_admin))


@hug.exception()
def handle_exceptions(exception):
    if isinstance(exception, orm.ObjectNotFound):
        raise falcon.HTTPNotFound()
    elif isinstance(exception, orm.TransactionIntegrityError):
        raise falcon.HTTPConflict()
    elif isinstance(exception, orm.CacheIndexError):
        raise falcon.HTTPConflict()
    elif isinstance(exception, KeyError):
        raise falcon.HTTPBadRequest()
    else:
        raise exception


@hug.response_middleware()
def CORS(request, response, resource):
    response.set_header('Access-Control-Allow-Origin', '*')
    response.set_header('Access-Control-Allow-Methods',
                        'GET, POST, PUT, OPTIONS')
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


@admin_auth.post('/experiments/', versions=1)
def post_experiments(body, response, user: hug.directives.user):
    with orm.db_session():
        owner = User[user['id']]
        if body is None or 'name' not in body or 'variable_names' not in body:
            raise falcon.HTTPBadRequest()
        expr = Experiment(owner=owner,
                          name=body['name'],
                          variable_names=body['variable_names'])
    with orm.db_session():
        return expr.summary()


@admin_auth.get('/experiments/{exp_id}/', versions=1)
def get_experiments(exp_id: int, response):
    with orm.db_session():
        return Experiment[exp_id].summary()


@admin_auth.put('/experiments/{exp_id}/', versions=1)
def put_experiments(exp_id: int, body, response):
    with orm.db_session():
        expr = Experiment[exp_id]
        if 'name' in body:
            expr.name = body['name']
        if 'owner' in body:
            expr.owner = User[body['owner']]
        return expr.summary()


# End point /experiments/<id>/trials/
@admin_auth.get('/experiments/{exp_id}/trials/', versions=1)
def get_all_experiments_trials(exp_id: int, response, request):
    with orm.db_session():
        expr = Experiment[exp_id]
        trials = (trial.summary() for trial in expr.trials)
        return json.dumps(list(trials))


@basic_auth.post('/experiments/{exp_id}/trials/', versions=1)
def post_experiments_trials(exp_id: int,
                            body,
                            response,
                            user: hug.directives.user):
    if body is None:
        raise falcon.BadRequest()

    with orm.db_session():
        expr = Experiment[exp_id]

        observer = User[user['id']]
        trial_data = ','.join([str(body.pop(key))
                               for key in expr.variable_names.split(',')])

        if len(body):
            raise falcon.HTTPBadRequest()

        trial = expr.trials.create(observer=observer, trial_data=trial_data)

        orm.commit()
        return trial.summary()


@admin_auth.get('/experiments/{exp_id}/trials/{trial_id}/', versions=1)
def get_experiments_trials(exp_id: int, trial_id: int, response):
    with orm.db_session():
        expr = Experiment[exp_id]
        trial = Trial[trial_id]
        if trial in expr.trials:
            return trial.summary()
        else:
            raise falcon.HTTPNotFound()


@basic_auth.get('/experiments/{exp_id}/state/', versions=1)
def get_state(exp_id: int, response, user: hug.directives.user):
    with orm.db_session():
        observer = User[user['id']]
        experiment = Experiment[exp_id]
        state = State.get(observer=observer, experiment=experiment)
        if state:
            return json.loads(state.state_json)
        else:
            raise falcon.HTTPNotFound()


@basic_auth.post('/experiments/{exp_id}/state/', versions=1)
def post_state(exp_id: int, body, response, user: hug.directives.user):
    with orm.db_session():
        observer = User[user['id']]
        experiment = Experiment[exp_id]
        state = State.get(observer=observer, experiment=experiment)
        if state:
            raise falcon.HTTPBadRequest()
        if body is None or 'state' not in body:
            raise falcon.HTTPBadRequest()
        state = State(observer=observer,
                      experiment=experiment,
                      state_json=json.dumps(body['state']))
        return json.loads(state.state_json)


@basic_auth.put('/experiments/{exp_id}/state/', versions=1)
def put_state(exp_id: int, body, response, user: hug.directives.user):
    with orm.db_session():
        observer = User[user['id']]
        experiment = Experiment[exp_id]
        state = State.get(observer=observer, experiment=experiment)
        if state is None:
            raise falcon.HTTPBadRequest()
        state.state_json = json.dumps(body['state'])
        return json.loads(state.state_json)


# End point /users/
@hug.post('/users/', versions=1)
def post_users(body, response):
    with orm.db_session():
        user = User(username=body['username'], password=body['password'])
    return user.safe_json()


@admin_auth.get('/users/', versions=1)
def get_all_users():
    with orm.db_session():
        return [user.safe_json() for user in orm.select(user for user in User)]


@token_auth.put('/users/{user_id}/', versions=1)
def put_users(user_id: int, body, response, user: hug.directives.user):
    with orm.db_session():
        user_ = User[user_id]

        if not (user['isadmin'] or user['username'] == user_.username):
            raise falcon.HTTPUnauthorized()

        if not set(body.keys()).issubset({'username', 'password', 'isadmin'}):
            raise falcon.HTTPBadRequest()

        if 'isadmin' in body and not user['isadmin']:
            raise falcon.HTTPUnauthorized()

        for key, value in body.items():
            setattr(user_, key, value)
        return user_.safe_json()


@token_auth.get('/users/{user_id}/', versions=1)
def get_users(user_id: int, response, user: hug.directives.user):
    with orm.db_session():
        user_ = User[user_id]
        if not (user['isadmin'] or user['username'] == user_.username):
            raise falcon.HTTPUnauthorized()
        return user_.safe_json()


@basic_auth.get('/token/', versions=1)
def get_token(user: hug.directives.user):
    return crypto.create_token(user['id'])
