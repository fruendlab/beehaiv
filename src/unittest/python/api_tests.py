from unittest import TestCase
import hug
from falcon import HTTP_200, HTTP_400, HTTP_404
from pony import orm

from percept import api

api.db.bind(provider='sqlite', filename=':memory:')
api.db.generate_mapping(create_tables=True)


class TestExperimentsEndpoint(TestCase):

    def setUp(self):
        api.db.drop_all_tables(with_all_data=True)
        api.db.create_tables()
        self.expected_expr_keys = {'id', 'owner', 'name', 'trial_count'}

    def tearDown(self):
        pass

    def create_experiment_with_user(self):
        with orm.db_session():
            user = api.User(username='ANY_NAME', password='ANY_PASSWORD')
            expr = api.Experiment(owner=user, name='ANY_EXPERIMENT')
        return user.id, expr.id

    def create_user(self):
        with orm.db_session():
            user = api.User(username='SINGLE_USER', password='ANY_PASSWORD')
        return user.id

    def test_get_experiments_for_empty_experiments(self):
        resp = hug.test.get(api, '/experiments/')
        self.assertEqual(resp.status, HTTP_200)
        self.assertSequenceEqual(resp.data, [])

    def test_get_experiments_for_existing_experiments(self):
        userid, expid = self.create_experiment_with_user()

        resp = hug.test.get(api, '/experiments/')

        self.assertEqual(resp.status, HTTP_200)
        self.assertIsInstance(resp.data, list)
        first_expr = resp.data[0]
        self.assertSetEqual(set(first_expr.keys()), self.expected_expr_keys)

    def test_post_experiments_creates_and_returns(self):
        userid = self.create_user()
        resp = hug.test.post(api,
                             '/experiments/',
                             {'owner': userid, 'name': 'ANY_NAME'})

        # Return stuff
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(set(resp.data.keys()), self.expected_expr_keys)

    def test_post_experiments_fails_if_missing_arguments(self):
        resp = hug.test.post(api,
                             '/experiments/',
                             {'owner': 1})
        self.assertEqual(resp.status, HTTP_400)

    def test_get_existing_experiment(self):
        userid, expid = self.create_experiment_with_user()

        resp = hug.test.get(api, '/experiments/{}/'.format(expid))

        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(set(resp.data.keys()), self.expected_expr_keys)

    def test_get_unexisting_experiment(self):
        resp = hug.test.get(api, '/experiments/1/')
        self.assertEqual(resp.status, HTTP_404)

    def test_put_existing_experiment_change_name(self):
        userid, expid = self.create_experiment_with_user()

        resp = hug.test.put(api,
                            '/experiments/{}/'.format(expid),
                            {'name': 'OTHER_EXPERIMENT'})
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(resp.data['name'], 'OTHER_EXPERIMENT')

    def test_put_existing_experiment_change_owner(self):
        userid, expid = self.create_experiment_with_user()
        other_userid = self.create_user()

        resp = hug.test.put(api,
                            '/experiments/{}/'.format(expid),
                            {'owner': other_userid})
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(resp.data['owner'], other_userid)

    def test_put_to_non_existing_experiment_gives_404(self):
        resp = hug.test.put(api,
                            '/experiments/1/',
                            {'name': 'OTHER_EXPERIMENT'})
        self.assertEqual(resp.status, HTTP_404)

    def test_get_all_trials_for_empty_exp(self):
        userid, expid = self.create_experiment_with_user()
        resp = hug.test.get(api,
                            '/experiments/{}/trials'.format(expid))

        self.assertEqual(resp.status, HTTP_200)
        self.assertSequenceEqual(resp.data, [])

    def test_get_all_trials_for_exp(self):
        userid, expid = self.create_experiment_with_user()
        with orm.db_session():
            expr = api.Experiment[expid]
            user = api.User[userid]
            for trial in range(2):
                api.Trial(experiment=expr,
                          observer=user,
                          response='ANY_RESPONSE',
                          stimulus='ANY_STIMULUS',
                          condition='ANY_CONDITION')

        resp = hug.test.get(api,
                            '/experiments/{}/trials'.format(expid))

        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(len(resp.data), 2)

    def test_get_all_trials_from_nonexisting_exp(self):
        resp = hug.test.get(api,
                            '/experiments/1/trials')
        self.assertEqual(resp.status, HTTP_404)
