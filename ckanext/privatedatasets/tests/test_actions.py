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

    def tearDown(self):
        # Unmock
        actions.config = self._config
        actions.importlib = self._importlib
        actions.plugins = self._plugins

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
                actions.package_adquired({}, {})
            self.assertEqual(cm.exception.error_dict['message'], expected_error)
        else:
            # Exception is not risen
            self.assertEquals(None, actions.package_adquired({}, {}))

        # Checks
        self.assertEquals(0, actions.plugins.toolkit.get_action.call_count)

    def configure_mocks(self, parse_result, datasets_not_found=[], not_updatable_datasets=[], allowed_users=None):
   
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
                dataset = {'id': data_dict['id']}
                if allowed_users is not None:
                    dataset['allowed_users'] = list(allowed_users)
                return dataset

        def _package_update(context, data_dict):
            if data_dict['id'] in not_updatable_datasets:
                raise actions.plugins.toolkit.ValidationError({'allowed_users': [ADD_USERS_ERROR]})

        package_show = MagicMock(side_effect=_package_show)
        package_update = MagicMock(side_effect=_package_update)

        def _get_action(action):
            if action == 'package_update':
                return package_update
            elif action == 'package_show':
                return package_show

        actions.plugins.toolkit.get_action = _get_action

        return parser_instance.parse_notification, package_show, package_update

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

        # Complex test: some users and some datasets
        ({'user1': ['ds1', 'ds2', 'ds3', 'ds4'], 'user2': ['ds5', 'ds6', 'ds7']}, ['ds3', 'ds6'], ['ds4', 'ds7'], []),
        ({'user3': ['ds1', 'ds2', 'ds3', 'ds4'], 'user4': ['ds5', 'ds6', 'ds7']}, ['ds3', 'ds6'], ['ds4', 'ds7'], ['another_user']),
        ({'user5': ['ds1', 'ds2', 'ds3', 'ds4'], 'user6': ['ds5', 'ds6', 'ds7']}, ['ds3', 'ds6'], ['ds4', 'ds7'], ['another_user', 'another_one']),
        ({'user7': ['ds1', 'ds2', 'ds3', 'ds4'], 'user8': ['ds5', 'ds6', 'ds7']}, ['ds3', 'ds6'], ['ds4', 'ds7'], ['another_user', 'another_one', 'user7'])
    ])
    def test_add_users(self, users_info, datasets_not_found, not_updatable_datasets, allowed_users=[]):

        parse_result = {'users_datasets': []}

        # Transform user_info
        for user in users_info:
            parse_result['users_datasets'].append({'user': user, 'datasets': users_info[user]})

        parse_notification, package_show, package_update = self.configure_mocks(parse_result, datasets_not_found, not_updatable_datasets, allowed_users)

        # Call the function
        context = {'user': 'user1', 'model': 'model', 'auth_obj': {'id': 1}}
        result = actions.package_adquired(context, users_info)

        # Calculate the list of warns
        warns = []
        for user_datasets in parse_result['users_datasets']:
            for dataset_id in user_datasets['datasets']:
                if dataset_id in datasets_not_found:
                    warns.append('Dataset %s was not found in this instance' % dataset_id)
                elif dataset_id in not_updatable_datasets and allowed_users is not None and user_datasets['user'] not in allowed_users:
                    warns.append('Dataset %s: %s' % (dataset_id, ADD_USERS_ERROR))

        expected_result = {'warns': warns} if len(warns) > 0 else None

        # Check that the returned result is as expected
        self.assertEquals(expected_result, result)

        # Check that the initial functions (check_access and parse_notification) has been called properly
        parse_notification.assert_called_once_with(users_info)
        actions.plugins.toolkit.check_access.assert_called_once_with('package_adquired', context, users_info)

        for user_datasets in parse_result['users_datasets']:
            for dataset_id in user_datasets['datasets']:
                # The show function is always called
                package_show.assert_any_call({'ignore_auth': True, 'updating_via_cb': True}, {'id': dataset_id})

                # The update function is called only when the show function does not throw an exception and
                # when the user is not in the list of allowed users.
                if dataset_id not in datasets_not_found and allowed_users is not None and user_datasets['user'] not in allowed_users:
                    # Calculate the list of allowed_users
                    expected_allowed_users = list(allowed_users)
                    expected_allowed_users.append(user_datasets['user'])

                    package_update.assert_any_call({'ignore_auth': True}, {'id': dataset_id, 'allowed_users': expected_allowed_users})
