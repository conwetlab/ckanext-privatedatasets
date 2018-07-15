# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid
# Copyright (c) 2018 Future Internet Consulting and Development Solutions S.L.

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

from mock import ANY, DEFAULT, MagicMock, patch
from parameterized import parameterized

from ckanext.privatedatasets import views


class ViewsTest(unittest.TestCase):

    @parameterized.expand([
        ('NotFound', 404),
        ('NotAuthorized', 403),
    ])
    @patch.multiple("ckanext.privatedatasets.views", base=DEFAULT, toolkit=DEFAULT, model=DEFAULT, g=DEFAULT, logic=DEFAULT, _=DEFAULT)
    def test_exceptions_loading_users(self, exception, expected_status, base, toolkit, model, g, logic, _):

        # Configure the mocks
        setattr(logic, exception, ValueError)
        toolkit.get_action().side_effect=getattr(logic, exception)
        base.abort.side_effect = TypeError

        # Call the function
        with self.assertRaises(TypeError):
            views.acquired_datasets()

        # Assertations
        expected_context = {
            'auth_user_obj': g.userobj,
            'for_view': True,
            'model': model,
            'session': model.Session,
            'user': g.user,
        }

        toolkit.get_action().assert_called_once_with(expected_context, {'user_obj': g.userobj})
        base.abort.assert_called_once_with(expected_status, ANY)

    @patch.multiple("ckanext.privatedatasets.views", base=DEFAULT, toolkit=DEFAULT, model=DEFAULT, g=DEFAULT, logic=DEFAULT)
    def test_no_error_loading_users(self, base, toolkit, model, g, logic):

        # actions
        default_user = {'user_name': 'test', 'another_val': 'example value'}
        user_show = MagicMock(return_value=default_user)
        acquisitions_list = MagicMock()

        toolkit.get_action = MagicMock(side_effect=lambda action: user_show if action == 'user_show' else acquisitions_list)

        # Call the function
        returned = views.acquired_datasets()

        # User_show called correctly
        expected_context = {
            'auth_user_obj': g.userobj,
            'for_view': True,
            'model': model,
            'session': model.Session,
            'user': g.user,
        }

        user_show.assert_called_once_with(expected_context, {'user_obj': g.userobj})
        acquisitions_list.assert_called_with(expected_context, None)

        # Check that the render method has been called
        base.render.assert_called_once_with('user/dashboard_acquired.html', {'user_dict': default_user, 'acquired_datasets': acquisitions_list()})
        self.assertEqual(returned, base.render())
