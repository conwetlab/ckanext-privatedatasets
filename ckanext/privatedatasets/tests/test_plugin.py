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

        if hasattr(self, '_package_show'):
            plugin.package_show = self._package_show

    def test_implementations(self):
        self.assertTrue(plugin.p.IDatasetForm.implemented_by(plugin.PrivateDatasets))
        self.assertTrue(plugin.p.IAuthFunctions.implemented_by(plugin.PrivateDatasets))
        self.assertTrue(plugin.p.IConfigurer.implemented_by(plugin.PrivateDatasets))
        self.assertTrue(plugin.p.IRoutes.implemented_by(plugin.PrivateDatasets))
        self.assertTrue(plugin.p.IActions.implemented_by(plugin.PrivateDatasets))
        self.assertTrue(plugin.p.IPackageController.implemented_by(plugin.PrivateDatasets))

    def test_decordators(self):
        self.assertEquals(True, getattr(plugin.package_show, 'auth_allow_anonymous_access', False))
        self.assertEquals(True, getattr(plugin.resource_show, 'auth_allow_anonymous_access', False))

    @parameterized.expand([
        # Anonymous user (public)
        (None, None, None,   False, 'active', None,     None,  None,                      None,        None,              True),
        # Anonymous user (private)
        (None, None, None,   True,  'active', None,     None,  None,                      None,        '/',               False),
        (None, None, '',     True,  'active', None,     None,  '',                        None,        '/',               False),
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
        (1,    2,    'test', True,  'draft',  'conwet', True,  None,                      None,        None,              False),
        # Other user with organizations (user is not in the organization)
        (1,    2,    'test', True,  'active', 'conwet', False, 'test',                    None,        None,              True),
        (1,    2,    'test', True,  'active', 'conwet', False, 'some,another,other',      None,        None,              False),
        (1,    2,    'test', True,  'active', 'conwet', False, 'some,another,other',      'google.es', '/dataset/testds', False),
        (1,    2,    'test', True,  'active', 'conwet', False, 'some,another,other',      'google.es', '/',               False)
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

        if allowed_users is not None:
            returned_package.extras['allowed_users'] = allowed_users

        if adquire_url:
            returned_package.extras['adquire_url'] = adquire_url

        plugin.logic_auth.get_package_object = MagicMock(return_value=returned_package)
        plugin.new_authz.has_user_permission_for_group_or_org = MagicMock(return_value=owner_member)
        plugin.request.path = MagicMock(return_value=request_path)

        # Prepare the context
        context = {}
        if user is not None:
            context['user'] = user
        if user_obj_id is not None:
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
        if user is not None:
            context['user'] = user
        if user_obj_id is not None:
            context['auth_user_obj'] = MagicMock()
            context['auth_user_obj'].id = user_obj_id

        # Function to be tested
        result = plugin.package_update(context, {})

        # Check the result
        self.assertEquals(authorized, result['success'])

        # Check that the mock has been called properly
        if creator_user_id != user_obj_id and owner_org:
            plugin.new_authz.has_user_permission_for_group_or_org.assert_called_once_with(owner_org, user, 'update_dataset')

    @parameterized.expand([
        (True, True),
        (True, False),
        (False, False),
        (False, False)
    ])
    def test_auth_resource_show(self, exist_pkg=True, authorized_pkg=True):
        #Recover the exception
        plugin.tk.ObjectNotFound = self._tk.ObjectNotFound

        # Mock the calls
        package = MagicMock()
        package.id = '1'

        final_query = MagicMock()
        final_query.first = MagicMock(return_value=package if exist_pkg else None)

        second_join = MagicMock()
        second_join.filter = MagicMock(return_value=final_query)

        first_join = MagicMock()
        first_join.join = MagicMock(return_value=second_join)

        query = MagicMock()
        query.join = MagicMock(return_value=first_join)

        model = MagicMock()
        session = MagicMock()
        session.query = MagicMock(return_value=query)
        model.Session = session

        # Create the context
        context = {}
        context['model'] = model

        # Mock the package_show function
        self._package_show = plugin.package_show
        success = True if authorized_pkg else False
        plugin.package_show = MagicMock(return_value={'success': success})

        if not exist_pkg:
            self.assertRaises(self._tk.ObjectNotFound, plugin.resource_show, context, {})
        else:
            result = plugin.resource_show(context, {})
            self.assertEquals(authorized_pkg, result['success'])

    def test_auth_functions(self):
        auth_functions = self.privateDatasets.get_auth_functions()
        self.assertEquals(auth_functions['package_show'], plugin.package_show)
        self.assertEquals(auth_functions['package_update'], plugin.package_update)
        self.assertEquals(auth_functions['resource_show'], plugin.resource_show)

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
        (True,    'conwet', 'test', False),
        ('True',  'conwet', 'test', False),
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

        if error_set:
            self.assertEquals(1, len(errors[KEY]))
        else:
            self.assertEquals(0, len(errors[KEY]))

    def test_fallback(self):
        self.assertEquals(True, self.privateDatasets.is_fallback())

    def test_package_types(self):
        self.assertEquals([], self.privateDatasets.package_types())

    @parameterized.expand([
        ('after_create',),
        ('after_update',),
        ('after_show',),
        ('after_delete',),
        ('after_create', 'False'),
        ('after_update', 'False'),
        ('after_show',   'False'),
        ('after_delete', 'False')
    ])
    def test_packagecontroller_after(self, function, private='True'):
        pkg_dict = {'test': 'a', 'private': private, 'allowed_users': 'a,b,c'}
        expected_pkg_dict = pkg_dict.copy()
        result = getattr(self.privateDatasets, function)({}, pkg_dict)  # Call the function
        self.assertEquals(expected_pkg_dict, result)                    # Check the result

    def test_packagecontroller_after_search(self):
        search_res = {'test': 'a', 'private': 'a', 'allowed_users': 'a,b,c'}
        expected_search_res = search_res.copy()
        result = getattr(self.privateDatasets, 'after_search')(search_res, {})  # Call the function
        self.assertEquals(expected_search_res, result)                          # Check the result

    @parameterized.expand([
        ('before_index',),
        ('before_view',),
        ('create',),
        ('edit',),
        ('read',),
        ('delete',),
        ('before_index', 'False'),
        ('before_view',  'False'),
        ('create',       'False'),
        ('edit',         'False'),
        ('read',         'False'),
        ('delete',       'False')
    ])
    def test_before_and_CRUD(self, function, private='True'):
        pkg_dict = {'test': 'a', 'private': private, 'allowed_users': 'a,b,c'}
        expected_pkg_dict = pkg_dict.copy()
        result = getattr(self.privateDatasets, function)(pkg_dict)   # Call the function
        self.assertEquals(expected_pkg_dict, result)                 # Check the result

    @parameterized.expand([
        (None,                              None,                              True),
        (None,                              '',                                True),
        ('',                                None,                              True),
        ('',                                '',                                True),
        ('ow',                              'ne',                              True),
        ('owner_org:"conwet"',              None,                              False),
        ('owner_org:"conwet"',              'ne',                              False),
        ('ow',                              'owner_org:"conwet"',              False),
        (None,                              'owner_org:"conwet"',              False),
        ('+owner_org:"conwet" +cap:public', None,                              False),
        ('+owner_org:"conwet" +cap_public', 'ne',                              False),
        ('ow',                              '+owner_org:"conwet" +cap:public', False),
        (None,                              '+owner_org:"conwet" +cap:public', False),
        ('+owner_org:"conwet" +cap:public', '+owner_org:"conwet" +cap:public', False)
    ])
    def test_before_serach(self, q=None, fq=None, expected_searchable=True):
        search_params = {}

        if q is not None:
            search_params['q'] = q

        if fq is not None:
            search_params['fq'] = fq

        expected_search_params = search_params.copy()

        # Call the function
        result = self.privateDatasets.before_search(search_params)

        # Check the result
        if expected_searchable:
            if 'fq' not in expected_search_params:
                expected_search_params['fq'] = ''
            expected_search_params['fq'] += ' -(-searchable:True AND searchable:[* TO *])'

        self.assertEquals(expected_search_params, result)
