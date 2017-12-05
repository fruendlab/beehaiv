import hug
from pony import orm
import falcon

db = orm.Database()

# basic_auth = hug.http(requires=hug.authentication.basic())
# token_auth = hug.http(requires=hug.authentication.token_key_authentication())


class Experiment(db.Entity):
    owner = orm.Required('User')
    name = orm.Required(str)
    trials = orm.Set('Trial')

    def summary(self):
        return {'id': self.id,
                'owner': self.owner.id,
                'name': self.name,
                'trial_count': len(self.trials)}


class Trial(db.Entity):
    experiment = orm.Required(Experiment)
    observer = orm.Required('User')
    response = orm.Required(str)
    stimulus = orm.Required(str)
    condition = orm.Required(str)
    meta = orm.Optional(str)

    def summary(self):
        return {'id': self.id,
                'experiment': self.experiment.id,
                'observer': self.observer.id,
                'response': self.response,
                'stimulus': self.stimulus,
                'condition': self.condition,
                'meta': self.meta}


class User(db.Entity):
    username = orm.Required(str, unique=True)
    password = orm.Required(str)
    trials = orm.Set(Trial)
    experiments = orm.Set(Experiment)

    def safe_json(self):
        return {'id': self.id,
                'username': self.username,
                'trial_count': len(self.trials),
                'experiment_count': len(self.experiments)}


# End point /experiments/
@hug.get('/experiments/')
def get_all_experiments():
    with orm.db_session():
        owners_experiments = orm.select(e for e in Experiment)
        return [expr.summary()
                for expr in owners_experiments]


@hug.get('/experiments/{exp_id}/')
def get_experiments(exp_id: int, response):
    with orm.db_session():
        try:
            return Experiment[exp_id].summary()
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404


@hug.post('/experiments/')
def post_experiments(body, response):
    if not ('owner' in body and 'name' in body):
        response.status = falcon.HTTP_400
        return
    with orm.db_session():
        owner = User[body['owner']]
        expr = Experiment(owner=owner, name=body['name'])
    with orm.db_session():
        return expr.summary()


@hug.put('/experiments/{exp_id}/')
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
@hug.get('/experiments/{exp_id}/trials/')
def get_all_experiments_trials(exp_id: int, response):
    with orm.db_session():
        try:
            expr = Experiment[exp_id]
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404
            return
        return [trial.summary() for trial in expr.trials]


@hug.post('/experiments/{exp_id}/trials/')
def post_experiments_trials(exp_id: int, body, response):
    with orm.db_session():
        try:
            expr = Experiment[exp_id]
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404
            return
        try:
            trial = expr.trials.create(**body)
        except ValueError:
            response.status = falcon.HTTP_400
            return
        orm.commit()
        return trial.summary()


@hug.get('/experiments/{exp_id}/trials/{trial_id}/')
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


@hug.get('/users/')
def get_all_users():
    with orm.db_session():
        return [user.safe_json() for user in orm.select(user for user in User)]


@hug.put('/users/{user_id}/')
def put_users(user_id: int, body, response):
    with orm.db_session():
        user = User[user_id]
        if not set(body.keys()).issubset({'username', 'password'}):
            response.status = falcon.HTTP_400
            return
        for key, value in body.items():
            setattr(user, key, value)
        return user.safe_json()


@hug.get('/users/{user_id}/')
def get_users(user_id: int, response):
    with orm.db_session():
        try:
            return User[user_id].safe_json()
        except orm.ObjectNotFound:
            response.status = falcon.HTTP_404
