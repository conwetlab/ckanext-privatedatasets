import ckanext.privatedatasets.controllers.ui_controller as controller
import unittest

from mock import MagicMock, ANY
from nose_parameterized import parameterized


class UIControllerTest(unittest.TestCase):

    def setUp(self):

        # Get the instance
        self.instanceUI = controller.AdquiredDatasetsControllerUI()

        # Load the mocks
        self._plugins = controller.plugins
        controller.plugins = MagicMock()

        self._model = controller.model
        controller.model = MagicMock()

        self._db = controller.db
        controller.db = MagicMock()

        # Set exceptions
        controller.plugins.toolkit.ObjectNotFound = self._plugins.toolkit.ObjectNotFound
        controller.plugins.toolkit.NotAuthorized = self._plugins.toolkit.NotAuthorized

    def tearDown(self):
        # Unmock
        controller.plugins = self._plugins
        controller.model = self._model
        controller.db = self._db

    @parameterized.expand([
        (controller.plugins.toolkit.ObjectNotFound, 404),
        (controller.plugins.toolkit.NotAuthorized,  401)
    ])
    def test_exceptions_loading_users(self, exception, expected_status):

        # Configure the mock
        user_show = MagicMock(side_effect=exception)
        controller.plugins.toolkit.get_action = MagicMock(return_value=user_show)

        # Call the function
        self.instanceUI.user_adquired_datasets()

        # Assertations
        expected_context = {
            'model': controller.model,
            'session': controller.model.Session,
            'user': controller.plugins.toolkit.c.user
        }

        user_show.assert_called_once_with(expected_context, {'user_obj': controller.plugins.toolkit.c.userobj})
        controller.plugins.toolkit.abort.assert_called_once_with(expected_status, ANY)

    @parameterized.expand([
        ({},),
        ({2: controller.plugins.toolkit.ObjectNotFound},),
        ({1: controller.plugins.toolkit.NotAuthorized},)
    ])
    def test_no_error_loading_users(self, package_errors={}):

        pkgs_ids = [0, 1, 2, 3]
        user = 'example_user_test'
        controller.plugins.toolkit.c.user = user

        # get_action mock
        default_package = {'pkg_id': 0, 'test': 'ok', 'res': 'ta'}

        def _package_show(context, data_dict):
            if data_dict['id'] in package_errors:
                raise package_errors[data_dict['id']]('ERROR')
            else:
                pkg = default_package.copy()
                pkg['pkg_id'] = data_dict['id']
                return pkg

        user_dict = {'user_name': 'test', 'another_val': 'example value'}
        package_show = MagicMock(side_effect=_package_show)
        user_show = MagicMock(return_value=user_dict.copy())

        def _get_action(action):
            if action == 'package_show':
                return package_show
            elif action == 'user_show':
                return user_show

        controller.plugins.toolkit.get_action = MagicMock(side_effect=_get_action)

        # query mock
        query_res = []
        for i in pkgs_ids:
            pkg = MagicMock()
            pkg.package_id = i
            pkg.user_name = user
            query_res.append(pkg)

        controller.db.AllowedUser.get = MagicMock(return_value=query_res)

        # Call the function
        returned = self.instanceUI.user_adquired_datasets()

        # User_show called correctly
        expected_context = {
            'model': controller.model,
            'session': controller.model.Session,
            'user': controller.plugins.toolkit.c.user
        }

        user_show.assert_called_once_with(expected_context, {'user_obj': controller.plugins.toolkit.c.userobj})

        # Query called correctry
        controller.db.AllowedUser.get.assert_called_once_with(user_name=user)

        # Assert that the package_show has been called properly
        self.assertEquals(len(pkgs_ids), package_show.call_count)
        for i in pkgs_ids:
            package_show.assert_any_call(expected_context, {'id': i})

        # Check that the template receives the correct datasets
        expected_user_dict = user_dict.copy()
        expected_user_dict['adquired_datasets'] = []
        for i in pkgs_ids:
            if i not in package_errors:
                pkg = default_package.copy()
                pkg['pkg_id'] = i
                expected_user_dict['adquired_datasets'].append(pkg)

        self.assertEquals(expected_user_dict, controller.plugins.toolkit.c.user_dict)

        # Check that the render method has been called and that its result has been returned
        self.assertEquals(controller.plugins.toolkit.render.return_value, returned)
        controller.plugins.toolkit.render.assert_called_once_with('user/dashboard_adquired.html')
