from unittest import TestCase, mock
import jwt
from pony import orm

from beehaiv import crypto


class TestVerifyUser(TestCase):

    def setUp(self):
        self.mock_user = mock.patch('beehaiv.crypto.User').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_user_exists_and_has_correct_password(self):
        mock_user = mock.Mock()
        mock_user.password = 'ANY_PASSWORD'
        mock_user.username = 'ANY_USERNAME'
        self.mock_user.get.return_value = mock_user

        auth = crypto.verify_user('ANY_USERNAME', 'ANY_PASSWORD')
        self.assertEqual(auth['username'], 'ANY_USERNAME')
        self.assertSetEqual(set(auth.keys()), {'username', 'id', 'isadmin'})

    def test_user_exists_but_has_incorrect_password(self):
        mock_user = mock.Mock()
        mock_user.password = 'OTHER_PASSWORD'
        mock_user.username = 'ANY_USERNAME'
        self.mock_user.get.return_value = mock_user

        auth = crypto.verify_user('ANY_USERNAME', 'ANY_PASSWORD')
        self.assertFalse(auth)


class TestVerifyToken(TestCase):

    def setUp(self):
        self.mock_decode = mock.patch('beehaiv.crypto.jwt.decode').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_token_decodes_sucessfully(self):
        self.mock_decode.return_value = {'username': 'ANY_USERNAME'}
        username = crypto.verify_token('ANY_TOKEN')
        self.assertDictEqual(username, {'username': 'ANY_USERNAME'})

    def test_token_is_invalid(self):
        self.mock_decode.side_effect = jwt.DecodeError
        auth = crypto.verify_token('ANY_TOKEN')
        self.assertFalse(auth)


class TestVerifyAdmin(TestCase):

    def setUp(self):
        self.mock_decode = mock.patch('beehaiv.crypto.jwt.decode').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_invalid_token(self):
        self.mock_decode.side_effect = jwt.DecodeError
        auth = crypto.verify_admin('ANY_TOKEN')
        self.assertFalse(auth)

    def test_valid_token_no_admin(self):
        self.mock_decode.return_value = {'username': 'ANY_USERNAME',
                                         'isadmin': False}
        auth = crypto.verify_admin('ANY_TOKEN')
        self.assertFalse(auth)

    def test_valid_admin_token(self):
        self.mock_decode.return_value = {'username': 'ANY_USERNAME',
                                         'isadmin': True}
        auth = crypto.verify_admin('ANY_TOKEN')
        self.assertDictEqual(auth, self.mock_decode.return_value)
