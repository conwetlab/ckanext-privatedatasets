import unittest
import ckanext.privatedatasets.plugin as plugin

from mock import MagicMock
from nose_parameterized import parameterized


class PluginTest(unittest.TestCase):

    def setUp(self):
        # Create the plugin
        self.privateDatasets = plugin.PrivateDatasets()

        # Create mocks
        self._tk = plugin.tk
        plugin.tk = MagicMock()

    def tearDown(self):
        plugin.tk = self._tk

    @parameterized.expand([
        (plugin.p.IDatasetForm,),
        (plugin.p.IAuthFunctions,),
        (plugin.p.IConfigurer,),
        (plugin.p.IRoutes,),
        (plugin.p.IActions,),
        (plugin.p.IPackageController,),
        (plugin.p.ITemplateHelpers,)
    ])
    def test_implementations(self, interface):
        self.assertTrue(interface.implemented_by(plugin.PrivateDatasets))

    def test_auth_functions(self):
        auth_functions = self.privateDatasets.get_auth_functions()
        self.assertEquals(auth_functions['package_show'], plugin.auth.package_show)
        self.assertEquals(auth_functions['package_update'], plugin.auth.package_update)
        self.assertEquals(auth_functions['resource_show'], plugin.auth.resource_show)
        self.assertEquals(auth_functions['package_adquired'], plugin.auth.package_adquired)

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
        m.connect.assert_any_call('user_adquired_datasets', '/dashboad/adquired', ckan_icon='shopping-cart',
                                  controller='ckanext.privatedatasets.controllers.ui_controller:AdquiredDatasetsControllerUI',
                                  action='user_adquired_datasets', conditions=dict(method=['GET']))

    def test_actions_functions(self):
        actions = self.privateDatasets.get_actions()
        self.assertEquals(actions['package_adquired'], plugin.actions.package_adquired)

    def test_fallback(self):
        self.assertEquals(True, self.privateDatasets.is_fallback())

    def test_package_types(self):
        self.assertEquals([], self.privateDatasets.package_types())

    ######################################################################
    ############################## SCHEMAS ###############################
    ######################################################################

    def _check_fields(self, schema, fields):
        for field in fields:
            for checker_validator in fields[field]:
                self.assertTrue(checker_validator in schema[field])
            self.assertEquals(len(fields[field]), len(schema[field]))

    @parameterized.expand([
        ('create_package_schema'),
        ('update_package_schema'),
    ])
    def test_schema_create_update(self, function_name):
  
        function = getattr(self.privateDatasets, function_name)
        returned_schema = function()

        fields = {
            'private': [plugin.tk.get_validator('ignore_missing'), plugin.tk.get_validator('boolean_validator')],
            'adquire_url': [plugin.tk.get_validator('ignore_missing'), plugin.tk.get_converter('convert_to_extras'),
                            plugin.conv_val.private_datasets_metadata_checker],
            'searchable': [plugin.tk.get_validator('ignore_missing'), plugin.tk.get_validator('boolean_validator'),
                           plugin.tk.get_converter('convert_to_extras'), plugin.conv_val.private_datasets_metadata_checker],
            'allowed_users_str': [plugin.tk.get_validator('ignore_missing'), plugin.conv_val.allowed_users_convert,
                                  plugin.conv_val.private_datasets_metadata_checker],
            'allowed_users': [plugin.tk.get_validator('ignore_missing'), plugin.conv_val.private_datasets_metadata_checker]
        }

        self._check_fields(returned_schema, fields)

    def test_schema_show(self):

        returned_schema = self.privateDatasets.show_package_schema()
   
        fields = ['searchable', 'adquire_url']

        fields = {
            'adquire_url': [plugin.tk.get_validator('ignore_missing'), plugin.tk.get_converter('convert_from_extras')],
            'searchable': [plugin.tk.get_validator('ignore_missing'), plugin.tk.get_converter('convert_from_extras')],
            'allowed_users': [plugin.tk.get_validator('ignore_missing'), plugin.conv_val.get_allowed_users]
        }

        self._check_fields(returned_schema, fields)

    ######################################################################
    ############################## PACKAGE ###############################
    ######################################################################

    @parameterized.expand([
        ('after_delete',),
        ('after_delete', 'False')
    ])
    def test_packagecontroller_after_delete(self, function, private='True'):
        pkg_dict = {'test': 'a', 'private': private, 'allowed_users': ['a', 'b', 'c']}
        expected_pkg_dict = pkg_dict.copy()
        result = self.privateDatasets.after_delete({}, pkg_dict)    # Call the function
        self.assertEquals(expected_pkg_dict, result)                # Check the result

    def test_packagecontroller_after_search(self):
        search_res = {'test': 'a', 'private': 'a', 'allowed_users': ['a', 'b', 'c']}
        expected_search_res = search_res.copy()
        result = getattr(self.privateDatasets, 'after_search')(search_res, {})  # Call the function
        self.assertEquals(expected_search_res, result)                          # Check the result

    @parameterized.expand([
        (True,  1, 1,    False, True),
        (True,  1, 2,    False, True),
        (True,  1, 1,    True,  True),
        (True,  1, 2,    True,  True),
        (True,  1, None, None,  True),
        (True,  1, 1,    None,  True),
        (True,  1, None, True,  True),
        (True,  1, None, False, True),
        (False, 1, 1,    False, True),
        (False, 1, 2,    False, False),
        (False, 1, 1,    True,  True),
        (False, 1, 2,    True,  True),
        (False, 1, None, None,  False),
        (False, 1, 1,    None,  True),
        (False, 1, None, True,  True),
        (False, 1, None, False, False),
    ])
    def test_packagecontroller_after_show(self, update_via_api, creator_id, user_id, sysadmin, fields_expected):
        
        context = {'updating_via_cb': update_via_api, }

        if creator_id is not None or sysadmin is not None:
            user = MagicMock()
            user.id = user_id
            user.sysadmin = sysadmin
            context['auth_user_obj'] = user

        pkg_dict = {'creator_user_id': creator_id, 'allowed_users': ['a', 'b', 'c'], 'searchable': True, 'adquire_url': 'http://google.es'}

        # Call the function
        result = self.privateDatasets.after_show(context, pkg_dict)    # Call the function

        # Check the final result
        fields = ['allowed_users', 'searchable', 'adquire_url']
        for field in fields:
            if fields_expected:
                self.assertTrue(field in result)
            else:
                self.assertFalse(field in result)

    @parameterized.expand([
        ('before_search',),
        ('before_view',),
        ('create',),
        ('edit',),
        ('read',),
        ('delete',),
        ('before_search', 'False'),
        ('before_view',   'False'),
        ('create',        'False'),
        ('edit',          'False'),
        ('read',          'False'),
        ('delete',        'False')
    ])
    def test_before_and_CRUD(self, function, private='True'):
        pkg_dict = {'test': 'a', 'private': private, 'allowed_users': ['a', 'b', 'c']}
        expected_pkg_dict = pkg_dict.copy()
        result = getattr(self.privateDatasets, function)(pkg_dict)   # Call the function
        self.assertEquals(expected_pkg_dict, result)                 # Check the result

    @parameterized.expand([
        ('public',  None,    'public'),
        ('public',  'False', 'private'),
        ('public',  'True',  'public'),
        ('private', None,    'private'),
        ('private', 'False', 'private'),
        ('public',  'True',  'public')
    ])
    def test_before_index(self, initialCapacity, searchable, finalCapacity):
        pkg_dict = {'capacity': initialCapacity, 'name': 'a', 'description': 'This is a test'}
        if searchable is not None:
            pkg_dict['extras_searchable'] = searchable

        expected_result = pkg_dict.copy()
        expected_result['capacity'] = finalCapacity

        self.assertEquals(expected_result, self.privateDatasets.before_index(pkg_dict))

    def test_helpers_functions(self):
        helpers_functions = self.privateDatasets.get_helpers()
        self.assertEquals(helpers_functions['privatedatasets_adquired'], plugin.helpers.is_adquired)

    # TODO: Test after create, after update...


