import unittest
import ckanext.privatedatasets.plugin as plugin

from mock import MagicMock, ANY
from nose_parameterized import parameterized


class PluginTest(unittest.TestCase):

    def setUp(self):
        # Create the plugin
        self.privateDatasets = plugin.PrivateDatasets()

        # Create mocks
        self._logic_auth = plugin.logic_auth
        plugin.logic_auth = MagicMock()

        self._request = plugin.request
        plugin.request = MagicMock()

        self._helpers = plugin.helpers
        plugin.helpers = MagicMock()

        self._new_authz = plugin.new_authz
        plugin.new_authz = MagicMock()

        self._tk = plugin.tk
        plugin.tk = MagicMock()

    def tearDown(self):
        plugin.logic_auth = self._logic_auth
        plugin.request = self._request
        plugin.helpers = self._helpers
        plugin.new_authz = self._new_authz
        plugin.tk = self._tk

    def test_implementations(self):
        self.assertTrue(plugin.p.IDatasetForm.implemented_by(plugin.PrivateDatasets))
        self.assertTrue(plugin.p.IAuthFunctions.implemented_by(plugin.PrivateDatasets))
        self.assertTrue(plugin.p.IConfigurer.implemented_by(plugin.PrivateDatasets))
        self.assertTrue(plugin.p.IRoutes.implemented_by(plugin.PrivateDatasets))
        self.assertTrue(plugin.p.IActions.implemented_by(plugin.PrivateDatasets))

    @parameterized.expand([
        # Anonymous user (public)
        (None, None, None,   False, 'active', None,     None,  None,                      None,        None,              True),
        # Anonymous user (private)
        (None, None, None,   True,  'active', None,     None,  None,                      None,        '/',               False),
        # Anonymous user (private). Buy URL not shown
        (None, None, None,   True,  'active', None,     None,  None,                      'google.es', '/',               False),
        # Anonymous user (private). Buy URL shown
        (None, None, None,   True,  'active', None,     None,  None,                      'google.es', '/dataset/testds', False),
        # The creator can always see the dataset
        (1,    1,    None,   False, 'active', None,     None,  None,                      None,        None,              True),
        (1,    1,    None,   True,  'active', None,     None,  None,                      None,        None,              True),
        (1,    1,    None,   False, 'draft',  None,     None,  None,                      None,        None,              True),
        # Other user (no organizations)
        (1,    2,    'test', False, 'active', None,     None,  None,                      None,        None,              True),
        (1,    2,    'test', True,  'active', None,     None,  None,                      'google.es', '/',               False),  # Buy MSG not shown
        (1,    2,    'test', True,  'active', None,     None,  None,                      None,        '/dataset/testds', False),  # Buy MSG not shown
        (1,    2,    'test', True,  'active', None,     None,  None,                      'google.es', '/dataset/testds', False),  # Buy MSG shown
        (1,    2,    'test', False, 'draft',  None,     None,  None,                      None,        None, False),
        # Other user but authorized in the list of authorized users
        (1,    2,    'test', True,  'active', None,     None,  'some,another,test,other', None,        None,              True),
        (1,    2,    'test', True,  'active', None,     None,  'test',                    None,        None,              True),
        # Other user and not authorized in the list of authorized users
        (1,    2,    'test', True,  'active', None,     None,  'some,another,other',      'google.es', '/',               False),
        (1,    2,    'test', True,  'active', None,     None,  'some,another,other',      'google.es', '/dataset/testds', False),
        # Other user with organizations
        (1,    2,    'test', False, 'active', 'conwet', False, None,                      None,        None,              True),
        (1,    2,    'test', True,  'active', 'conwet', False, None,                      None,        None,              False),
        (1,    2,    'test', True,  'active', 'conwet', True,  None,                      None,        None,              True),
        (1,    2,    'test', True,  'draft',  'conwet', True,  None,                      None,        None,              False)
    ])
    def test_auth_package_show(self, creator_user_id, user_obj_id, user, private, state, owner_org,
                               owner_member, allowed_users, adquire_url, request_path, authorized):

        # Configure the mocks
        returned_package = MagicMock()
        returned_package.creator_user_id = creator_user_id
        returned_package.private = private
        returned_package.state = state
        returned_package.owner_org = owner_org
        returned_package.extras = {}

        if allowed_users:
            returned_package.extras['allowed_users'] = allowed_users

        if adquire_url:
            returned_package.extras['adquire_url'] = adquire_url

        plugin.logic_auth.get_package_object = MagicMock(return_value=returned_package)
        plugin.new_authz.has_user_permission_for_group_or_org = MagicMock(return_value=owner_member)
        plugin.request.path = MagicMock(return_value=request_path)

        # Prepare the context
        context = {}
        if user:
            context['user'] = user
        if user_obj_id:
            context['auth_user_obj'] = MagicMock()
            context['auth_user_obj'].id = user_obj_id

        # Function to be tested
        result = plugin.package_show(context, {})

        # Check the result
        self.assertEquals(authorized, result['success'])

        # Check that the mocks has been called properly
        if private and owner_org and state == 'active':
            plugin.new_authz.has_user_permission_for_group_or_org.assert_called_once_with(owner_org, user, 'read')

        # Conditions to buy a dataset; It should be private, active and should not belong to any organization
        if not authorized and state == 'active' and not owner_org and request_path.startswith('/dataset/'):
            plugin.helpers.flash_error.assert_called_once()

    @parameterized.expand([
        (None, None, None,   None,     None,  False),   # Anonymous user
        (1,    1,    None,   None,     None,  True),    # A user can edit its dataset
        (1,    2,    None,   None,     None,  False),   # A user cannot edit a dataset belonging to another user
        (1,    2,    'test', 'conwet', False, False),   # User without rights to update a dataset
        (1,    2,    'test', 'conwet', True,  True),    # User with rights to update a dataset
    ])
    def test_auth_package_update(self, creator_user_id, user_obj_id, user, owner_org, owner_member, authorized):

        # Configure the mocks
        returned_package = MagicMock()
        returned_package.creator_user_id = creator_user_id
        returned_package.owner_org = owner_org

        plugin.logic_auth.get_package_object = MagicMock(return_value=returned_package)
        plugin.new_authz.has_user_permission_for_group_or_org = MagicMock(return_value=owner_member)

        # Prepare the context
        context = {}
        if user:
            context['user'] = user
        if user_obj_id:
            context['auth_user_obj'] = MagicMock()
            context['auth_user_obj'].id = user_obj_id

        # Function to be tested
        result = plugin.package_update(context, {})

        # Check the result
        self.assertEquals(authorized, result['success'])

        # Check that the mock has been called properly
        if creator_user_id != user_obj_id and owner_org:
            plugin.new_authz.has_user_permission_for_group_or_org.assert_called_once_with(owner_org, user, 'update_dataset')

    def test_auth_functions(self):
        auth_functions = self.privateDatasets.get_auth_functions()
        self.assertEquals(auth_functions['package_show'], plugin.package_show)
        self.assertEquals(auth_functions['package_update'], plugin.package_update)

    @parameterized.expand([
        ('/dataset',                     True),    # Include ignore_capacity_check
        ('/',                            False),   # Not include ignore_capacity_check
        ('/datasets',                    False),   # Not include ignore_capacity_check
        ('/api/3/action/package_search', True),    # Include ignore_capacity_check
        ('/api/3/action/dataset_search', True)     # Include ignore_capacity_check
    ])
    def test_package_seach_modified(self, request_path, include_ignore_capacity):
        # Mock the default actions
        package_search_old = MagicMock()
        plugin.tk.get_action = MagicMock(return_value=package_search_old)

        # Mock request
        plugin.request.path = request_path

        # Unmock the decorator
        plugin.tk.side_effect_free = self._tk.side_effect_free

        # Get the actions returned by the plugin
        actions = self.privateDatasets.get_actions()

        # Call the function
        context = {'id': 'test', 'another_test': 'test_value'}
        expected_context = context.copy()
        data_dict = {'example': 'test', 'key': 'value'}
        actions['package_search'](context, data_dict)

        # Test if the default function has been called properly
        package_search_old.assert_called_once_with(ANY, data_dict)
        context_called = package_search_old.call_args_list[0][0][0]    # First call, first argument

        if include_ignore_capacity:
            expected_context.update({'ignore_capacity_check': True})

        self.assertEquals(expected_context, context_called)

    def test_update_config(self):
        # Call the method
        config = {'test': 1234, 'another': 'value'}
        self.privateDatasets.update_config(config)

        # Test that functions are called as expected
        plugin.tk.add_template_directory.assert_called_once_with(config, 'templates')
        plugin.tk.add_resource('fanstatic', 'privatedatasets')

    def test_map(self):
        # Call the method
        m = MagicMock()
        self.privateDatasets.after_map(m)

        # Test that the connect method has been called
        m.connect.assert_called_once_with('/dataset_adquired',
                                          controller='ckanext.privatedatasets.controller:AdquiredDatasetsController',
                                          action='add_users', conditions=dict(method=['POST']))

    @parameterized.expand([
        ('create_package_schema'),
        ('update_package_schema'),
    ])
    def test_schema_create_update(self, function_name):

        function = getattr(self.privateDatasets, function_name)
        returned_schema = function()

        self.assertTrue(plugin.tk.get_validator('ignore_missing') in returned_schema['private'])
        self.assertTrue(plugin.tk.get_validator('boolean_validator') in returned_schema['private'])
        self.assertEquals(2, len(returned_schema['private']))

        fields = ['allowed_users', 'adquire_url']

        for field in fields:
            self.assertTrue(plugin.tk.get_validator('ignore_missing') in returned_schema[field])
            self.assertTrue(plugin.tk.get_converter('convert_to_extras') in returned_schema[field])
            self.assertTrue(plugin.private_datasets_metadata_checker in returned_schema[field])
            self.assertEquals(3, len(returned_schema[field]))

    def test_schema_show(self):

        returned_schema = self.privateDatasets.show_package_schema()

        fields = ['allowed_users', 'adquire_url']

        for field in fields:
            self.assertTrue(plugin.tk.get_validator('ignore_missing') in returned_schema[field])
            self.assertTrue(plugin.tk.get_converter('convert_from_extras') in returned_schema[field])
            self.assertEquals(2, len(returned_schema[field]))

    @parameterized.expand([
        # When no data is present, no errors should be returned
        (True,    'conwet', '',     False),
        ('True',  'conwet', '',     False),
        (False,   'conwet', '',     False),
        ('False', 'conwet', '',     False),
        (True,    None,     '',     False),
        ('True',  None,     '',     False),
        (False,   None,     '',     False),
        ('False', None,     '',     False),
        # When data is present, the field is only valid when the
        # organization is not set and the private field is set to true
        (True,    'conwet', 'test', True),
        ('True',  'conwet', 'test', True),
        (False,   'conwet', 'test', True),
        ('False', 'conwet', 'test', True),
        (True,    None,     'test', False),
        ('True',  None,     'test', False),
        (False,   None,     'test', True),
        ('False', None,     'test', True),
    ])
    def test_metadata_checker(self, private, owner_org, metada_val, error_set):

        # TODO: Maybe this test should be refactored since the function should be refactored

        KEY = ('test')
        errors = {}
        errors[KEY] = []

        data = {}
        data[('private',)] = private
        data[('owner_org',)] = owner_org
        data[KEY] = metada_val

        plugin.private_datasets_metadata_checker(KEY, data, errors, {})

        if (error_set):
            self.assertEquals(1, len(errors[KEY]))
        else:
            self.assertEquals(0, len(errors[KEY]))

    def test_fallback(self):
        self.assertEquals(True, self.privateDatasets.is_fallback())

    def test_package_types(self):
        self.assertEquals([], self.privateDatasets.package_types())
