from unittest import mock, TestCase
import hug
from falcon import HTTP_200, HTTP_400
from pony import orm

import api


class TestExperimentsEndpoint(TestCase):

    def setUp(self):
        self.mock_experiment = mock.patch('api.Experiment').start()
        self.mock_select = mock.patch('api.orm.select').start()
        self.mock_user = mock.patch('api.User').start()
        self.mock_trial = mock.patch('api.Trial').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_get_experiments_for_empty_experiments(self):
        resp = hug.test.get(api, '/experiments/')
        self.assertEqual(resp.status, HTTP_200)
        self.assertSequenceEqual(resp.data, [])

    def test_get_experiments_for_existing_experiments(self):
        mock_expr = mock.Mock()
        mock_expr.summary.return_value = 'ANY_SUMMARY'
        self.mock_select.return_value = [mock_expr]
        resp = hug.test.get(api, '/experiments/')
        self.assertEqual(resp.status, HTTP_200)
        self.assertSequenceEqual(resp.data, ['ANY_SUMMARY'])

    def test_post_experiments_creates_and_returns(self):
        mock_expr = mock.Mock()
        mock_expr.summary.return_value = 'ANY_SUMMARY'
        self.mock_experiment.return_value = mock_expr

        resp = hug.test.post(api,
                             '/experiments/',
                             {'owner': 1, 'name': 'ANY_NAME'})
        # Internal stuff
        self.mock_user.__getitem__.assert_called_once_with(1)
        self.mock_experiment.assert_called_once_with(
            owner=self.mock_user.__getitem__.return_value,
            name='ANY_NAME')

        # Return stuff
        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(resp.data, 'ANY_SUMMARY')

    def test_post_experiments_fails_if_missing_arguments(self):
        resp = hug.test.post(api,
                             '/experiments/',
                             {'owner': 1})
        self.assertEqual(resp.status, HTTP_400)

    def test_get_existing_experiment(self):
        mock_expr = mock.Mock()
        mock_expr.summary.return_value = 'ANY_SUMMARY'
        self.mock_experiment.__getitem__.return_value = mock_expr

        resp = hug.test.get(api, '/experiments/1/')

        self.assertEqual(resp.status, HTTP_200)
        self.assertEqual(resp.data, 'ANY_SUMMARY')

    def test_get_unexisting_experiment(self):
        mock_entity = mock.Mock()
        mock_entity.__name__ = 'ANY_NAME'
        self.mock_experiment.__getitem__.side_effect = orm.ObjectNotFound(
            mock_entity)
        resp = hug.test.get(api, '/experiments/1/')
