from unittest import TestCase
import hug
from falcon import HTTP_200, HTTP_400, HTTP_404, HTTP_409, HTTP_401
from pony import orm
from base64 import b64encode

from beehaiv import api
from beehaiv.crypto import create_token

api.db.bind(provider='sqlite', filename=':memory:')
api.db.generate_mapping(create_tables=True)


class TestExperimentsEndpoint(TestCase):

    def setUp(self):
        api.db.drop_all_tables(with_all_data=True)
        api.db.create_tables()
        self.expected_expr_keys = {'id', 'owner', 'name', 'trial_count',
                                   'variable_names'}
        self.expected_trial_keys = {'id', 'experiment', 'observer', 'stimulus',
                                    'response', 'condition'}
        self.expected_user_keys = {'id', 'username', 'experiment_count',
                                   'trial_count'}
        self.adminid = self.create_user('ADMIN_USER', True)

    def tearDown(self):
        pass

    def create_experiment_with_user(self, ownerid=None):
        variable_names = 'stimulus,response,condition'
        with orm.db_session():
            if ownerid is None:
                user = api.User(username='ANY_NAME',
                                password='ANY_PASSWORD',
                                isadmin=True)
            else:
                user = api.User[ownerid]
            expr = api.Experiment(owner=user, name='ANY_EXPERIMENT',
                                  variable_names=variable_names)
        return user.id, expr.id

    def create_user(self, username='SINGLE_USER', isadmin=False):
        with orm.db_session():
            user = api.User(username=username,
                            password='ANY_PASSWORD',
                            isadmin=isadmin)
        return user.id

    @orm.db_session()
    def create_trials_in_experiment(self, expid, observerid, n=1):
        expr = api.Experiment[expid]
        observer = api.User[observerid]
        trials = [
            api.Trial(experiment=expr,
                      observer=observer,
                      trial_data='ANY_RESPONSE,ANY_STIMULUS,ANY_CONDITION')
            for _ in range(n)]
        orm.commit()
        return [trial.id for trial in trials]

    @orm.db_session()
    def get_header(self, userid=None, basic=False):
        if userid is None:
            userid = self.adminid
        user = api.User[userid]
        if basic:
            basic_token = b64encode(
                '{}:{}'.format(user.username, user.password).encode('utf8')
            ).decode('utf8')
            return {'Authorization': 'Basic {}'.format(basic_token)}
        else:
            return {'Authorization': create_token(user.username)}

    def test_get_experiments_for_empty_experiments(self):
        resp = hug.test.get(api, '/v1/experiments/', headers=self.get_header())
        self.assertEqual(resp.status, HTTP_200)
        self.assertSequenceEqual(resp.data, [])

    def test_get_experiments_for_existing_experiments(self):
        userid, expid = self.create_experiment_with_user()

        resp = hug.test.get(api, '/v1/experiments/', headers=self.get_header())

        self.assertEqual(resp.status, HTTP_200)
        self.assertIsInstance(resp.data, list)
        first_expr = resp.data[0]
        self.assertSetEqual(set(first_expr.keys()), self.expected_expr_keys)

    def test_post_experiments_creates_and_returns(self):
        resp = hug.test.post(api,
                             '/v1/experiments/',
                             {'name': 'ANY_NAME',
                              'variable_names': 'response,stimulus,condition'},
                             headers=self.get_header())

        # Return stuff
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(set(resp.data.keys()), self.expected_expr_keys)

    def test_post_experiments_fails_if_missing_arguments(self):
        resp = hug.test.post(api,
                             '/v1/experiments/',
                             {},
                             headers=self.get_header())
        self.assertEqual(resp.status, HTTP_400)

    def test_get_existing_experiment(self):
        userid, expid = self.create_experiment_with_user()

        resp = hug.test.get(api,
                            '/v1/experiments/{}/'.format(expid),
                            headers=self.get_header())

        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(set(resp.data.keys()), self.expected_expr_keys)

    def test_get_unexisting_experiment(self):
        resp = hug.test.get(api,
                            '/v1/experiments/1/',
                            headers=self.get_header())
        self.assertEqual(resp.status, HTTP_404)

    def test_put_existing_experiment_change_name(self):
        userid, expid = self.create_experiment_with_user()

        resp = hug.test.put(api,
                            '/v1/experiments/{}/'.format(expid),
                            {'name': 'OTHER_EXPERIMENT'},
                            headers=self.get_header())
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(resp.data['name'], 'OTHER_EXPERIMENT')

    def test_put_existing_experiment_change_owner(self):
        userid, expid = self.create_experiment_with_user()
        other_userid = self.create_user()

        resp = hug.test.put(api,
                            '/v1/experiments/{}/'.format(expid),
                            {'owner': other_userid},
                            headers=self.get_header())
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(resp.data['owner'], other_userid)

    def test_put_to_non_existing_experiment_gives_404(self):
        resp = hug.test.put(api,
                            '/v1/experiments/1/',
                            {'name': 'OTHER_EXPERIMENT'},
                            headers=self.get_header())
        self.assertEqual(resp.status, HTTP_404)

    def test_get_all_trials_for_empty_exp(self):
        userid, expid = self.create_experiment_with_user()
        resp = hug.test.get(api,
                            '/v1/experiments/{}/trials'.format(expid),
                            headers=self.get_header())

        self.assertEqual(resp.status, HTTP_200)
        self.assertSequenceEqual(resp.data, [])

    def test_get_all_trials_for_exp(self):
        userid, expid = self.create_experiment_with_user()
        self.create_trials_in_experiment(expid, userid, 2)

        resp = hug.test.get(api,
                            '/v1/experiments/{}/trials'.format(expid),
                            headers=self.get_header())

        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(len(resp.data), 2)

    def test_get_all_trials_from_nonexisting_exp(self):
        resp = hug.test.get(api,
                            '/v1/experiments/1/trials',
                            headers=self.get_header())
        self.assertEqual(resp.status, HTTP_404)

    def test_post_trial_to_experiment(self):
        userid, expid = self.create_experiment_with_user()
        resp = hug.test.post(api,
                             '/v1/experiments/{}/trials'.format(expid),
                             {'response': 'ANY_RESPONSE',
                              'stimulus': 'ANY_STIMULUS',
                              'condition': 'ANY_CONDITION'},
                             headers=self.get_header(userid, basic=True))
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(set(resp.data.keys()), self.expected_trial_keys)

    def test_post_trial_to_non_existing_exp(self):
        userid = self.create_user()
        resp = hug.test.post(api,
                             '/v1/experiments/1/trials',
                             {'response': 'ANY_RESPONSE',
                              'stimulus': 'ANY_STIMULUS',
                              'condition': 'ANY_CONDITION'},
                             headers=self.get_header(userid, basic=True))
        self.assertEqual(resp.status, HTTP_404)

    def test_post_trial_with_incomplete_specs(self):
        userid, expid = self.create_experiment_with_user()
        resp = hug.test.post(api,
                             '/v1/experiments/{}/trials'.format(expid),
                             {'response': 'ANY_RESPONSE'},
                             headers=self.get_header(userid, basic=True))
        self.assertEqual(resp.status, HTTP_400)

    def test_get_trial_with_id(self):
        userid, expid = self.create_experiment_with_user()
        trial_ids = self.create_trials_in_experiment(expid, userid)
        resp = hug.test.get(api,
                            '/v1/experiments/{}/trials/{}'.format(
                                expid,
                                trial_ids[0]),
                            headers=self.get_header())
        self.assertEqual(resp.status, HTTP_200)
        self.assertSetEqual(set(resp.data.keys()), self.expected_trial_keys)

    def test_get_trial_from_nonexisting_exp(self):
        resp = hug.test.get(api,
                            '/v1/experiments/1/trials/1',
                            headers=self.get_header())
        self.assertEqual(resp.status, HTTP_404)

    def test_get_nonexisting_trial_from_existing_exp(self):
        userid, expid = self.create_experiment_with_user()
        resp = hug.test.get(api,
                            '/v1/experiment/{}/trials/1'.format(expid),
                            headers=self.get_header())
        self.assertEqual(resp.status, HTTP_404)

    def test_get_trial_from_other_experiment(self):
        userid, expid = self.create_experiment_with_user()
        _, otherexpid = self.create_experiment_with_user(userid)
        trial_ids = self.create_trials_in_experiment(expid, userid)
        resp = hug.test.get(api,
                            '/v1/experiments/{}/trials/{}'.format(
                                otherexpid,
                                trial_ids[0]),
                            headers=self.get_header())
        self.assertEqual(resp.status, HTTP_404)

    def test_post_user(self):
        resp = hug.test.post(api, '/v1/users/', {'username': 'ANY_USERNAME',
                                                 'password': 'ANY_PASSWORD'})
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(set(resp.data.keys()), self.expected_user_keys)

    def test_post_existing_user(self):
        self.create_user()
        resp = hug.test.post(api, '/v1/users/', {'username': 'SINGLE_USER',
                                                 'password': 'ANY_PASSWORD'})
        self.assertEqual(resp.status, HTTP_409)

    def test_get_all_users_with_two_users(self):
        self.create_user()
        resp = hug.test.get(api, '/v1/users/', headers=self.get_header())
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(len(resp.data), 2)

    def test_put_user_updates_username(self):
        userid = self.create_user()
        resp = hug.test.put(api, '/v1/users/{}'.format(userid),
                            {'username': 'OTHER_USER'},
                            headers=self.get_header())
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(resp.data['username'], 'OTHER_USER')

    def test_put_user_updates_password(self):
        userid = self.create_user()
        resp = hug.test.put(api, '/v1/users/{}'.format(userid),
                            {'password': 'NEW_PASSWORD'},
                            headers=self.get_header())
        self.assertEqual(resp.status, HTTP_200)
        with orm.db_session():
            user = api.User[userid]
            self.assertEqual(user.password, 'NEW_PASSWORD')

    def test_put_user_on_invalid_key(self):
        userid = self.create_user()
        resp = hug.test.put(api, '/v1/users/{}'.format(userid),
                            {'trial_count': 5},
                            headers=self.get_header())
        self.assertEqual(resp.status, HTTP_400)

    def test_get_existing_user(self):
        userid = self.create_user()
        headers = self.get_header()

        resp = hug.test.get(api,
                            '/v1/users/{}'.format(userid),
                            headers=headers)
        self.assertEqual(resp.status, HTTP_200)
        self.assertSetEqual(set(resp.data.keys()), self.expected_user_keys)

    def test_get_nonexisting_user(self):
        headers = self.get_header()
        resp = hug.test.get(api, '/v1/users/500', headers=headers)
        self.assertEqual(resp.status, HTTP_404)


class TestFlexibleExperimentSetup(TestCase):

    def setUp(self):
        api.db.drop_all_tables(with_all_data=True)
        api.db.create_tables()

        with orm.db_session():
            admin = api.db.User(username='ADMIN_USER',
                                password='ADMIN_PASSWORD',
                                isadmin=True)
            user = api.db.User(username='ANY_USER',
                               password='ANY_PASSWORD',
                               isadmin=False)
            exp1 = api.db.Experiment(owner=user, name='EXPERIMENT1',
                                     variable_names='A,B,C')
            exp2 = api.db.Experiment(owner=user, name='EXPERIMENT2',
                                     variable_names='A,D,E')

        self.adminid = admin.id
        self.userid = user.id
        self.exp1id = exp1.id
        self.exp2id = exp2.id

    @orm.db_session()
    def get_header(self, userid=None):
        if userid is None:
            userid = self.adminid

        user = api.User[userid]
        basic_token = b64encode(
            '{}:{}'.format(user.username, user.password).encode('utf8')
        ).decode('utf8')
        return {'Authorization': 'Basic {}'.format(basic_token)}

    def test_post_trial_with_valid_layout(self):
        resp = hug.test.post(api,
                             '/v1/experiments/{}/trials'.format(self.exp1id),
                             {'A': 'a',
                              'B': 'b',
                              'C': 'c'},
                             headers=self.get_header())
        self.assertEqual(resp.status, HTTP_200)

    def test_post_trial_with_layout_of_other_exp(self):
        resp = hug.test.post(api,
                             '/v1/experiments/{}/trials'.format(self.exp2id),
                             {'A': 'a',
                              'B': 'b',
                              'C': 'c'},
                             headers=self.get_header())
        self.assertEqual(resp.status, HTTP_400)

    def test_post_trial_with_variables_from_other_exp(self):
        resp = hug.test.post(api,
                             '/v1/experiments/{}/trials'.format(self.exp1id),
                             {'A': 'a',
                              'B': 'b',
                              'C': 'c',
                              'E': 'e'},
                             headers=self.get_header())
        self.assertEqual(resp.status, HTTP_400)

    def test_post_trial_with_incomplete_specs(self):
        resp = hug.test.post(api,
                             '/v1/experiments/{}/trials'.format(self.exp1id),
                             {'A': 'a',
                              'B': 'b',
                              },
                             headers=self.get_header())
        self.assertEqual(resp.status, HTTP_400)


class TestAutentication(TestCase):

    def setUp(self):
        api.db.drop_all_tables(with_all_data=True)
        api.db.create_tables()

        with orm.db_session():
            admin = api.User(username='ADMIN',
                             password='ANY_PASSWORD',
                             isadmin=True)
            user = api.User(username='ANY_USER', password='ANY_PASSWORD')
            other_user = api.User(username='ANY_OTHER_USER',
                                  password='ANY_PASSWORD')
            orm.commit()
            self.admin_id = admin.id
            self.user_id = user.id
            self.other_user_id = other_user.id

    @orm.db_session()
    def get_header(self, userid):
        user = api.User[userid]
        return {'Authorization': create_token(user.username)}

    def test_user_can_change_own_username(self):
        resp = hug.test.put(api,
                            '/v1/users/{}'.format(self.user_id),
                            {'username': 'OTHER_NAME'},
                            headers=self.get_header(self.user_id))
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(resp.data['username'], 'OTHER_NAME')

    def test_user_can_change_own_password(self):
        resp = hug.test.put(api,
                            '/v1/users/{}'.format(self.user_id),
                            {'password': 'OTHER_PASSWORD'},
                            headers=self.get_header(self.user_id))
        self.assertEqual(resp.status, HTTP_200)

    def test_user_cannot_change_own_admin_status(self):
        resp = hug.test.put(api,
                            '/v1/users/{}'.format(self.user_id),
                            {'isadmin': True},
                            headers=self.get_header(self.user_id))
        self.assertEqual(resp.status, HTTP_401)
        with orm.db_session():
            user = api.User[self.user_id]
            self.assertFalse(user.isadmin)

    def test_admin_can_change_other_users_admin_status(self):
        resp = hug.test.put(api,
                            '/v1/users/{}'.format(self.user_id),
                            {'isadmin': True},
                            headers=self.get_header(self.admin_id))
        self.assertEqual(resp.status, HTTP_200)
        with orm.db_session():
            user = api.User[self.user_id]
            self.assertTrue(user.isadmin)

    def test_other_user_cannot_change_users_info(self):
        resp = hug.test.put(api,
                            '/v1/users/{}'.format(self.user_id),
                            {'password': 'OTHER_PASSWORD'},
                            headers=self.get_header(self.other_user_id))
        self.assertEqual(resp.status, HTTP_401)
        with orm.db_session():
            user = api.User[self.user_id]
            self.assertEqual(user.password, 'ANY_PASSWORD')
