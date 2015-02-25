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

import ckanext.privatedatasets.actions as actions
import unittest

from mock import MagicMock
from nose_parameterized import parameterized

PARSER_CONFIG_PROP = 'ckan.privatedatasets.parser'
IMPORT_ERROR_MSG = 'Unable to load the module'
CLASS_NAME = 'parser_class'
ADD_USERS_ERROR = 'Error updating the dataset'


class ActionsTest(unittest.TestCase):

    def setUp(self):

        # Load the mocks
        self._config = actions.config
        actions.config = MagicMock()

        self._importlib = actions.importlib
        actions.importlib = MagicMock()

        self._plugins = actions.plugins
        actions.plugins = MagicMock()

        self._db = actions.db
        actions.db = MagicMock()

    def tearDown(self):
        # Unmock
        actions.config = self._config
        actions.importlib = self._importlib
        actions.plugins = self._plugins
        actions.db = self._db

    @parameterized.expand([
        ('',              None,       False, False, '%s not configured' % PARSER_CONFIG_PROP),
        ('INVALID_CLASS', None,       False, False, 'IndexError: list index out of range'),
        ('INVALID.CLASS', None,       False, False, 'IndexError: list index out of range'),
        ('valid.path',    CLASS_NAME, False, False, 'ImportError: %s' % IMPORT_ERROR_MSG),
        ('valid.path',    CLASS_NAME, False, True,  'ImportError: %s' % IMPORT_ERROR_MSG),
        ('valid.path',    CLASS_NAME, True,  False, 'AttributeError: %s' % CLASS_NAME),
        ('valid.path',    CLASS_NAME, True,  True,  None)

    ])
    def test_class_cannot_be_loaded(self, class_path, class_name, path_exist, class_exist, expected_error):

        class_package = class_path
        class_package += ':' + class_name if class_name else ''
        actions.config = {PARSER_CONFIG_PROP: class_package}

        # Recover exception
        actions.plugins.toolkit.ValidationError = self._plugins.toolkit.ValidationError

        # Configure the mock
        package = MagicMock()
        if class_name and not class_exist:
            delattr(package, class_name)

        actions.importlib.import_module = MagicMock(side_effect=ImportError(IMPORT_ERROR_MSG) if not path_exist else None,
                                                    return_value=package if path_exist else None)

        # Call the function
        if expected_error:
            with self.assertRaises(actions.plugins.toolkit.ValidationError) as cm:
                actions.package_acquired({}, {})
            self.assertEqual(cm.exception.error_dict['message'], expected_error)
        else:
            # Exception is not risen
            self.assertEquals(None, actions.package_acquired({}, {}))

        # Checks
        self.assertEquals(0, actions.plugins.toolkit.get_action.call_count)

    def configure_mocks(self, parse_result, datasets_not_found=[], not_updatable_datasets=[],
            allowed_users=None, creator_user={'id': '1234', 'name': 'ckan'}):

        actions.config = {PARSER_CONFIG_PROP: 'valid.path:%s' % CLASS_NAME}

        # Configure mocks
        parser_instance = MagicMock()
        parser_instance.parse_notification = MagicMock(return_value=parse_result)
        package = MagicMock()
        package.parser_class = MagicMock(return_value=parser_instance)

        actions.importlib.import_module = MagicMock(return_value=package)

        # We should use the real exceptions
        actions.plugins.toolkit.ObjectNotFound = self._plugins.toolkit.ObjectNotFound
        actions.plugins.toolkit.ValidationError = self._plugins.toolkit.ValidationError

        def _package_show(context, data_dict):
            if data_dict['id'] in datasets_not_found:
                raise actions.plugins.toolkit.ObjectNotFound()
            else:
                dataset = {'id': data_dict['id'], 'private': data_dict['id'] not in not_updatable_datasets,
                           'creator_user_id': creator_user['id']}
                if allowed_users is not None:
                    dataset['allowed_users'] = list(allowed_users)
                return dataset

        def _package_update(context, data_dict):
            if data_dict['id'] in not_updatable_datasets:
                raise actions.plugins.toolkit.ValidationError({'allowed_users': [ADD_USERS_ERROR]})

        def _user_show(context, data_dict):
            return {'name': creator_user['name'], 'id': data_dict['id']}

        package_show = MagicMock(side_effect=_package_show)
        package_update = MagicMock(side_effect=_package_update)
        user_show = MagicMock(side_effect=_user_show)

        def _get_action(action):
            if action == 'package_update':
                return package_update
            elif action == 'package_show':
                return package_show
            elif action == 'user_show':
                return user_show

        actions.plugins.toolkit.get_action = _get_action

        return parser_instance.parse_notification, package_show, package_update, user_show

    @parameterized.expand([
        # Simple Test: one user and one dataset
        ({'user1': ['ds1']}, [],      [],      None),
        ({'user2': ['ds1']}, [],      [],      []),
        ({'user3': ['ds1']}, [],      [],      ['another_user']),
        ({'user4': ['ds1']}, [],      [],      ['another_user', 'another_one']),
        ({'user5': ['ds1']}, [],      [],      ['another_user', 'user_name']),
        ({'user6': ['ds1']}, ['ds1'], [],      None),
        ({'user7': ['ds1']}, [],      ['ds1'], []),
        ({'user8': ['ds1']}, [],      ['ds1'], ['another_user']),
        ({'user9': ['ds1']}, [],      ['ds1'], ['another_user', 'another_one']),
        ({'user1': ['ds1']}, [],      ['ds1'], ['another_user', 'user_name']),

        # # Complex test: some users and some datasets
        ({'user1': ['ds1', 'ds2', 'ds3', 'ds4'], 'user2': ['ds5', 'ds6', 'ds7']}, ['ds3', 'ds6'], ['ds4', 'ds7'], []),
        ({'user3': ['ds1', 'ds2', 'ds3', 'ds4'], 'user4': ['ds5', 'ds6', 'ds7']}, ['ds3', 'ds6'], ['ds4', 'ds7'], ['another_user']),
        ({'user5': ['ds1', 'ds2', 'ds3', 'ds4'], 'user6': ['ds5', 'ds6', 'ds7']}, ['ds3', 'ds6'], ['ds4', 'ds7'], ['another_user', 'another_one']),
        ({'user7': ['ds1', 'ds2', 'ds3', 'ds4'], 'user8': ['ds5', 'ds6', 'ds7']}, ['ds3', 'ds6'], ['ds4', 'ds7'], ['another_user', 'another_one', 'user7'])
    ])
    def test_add_users(self, users_info, datasets_not_found, not_updatable_datasets, allowed_users=[]):

        parse_result = {'users_datasets': []}
        creator_user = {'name': 'ckan', 'id': '1234'}

        # Transform user_info
        for user in users_info:
            parse_result['users_datasets'].append({'user': user, 'datasets': users_info[user]})

        parse_notification, package_show, package_update, user_show = self.configure_mocks(parse_result,
                datasets_not_found, not_updatable_datasets, allowed_users, creator_user)

        # Call the function
        context = {'user': 'user1', 'model': 'model', 'auth_obj': {'id': 1}}
        result = actions.package_acquired(context, users_info)

        # Calculate the list of warns
        warns = []
        for user_datasets in parse_result['users_datasets']:
            for dataset_id in user_datasets['datasets']:
                if dataset_id in datasets_not_found:
                    warns.append('Dataset %s was not found in this instance' % dataset_id)
                elif dataset_id in not_updatable_datasets:
                    # warns.append('%s(%s): %s' % (dataset_id, 'allowed_users', ADD_USERS_ERROR))
                    warns.append('Unable to upload the dataset %s: It\'s a public dataset' % dataset_id)

        expected_result = {'warns': warns} if len(warns) > 0 else None

        # Check that the returned result is as expected
        self.assertEquals(expected_result, result)

        # Check that the initial functions (check_access and parse_notification) has been called properly
        parse_notification.assert_called_once_with(users_info)
        actions.plugins.toolkit.check_access.assert_called_once_with('package_acquired', context, users_info)

        for user_datasets in parse_result['users_datasets']:
            for dataset_id in user_datasets['datasets']:
                # The show function is always called
                context_show = context.copy()
                context_show['ignore_auth'] = True
                context_show['updating_via_cb'] = True
                package_show.assert_any_call(context_show, {'id': dataset_id})

                # The update function is called only when the show function does not throw an exception and
                # when the user is not in the list of allowed users.
                if dataset_id not in datasets_not_found and allowed_users is not None and user_datasets['user'] not in allowed_users and dataset_id not in not_updatable_datasets:
                    # Calculate the list of allowed_users
                    expected_allowed_users = list(allowed_users)
                    expected_allowed_users.append(user_datasets['user'])

                    context_update = context.copy()
                    context_update['ignore_auth'] = True
                    context_update['user'] = creator_user['name']

                    package_update.assert_any_call(context_update, {'id': dataset_id, 'allowed_users': expected_allowed_users, 'private': True, 'creator_user_id': creator_user['id']})


    @parameterized.expand([
        (None,               {},),
        ({},                 {2: actions.plugins.toolkit.ObjectNotFound},),
        ({'user': 'fiware'}, {1: actions.plugins.toolkit.NotAuthorized},),
        (None,               {1: actions.plugins.toolkit.NotAuthorized, 2: actions.plugins.toolkit.ObjectNotFound},),
        ({},                 {},                                                                                    [1]),
        ({'user': 'fiware'}, {},                                                                                    [3, 2]),
        (None,               {1: actions.plugins.toolkit.NotAuthorized},                                            [2]),
        ({},                 {1: actions.plugins.toolkit.NotAuthorized, 2: actions.plugins.toolkit.ObjectNotFound}, [1, 3]),
    ])
    def test_acquisitions_list(self, data_dict, package_errors={}, deleted_packages=[]):

        pkgs_ids = [0, 1, 2, 3]
        user = 'example_user_test'
        actions.plugins.toolkit.c.user = user

        # get_action mock
        default_package = {'pkg_id': 0, 'test': 'ok', 'res': 'ta'}

        def _package_show(context, data_dict):
            if data_dict['id'] in package_errors:
                raise package_errors[data_dict['id']]('ERROR')
            else:
                pkg = default_package.copy()
                pkg['pkg_id'] = data_dict['id']
                pkg['state'] = 'deleted' if data_dict['id'] in deleted_packages else 'active'
                return pkg

        package_show = MagicMock(side_effect=_package_show)
        actions.plugins.toolkit.get_action.return_value = package_show

        # query mock
        query_res = []
        for i in pkgs_ids:
            pkg = MagicMock()
            pkg.package_id = i
            pkg.user_name = user
            query_res.append(pkg)

        actions.db.AllowedUser.get = MagicMock(return_value=query_res)

        # Context
        context = {
            'model': MagicMock(),
            'user': 'default_user'
        }

        # Call the function
        result = actions.acquisitions_list(context, data_dict)

        # Asset that check_access has been called
        actions.plugins.toolkit.chec_access(actions.constants.ACQUISITIONS_LIST, context, data_dict)

        # Check that the database has been initialized properly
        actions.db.init_db.assert_called_once_with(context['model'])

        # Set expected user
        expected_user = data_dict['user'] if data_dict is not None and 'user' in data_dict else context['user']

        # Query called correctry
        actions.db.AllowedUser.get.assert_called_once_with(user_name=expected_user)

        # Assert that the package_show has been called properly
        self.assertEquals(len(pkgs_ids), package_show.call_count)
        for i in pkgs_ids:
            package_show.assert_any_call(context, {'id': i})

        # Check that the template receives the correct datasets
        expected_acquired_datasets = []
        for i in pkgs_ids:
            if i not in package_errors and i not in deleted_packages:
                pkg = default_package.copy()
                pkg['pkg_id'] = i
                pkg['state'] = 'deleted' if i in deleted_packages else 'active'
                expected_acquired_datasets.append(pkg)

        self.assertEquals(expected_acquired_datasets, result)
