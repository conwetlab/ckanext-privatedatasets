import ckanext.privatedatasets.controllers as controllers
import json
import unittest

from mock import MagicMock
from nose_parameterized import parameterized

PARSER_CONFIG_PROP = 'ckan.privatedatasets.parser'
IMPORT_ERROR_MSG = 'Unable to load the module'
CLASS_NAME = 'parser_class'
ADD_USERS_ERROR = 'Default Message'


class APIControllerTest(unittest.TestCase):

    def setUp(self):

        # Get the instance
        self.instanceAPI = controllers.AdquiredDatasetsControllerAPI()

        # Load the mocks
        self._config = controllers.config
        controllers.config = MagicMock()

        self._importlib = controllers.importlib
        controllers.importlib = MagicMock()

        self._plugins = controllers.plugins
        controllers.plugins = MagicMock()

        self._response = controllers.response
        controllers.response = MagicMock()

    def tearDown(self):
        # Unmock
        controllers.config = self._config
        controllers.importlib = self._importlib
        controllers.plugins = self._plugins
        controllers.response = self._response

    @parameterized.expand([
        ('',              None,       False, False, '{"errors": ["%s not configured"]}' % PARSER_CONFIG_PROP),
        ('INVALID_CLASS', None,       False, False, '{"errors": ["IndexError: list index out of range"]}'),
        ('INVALID.CLASS', None,       False, False, '{"errors": ["IndexError: list index out of range"]}'),
        ('valid.path',    CLASS_NAME, False, False, '{"errors": ["ImportError: %s"]}' % IMPORT_ERROR_MSG),
        ('valid.path',    CLASS_NAME, False, True,  '{"errors": ["ImportError: %s"]}' % IMPORT_ERROR_MSG),
        ('valid.path',    CLASS_NAME, True,  False, '{"errors": ["AttributeError: %s"]}' % CLASS_NAME),
        ('valid.path',    CLASS_NAME, True,  True,  None)

    ])
    def test_class_cannot_be_loaded(self, class_path, class_name, path_exist, class_exist, expected_error):

        class_package = class_path
        class_package += ':' + class_name if class_name else ''
        controllers.config = {PARSER_CONFIG_PROP: class_package}

        # Configure the mock
        package = MagicMock()
        if class_name and not class_exist:
            delattr(package, class_name)

        controllers.importlib.import_module = MagicMock(side_effect=ImportError(IMPORT_ERROR_MSG) if not path_exist else None,
                                                        return_value=package if path_exist else None)

        # Call the function
        result = self.instanceAPI.add_users()

        # Checks
        self.assertEquals(expected_error, result)
        self.assertEquals(0, controllers.plugins.toolkit.get_action.call_count)

        if expected_error:
            self.assertEquals(400, controllers.response.status_int)

    def configure_mocks(self, parse_result, datasets_not_found=[], not_updatable_datasets=[], allowed_users=None):

        controllers.config = {PARSER_CONFIG_PROP: 'valid.path:%s' % CLASS_NAME}

        # Configure mocks
        parser_instance = MagicMock()
        parser_instance.parse_notification = MagicMock(return_value=parse_result)
        package = MagicMock()
        package.parser_class = MagicMock(return_value=parser_instance)

        controllers.importlib.import_module = MagicMock(return_value=package)

        # We should use the real exceptions
        controllers.plugins.toolkit.ObjectNotFound = self._plugins.toolkit.ObjectNotFound
        controllers.plugins.toolkit.ValidationError = self._plugins.toolkit.ValidationError

        def _package_show(context, data_dict):
            if data_dict['id'] in datasets_not_found:
                raise controllers.plugins.toolkit.ObjectNotFound()
            else:
                return {'id': data_dict['id'], 'allowed_users': allowed_users}

        def _package_update(context, data_dict):
            if data_dict['id'] in not_updatable_datasets:
                raise controllers.plugins.toolkit.ValidationError({'allowed_users': [ADD_USERS_ERROR]})

        package_show = MagicMock(side_effect=_package_show)
        package_update = MagicMock(side_effect=_package_update)

        def _get_action(action):
            if action == 'package_update':
                return package_update
            elif action == 'package_show':
                return package_show

        controllers.plugins.toolkit.get_action = _get_action

        return package_show, package_update

    @parameterized.expand([
        ({'errors': ['Error1', 'Error2']},                                                                 '{"errors": ["Error1", "Error2"]}'),
        # Even when the users_datasets field is included, the users should not be introduced
        ({'errors': ['Error1', 'Error2'], 'users_datasets': [{'user': 'user_name', 'datasets': ['ds1']}]}, '{"errors": ["Error1", "Error2"]}'),
    ])
    def test_errors_in_parse(self, parse_result, expected_result):

        package_search, package_update = self.configure_mocks(parse_result)

        # Call the function
        result = self.instanceAPI.add_users()

        # Checks
        self.assertEquals(0, package_search.call_count)
        self.assertEquals(0, package_update.call_count)
        self.assertEquals(expected_result, result)
        self.assertEquals(400, controllers.response.status_int)

    @parameterized.expand([
        # Simple Test: one user and one dataset
        ({'user_name': ['ds1']}, [],      [],      None),
        ({'user_name': ['ds1']}, [],      [],      ''),
        ({'user_name': ['ds1']}, [],      [],      'another_user'),
        ({'user_name': ['ds1']}, [],      [],      'another_user,another_one'),
        ({'user_name': ['ds1']}, [],      [],      'another_user,user_name'),
        ({'user_name': ['ds1']}, ['ds1'], [],      None),
        ({'user_name': ['ds1']}, [],      ['ds1'], ''),
        ({'user_name': ['ds1']}, [],      ['ds1'], 'another_user'),
        ({'user_name': ['ds1']}, [],      ['ds1'], 'another_user,another_one'),
        ({'user_name': ['ds1']}, [],      ['ds1'], 'another_user,user_name'),

        # Complex test: some users and some datasets
        ({'user1': ['ds1', 'ds2', 'ds3', 'ds4'], 'user2': ['ds5', 'ds6', 'ds7']}, ['ds3', 'ds6'], ['ds4', 'ds7'], ''),
        ({'user1': ['ds1', 'ds2', 'ds3', 'ds4'], 'user2': ['ds5', 'ds6', 'ds7']}, ['ds3', 'ds6'], ['ds4', 'ds7'], 'another_user'),
        ({'user1': ['ds1', 'ds2', 'ds3', 'ds4'], 'user2': ['ds5', 'ds6', 'ds7']}, ['ds3', 'ds6'], ['ds4', 'ds7'], 'another_user,another_one'),
        ({'user1': ['ds1', 'ds2', 'ds3', 'ds4'], 'user2': ['ds5', 'ds6', 'ds7']}, ['ds3', 'ds6'], ['ds4', 'ds7'], 'another_user,another_one,user1')
    ])
    def test_add_users(self, users_info, datasets_not_found, not_updatable_datasets, allowed_users=''):

        parse_result = {'users_datasets': []}
        datasets_ids = []

        for user in users_info:
            for dataset_id in users_info[user]:
                if dataset_id not in datasets_ids:
                    datasets_ids.append(dataset_id)

            parse_result['users_datasets'].append({'user': user, 'datasets': users_info[user]})

        package_show, package_update = self.configure_mocks(parse_result, datasets_not_found, not_updatable_datasets, allowed_users)

        # Call the function
        result = self.instanceAPI.add_users()

        # Calculate the list of warns
        warns = []
        for user_datasets in parse_result['users_datasets']:
            for dataset_id in user_datasets['datasets']:
                if dataset_id in datasets_not_found:
                    warns.append('Dataset %s was not found in this instance' % dataset_id)
                elif dataset_id in not_updatable_datasets and allowed_users is not None and user_datasets['user'] not in allowed_users:
                    warns.append('Dataset %s: %s' % (dataset_id, ADD_USERS_ERROR))

        expected_result = json.dumps({'warns': warns}) if len(warns) > 0 else None

        # Check that the returned result is as expected
        self.assertEquals(expected_result, result)

        for user_datasets in parse_result['users_datasets']:
            for dataset_id in user_datasets['datasets']:
                # The show function is always called
                package_show.assert_any_call({'ignore_auth': True}, {'id': dataset_id})

                # The update function is called only when the show function does not throw an exception and
                # when the user is not in the list of allowed users.
                if dataset_id not in datasets_not_found and allowed_users is not None and user_datasets['user'] not in allowed_users:
                    # Calculate the list of allowed_users
                    expected_allowed_users = allowed_users
                    expected_allowed_users += ',' + user_datasets['user'] if expected_allowed_users != '' else user_datasets['user']

                    package_update.assert_any_call({'ignore_auth': True}, {'id': dataset_id, 'allowed_users': expected_allowed_users})
