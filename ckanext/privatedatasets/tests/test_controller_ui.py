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
        self.instanceUI.user_adquired_datasets()

        # Assertations
        expected_context = {
            'model': controller.model,
            'session': controller.model.Session,
            'user': controller.plugins.toolkit.c.user
        }

        user_show.assert_called_once_with(expected_context, {'user_obj': controller.plugins.toolkit.c.userobj})
        controller.plugins.toolkit.abort.assert_called_once_with(expected_status, ANY)

    def test_no_errors(self):

        pkgs_ids = [0, 1, 2, 3]
        user = 'example_user_test'
        controller.plugins.toolkit.c.user = user

        # get_action mock
        user_dict = {'user_name': 'test', 'another_val': 'example value'}
        package_show = MagicMock(return_value={'pkg_id': '1', 'test': 'ok', 'res': 'ta'})
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
            query_res.append(pkg)

        filter_f = MagicMock()
        filter_f.filter = MagicMock(return_value=query_res)
        controller.model.Session.query = MagicMock(return_value=filter_f)

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
        controller.model.Session.query.assert_called_once_with(controller.model.PackageExtra)

        # Filter called correctly
        filter_f.filter.assert_called_once_with('package_extra.key=\'allowed_users\' AND package_extra.value!=\'\' ' +
                                                'AND package_extra.state=\'active\' AND ' +
                                                'regexp_split_to_array(package_extra.value,\',\') @> ARRAY[\'%s\']' % user)

        # Assert that the package_show has been called properly
        self.assertEquals(len(pkgs_ids), package_show.call_count)
        for i in pkgs_ids:
            package_show.assert_any_call(expected_context, {'id': i})

        # Check that the template has the correct datasets
        expected_user_dict = user_dict.copy()
        expected_user_dict['adquired_datasets'] = []
        for i in pkgs_ids:
            expected_user_dict['adquired_datasets'].append(package_show.return_value)
        self.assertEquals(expected_user_dict, controller.plugins.toolkit.c.user_dict)

        # Check that the render method has been called and that its result has been returned
        self.assertEquals(controller.plugins.toolkit.render.return_value, returned)
        controller.plugins.toolkit.render.assert_called_once_with('user/dashboard_adquired.html')
