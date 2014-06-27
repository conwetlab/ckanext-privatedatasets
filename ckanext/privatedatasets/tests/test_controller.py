import unittest
import ckanext.privatedatasets.controller as controller

from mock import MagicMock
from nose_parameterized import parameterized

PARSER_CONFIG_PROP = 'ckan.privatedatasets.parser'
IMPORT_ERROR_MSG = 'Unable to load the module'
CLASS_NAME = 'parser_class'
ADD_USERS_ERROR = 'Default Message'


class ControllerTest(unittest.TestCase):

    def setUp(self):

        # Get the instance
        self.instance = controller.AdquiredDatasetsController()

        # Load the mocks
        self._config = controller.config
        controller.config = MagicMock()

        self._importlib = controller.importlib
        controller.importlib = MagicMock()

        self._plugins = controller.plugins
        controller.plugins = MagicMock()

        self._response = controller.response
        controller.response = MagicMock()

    def tearDown(self):
        # Unmock
        controller.config = self._config
        controller.importlib = self._importlib
        controller.plugins = self._plugins
        controller.response = self._response

    @parameterized.expand([
        ('',              None,       False, False, '{"errors": ["%s not configured"]}' % PARSER_CONFIG_PROP),
        ('INVALID_CLASS', None,       False, False, '{"errors": ["list index out of range"]}'),
        ('INVALID.CLASS', None,       False, False, '{"errors": ["list index out of range"]}'),
        ('valid.path',    CLASS_NAME, False, False, '{"errors": ["%s"]}' % IMPORT_ERROR_MSG),
        ('valid.path',    CLASS_NAME, False, True,  '{"errors": ["%s"]}' % IMPORT_ERROR_MSG),
        ('valid.path',    CLASS_NAME, True,  False, '{"errors": ["%s"]}' % CLASS_NAME),
        ('valid.path',    CLASS_NAME, True,  True,  None)

    ])
    def test_class_cannot_be_loaded(self, class_path, class_name, path_exist, class_exist, expected_error):

        class_package = class_path
        class_package += ':' + class_name if class_name else ''
        controller.config = {PARSER_CONFIG_PROP: class_package}

        # Configure the mock
        package = MagicMock()
        if class_name and not class_exist:
            delattr(package, class_name)

        controller.importlib.import_module = MagicMock(side_effect=ImportError(IMPORT_ERROR_MSG) if not path_exist else None,
                                                       return_value=package if path_exist else None)

        # Call the function
        result = self.instance.add_user()

        # Checks
        self.assertEquals(expected_error, result)
        self.assertEquals(0, controller.plugins.toolkit.get_action.call_count)

        if expected_error:
            self.assertEquals(400, controller.response.status_int)

    def configure_mocks(self, parse_result, ds_not_found=None, error_update=None, dataset=None):

        controller.config = {PARSER_CONFIG_PROP: 'valid.path:%s' % CLASS_NAME}

        # Configure mocks
        parser_instance = MagicMock()
        parser_instance.parse_notification = MagicMock(return_value=parse_result)
        package = MagicMock()
        package.parser_class = MagicMock(return_value=parser_instance)

        controller.importlib.import_module = MagicMock(return_value=package)

        # We should use the real exceptions
        controller.plugins.toolkit.ObjectNotFound = self._plugins.toolkit.ObjectNotFound
        controller.plugins.toolkit.ValidationError = self._plugins.toolkit.ValidationError

        package_show = MagicMock(side_effect=controller.plugins.toolkit.ObjectNotFound if ds_not_found else None,
                                 return_value=dataset)
        package_update = MagicMock(side_effect=controller.plugins.toolkit.ValidationError(
                                   {'allowed_users': [ADD_USERS_ERROR]}) if error_update else None)

        def _get_action(action):
            if action == 'package_update':
                return package_update
            elif action == 'package_show':
                return package_show

        controller.plugins.toolkit.get_action = _get_action

        return package_show, package_update

    @parameterized.expand([
        ({'errors': ['Error1', 'Error2']},                                                                 '{"errors": ["Error1", "Error2"]}'),
        # Even when the users_datasets field is included, the users should not be introduced
        ({'errors': ['Error1', 'Error2'], 'users_datasets': [{'user': 'user_name', 'datasets': ['ds1']}]}, '{"errors": ["Error1", "Error2"]}'),
    ])
    def test_errors_in_parse(self, parse_result, expected_result):

        package_search, package_update = self.configure_mocks(parse_result)

        # Call the function
        result = self.instance.add_user()

        # Checks
        self.assertEquals(0, package_search.call_count)
        self.assertEquals(0, package_update.call_count)
        self.assertEquals(expected_result, result)
        self.assertEquals(400, controller.response.status_int)

    @parameterized.expand([
        (False, False, None),
        (False, False, ''),
        (False, False, 'another_user'),
        (False, False, 'another_user,another_one'),
        (False, False, 'another_user,user_name'),
        (True,  False),
        (False, True,  None),
        (False, True,  ''),
        (False, True,  'another_user'),
        (False, True,  'another_user,another_one'),
    ])
    def test_without_errors_one_user_one_ds(self, ds_not_found, error_update, allowed_users=None):

        user_name = 'user_name'
        dataset_id = 'ds1'
        parse_result = {'users_datasets': [{'user': user_name, 'datasets': [dataset_id]}]}

        # Expected allowed users: allowed_users + ',' + user_name
        # If the user_name is in the list, it should not be included again
        # If the list is empty, we should not a comma
        expected_allowed_users = allowed_users if allowed_users else ''
        if user_name not in expected_allowed_users:
            if not allowed_users or allowed_users == '':
                expected_allowed_users += user_name
            else:
                expected_allowed_users += ',' + user_name

        dataset = {'id': dataset_id}
        if allowed_users:
            dataset['allowed_users'] = allowed_users

        package_show, package_update = self.configure_mocks(parse_result, ds_not_found, error_update, dataset)

        # Call the function
        result = self.instance.add_user()

        # Check the result
        if not error_update and not ds_not_found:
            self.assertEquals(None, result)
        elif error_update:
            self.assertEquals('{"warns": ["Dataset %s: %s"]}' % (dataset_id, ADD_USERS_ERROR), result)
        elif ds_not_found:
            self.assertEquals('{"warns": ["Dataset %s was not found in this instance"]}' % dataset_id, result)

        # The show function is always called
        package_show.assert_called_once_with({'ignore_auth': True}, {'id': dataset_id})

        # The update function is called only when the show function does not throw an exception and
        # when it's needed to add the user (if the user is already in the list we mustn't add it)
        if not ds_not_found and allowed_users != expected_allowed_users:
            new_allowed_users = package_update.call_args[0][1]['allowed_users']
            self.assertEquals(expected_allowed_users, new_allowed_users)
        else:
            self.assertEquals(0, package_update.call_count)


