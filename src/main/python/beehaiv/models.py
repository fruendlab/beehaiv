from pony import orm

db = orm.Database()


class Experiment(db.Entity):
    owner = orm.Required('User')
    name = orm.Required(str)
    trials = orm.Set('Trial')
    variable_names = orm.Required(str)
    _states = orm.Set('State')

    def summary(self):
        return {'id': self.id,
                'owner': self.owner.id,
                'name': self.name,
                'trial_count': len(self.trials),
                'variable_names': self.variable_names}


class Trial(db.Entity):
    experiment = orm.Required(Experiment)
    observer = orm.Required('User')
    trial_data = orm.Required(str)

    def summary(self):
        data = {'id': self.id,
                'experiment': self.experiment.id,
                'observer': self.observer.id}
        data.update({key: value
                    for key, value in
                    zip(self.experiment.variable_names.split(','),
                        self.trial_data.split(','))})
        return data


class User(db.Entity):
    username = orm.Required(str, unique=True)
    password = orm.Required(str)
    trials = orm.Set(Trial)
    experiments = orm.Set(Experiment)
    isadmin = orm.Required(bool, default=False)
    _states = orm.Set('State')

    def safe_json(self):
        return {'id': self.id,
                'username': self.username,
                'trial_count': len(self.trials),
                'experiment_count': len(self.experiments)}


class State(db.Entity):
    experiment = orm.Required(Experiment)
    observer = orm.Required(User)
    state_json = orm.Required(str)
