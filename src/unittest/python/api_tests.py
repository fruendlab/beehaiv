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

    def test_get_experiments_for_empty_experiments(self):
        resp = hug.test.get(api, '/experiments/')
        self.assertEqual(resp.status, HTTP_200)
        self.assertSequenceEqual(resp.data, [])

    def test_get_experiments_for_existing_experiments(self):
        with orm.db_session():
            user = api.User(username='ANY_NAME', password='ANY_PASSWORD')
            api.Experiment(owner=user, name='ANY_EXPERIMENT')

        resp = hug.test.get(api, '/experiments/')

        self.assertEqual(resp.status, HTTP_200)
        self.assertIsInstance(resp.data, list)
        first_expr = resp.data[0]
        self.assertSetEqual(set(first_expr.keys()), self.expected_expr_keys)

    def test_post_experiments_creates_and_returns(self):
        with orm.db_session():
            user = api.User(username='ANY_NAME', password='ANY_PASSWORD')
        resp = hug.test.post(api,
                             '/experiments/',
                             {'owner': user.id, 'name': 'ANY_NAME'})

        # Return stuff
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(set(resp.data.keys()), self.expected_expr_keys)

    def test_post_experiments_fails_if_missing_arguments(self):
        resp = hug.test.post(api,
                             '/experiments/',
                             {'owner': 1})
        self.assertEqual(resp.status, HTTP_400)

    def test_get_existing_experiment(self):
        with orm.db_session():
            user = api.User(username='ANY_NAME', password='ANY_PASSWORD')
            expr = api.Experiment(owner=user, name='ANY_EXPERIMENT')

        resp = hug.test.get(api, '/experiments/{}/'.format(expr.id))

        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(set(resp.data.keys()), self.expected_expr_keys)

    def test_get_unexisting_experiment(self):
        resp = hug.test.get(api, '/experiments/1/')
        self.assertEqual(resp.status, HTTP_404)

    def test_put_existing_experiment_change_name(self):
        with orm.db_session():
            user = api.User(username='ANY_NAME', password='ANY_PASSWORD')
            expr = api.Experiment(owner=user, name='ANY_EXPERIMENT')

        resp = hug.test.put(api,
                            '/experiments/{}/'.format(expr.id),
                            {'name': 'OTHER_EXPERIMENT'})
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(resp.data['name'], 'OTHER_EXPERIMENT')

    def test_put_existing_experiment_change_owner(self):
        with orm.db_session():
            user = api.User(username='ANY_NAME', password='ANY_PASSWORD')
            other_user = api.User(username='OTHER_NAME', password='OTHER_PASS')
            expr = api.Experiment(owner=user, name='ANY_EXPERIMENT')

        resp = hug.test.put(api,
                            '/experiments/{}/'.format(expr.id),
                            {'owner': other_user.id})
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(resp.data['owner'], other_user.id)

    def test_put_to_non_existing_experiment_gives_404(self):
        resp = hug.test.put(api,
                            '/experiments/1/',
                            {'name': 'OTHER_EXPERIMENT'})
        self.assertEqual(resp.status, HTTP_404)
