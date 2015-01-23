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

import ckanext.privatedatasets.controllers.ui_controller as controller
import unittest

from mock import MagicMock, ANY
from nose_parameterized import parameterized


class UIControllerTest(unittest.TestCase):

    def setUp(self):

        # Get the instance
        self.instanceUI = controller.AcquiredDatasetsControllerUI()

        # Load the mocks
        self._plugins = controller.plugins
        controller.plugins = MagicMock()

        self._model = controller.model
        controller.model = MagicMock()

        # Set exceptions
        controller.plugins.toolkit.ObjectNotFound = self._plugins.toolkit.ObjectNotFound
        controller.plugins.toolkit.NotAuthorized = self._plugins.toolkit.NotAuthorized

    def tearDown(self):
        # Unmock
        controller.plugins = self._plugins
        controller.model = self._model

    @parameterized.expand([
        (controller.plugins.toolkit.ObjectNotFound, 404),
        (controller.plugins.toolkit.NotAuthorized,  401)
    ])
    def test_exceptions_loading_users(self, exception, expected_status):

        # Configure the mock
        user_show = MagicMock(side_effect=exception)
        controller.plugins.toolkit.get_action = MagicMock(return_value=user_show)

        # Call the function
        self.instanceUI.user_acquired_datasets()

        # Assertations
        expected_context = {
            'model': controller.model,
            'session': controller.model.Session,
            'user': controller.plugins.toolkit.c.user
        }

        user_show.assert_called_once_with(expected_context, {'user_obj': controller.plugins.toolkit.c.userobj})
        controller.plugins.toolkit.abort.assert_called_once_with(expected_status, ANY)

    def test_no_error_loading_users(self):

        user = 'example_user_test'
        controller.plugins.toolkit.c.user = user

        # actions
        default_user = {'user_name': 'test', 'another_val': 'example value'}
        user_show = MagicMock(return_value=default_user)
        acquisitions_list = MagicMock()
        def _get_action(action):
            if action == 'user_show':
                return user_show
            else:
                return acquisitions_list

        controller.plugins.toolkit.get_action = MagicMock(side_effect=_get_action)

        # Call the function
        returned = self.instanceUI.user_acquired_datasets()

        # User_show called correctly
        expected_context = {
            'model': controller.model,
            'session': controller.model.Session,
            'user': controller.plugins.toolkit.c.user
        }

        user_show.assert_called_once_with(expected_context, {'user_obj': controller.plugins.toolkit.c.userobj})

        # Query called correctry
        expected_user = default_user.copy()
        expected_user['acquired_datasets'] = acquisitions_list.return_value
        acquisitions_list.assert_called_with(expected_context, None)
        self.assertEquals(expected_user, controller.plugins.toolkit.c.user_dict)

        # Check that the render method has been called and that its result has been returned
        self.assertEquals(controller.plugins.toolkit.render.return_value, returned)
        controller.plugins.toolkit.render.assert_called_once_with('user/dashboard_acquired.html')
