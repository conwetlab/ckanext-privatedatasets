import unittest
import ckanext.privatedatasets.helpers as helpers

from mock import MagicMock
from nose_parameterized import parameterized


class HelpersTest(unittest.TestCase):

    def setUp(self):
        # Create mocks
        self._model = helpers.model
        helpers.model = MagicMock()

        self._tk = helpers.tk
        helpers.tk = MagicMock()

        self._db = helpers.db
        helpers.db = MagicMock()

    def tearDown(self):
        helpers.model = self._model
        helpers.tk = self._tk
        helpers.db = self._db

    @parameterized.expand([
        (False, 'user', False),
        (True,  'user', True),
        (False, None,   False),
        (True,  None,   False),
    ])
    def test_is_adquired(self, db_adquired, user, adquired):
        # Configure test
        helpers.tk.c.user = user
        pkg_dict = {'id': 'package_id'}

        db_response = []
        if db_adquired is True:
            out = helpers.db.AllowedUser()
            out.package_id = 'package_id'
            out.user_name = user
            db_response.append(out)

        helpers.db.AllowedUser.get = MagicMock(return_value=db_response)

        # Check the function returns the expected result
        self.assertEquals(adquired, helpers.is_adquired(pkg_dict))

        # Check that the database has been initialized properly
        helpers.db.init_db.assert_called_once_with(helpers.model)

    @parameterized.expand([
        (1, 1,    True),
        (1, 2,    False),
        (1, None, False)
    ])
    def test_is_owner(self, creator_user_id, user_id, owner):
        # Configure test
        if user_id:
            user = MagicMock()
            user.id = user_id
            helpers.tk.c.userobj = user
        else:
            helpers.tk.c.userobj = None

        pkg_dict = {'creator_user_id': creator_user_id}

        # Check that the functions return the expected result
        self.assertEquals(owner, helpers.is_owner(pkg_dict))

    @parameterized.expand([
        ([],                   ''),
        (['a'],                'a'),
        (['a', 'b'],           'a,b'),
        (['a', 'b', 'c', 'd'], 'a,b,c,d'),
    ])
    def test_get_allowed_users_str(self, allowed_users, expected_result):
        self.assertEquals(expected_result, helpers.get_allowed_users_str(allowed_users))
