# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of CKAN Private Dataset Extension.

# CKAN Private Dataset Extension is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# CKAN Private Dataset Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with CKAN Private Dataset Extension.  If not, see <http://www.gnu.org/licenses/>.

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

        self._config = helpers.config
        helpers.config = {}

        self._request = helpers.request
        helpers.request = MagicMock()

    def tearDown(self):
        helpers.model = self._model
        helpers.tk = self._tk
        helpers.db = self._db
        helpers.config = self._config
        helpers.request = self._request

    @parameterized.expand([
        (False, 'user', False),
        (True,  'user', True),
        (False, None,   False),
        (True,  None,   False),
    ])
    def test_is_dataset_acquired(self, db_acquired, user, acquired):
        # Configure test
        helpers.tk.c.user = user
        pkg_dict = {'id': 'package_id'}

        db_response = []
        if db_acquired is True:
            out = helpers.db.AllowedUser()
            out.package_id = 'package_id'
            out.user_name = user
            db_response.append(out)

        helpers.db.AllowedUser.get = MagicMock(return_value=db_response)

        # Check the function returns the expected result
        self.assertEquals(acquired, helpers.is_dataset_acquired(pkg_dict))

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

    @parameterized.expand([
        (False,),
        (True,)
    ])
    def test_can_read(self, auth):
        # Recover exception
        helpers.tk.NotAuthorized = self._tk.NotAuthorized

        def _check_access(function_name, context, data_dict):
            if not auth:
                raise helpers.tk.NotAuthorized()
            else:
                return True

        helpers.tk.check_access = MagicMock(side_effect=_check_access)

        # Call the function and check the result
        package = {'id': 1}
        self.assertEquals(auth, helpers.can_read(package))

        # Assert called with
        context = {'user': helpers.tk.c.user, 'userobj': helpers.tk.c.userobj, 'model': helpers.model}
        helpers.tk.check_access.assert_called_once_with('package_show', context, package)

    @parameterized.expand([
        (None,    False),
        ('True',  True),
        ('False', False)
    ])
    def test_show_acquire_url_on_create(self, config_value, expected_value):
        if config_value is not None:
            helpers.config['ckan.privatedatasets.show_acquire_url_on_create'] = config_value

        # Call the function
        self.assertEquals(expected_value, helpers.show_acquire_url_on_create())

    @parameterized.expand([
        (None,    False),
        ('True',  True),
        ('False', False)
    ])
    def test_show_acquire_url_on_edit(self, config_value, expected_value):
        if config_value is not None:
            helpers.config['ckan.privatedatasets.show_acquire_url_on_edit'] = config_value

        # Call the function
        self.assertEquals(expected_value, helpers.show_acquire_url_on_edit())

    @parameterized.expand([
        ({}, '/dataset', False),
        ({'acquire_url': 'http://fiware.org'}, '/dataset', True),
        ({'acquire_url': ''}, '/dataset', False),
        ({'acquire_url': 'http://fiware.org'}, '/user', False),
    ])
    def test_acquire_button(self, package, path, button_expected):

        # Mocking
        helpers.request.path = path

        # Call the function and check response
        result = helpers.acquire_button(package)

        if button_expected:
            helpers.tk.render_snippet.assert_called_once_with('snippets/acquire_button.html', 
                                                              {'url_dest': package['acquire_url']})
            self.assertEquals(result, helpers.tk.render_snippet.return_value)
        else:
            self.assertEquals(result, '')
