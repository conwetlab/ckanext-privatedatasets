import ckan.lib.helpers as helpers
import ckan.logic.auth as logic_auth
import ckan.plugins as p
import ckan.plugins.toolkit as tk
import ckan.new_authz as new_authz

from ckan.common import _, request


@tk.auth_allow_anonymous_access
def package_show(context, data_dict):
    user = context.get('user')
    user_obj = context.get('auth_user_obj')
    package = logic_auth.get_package_object(context, data_dict)

    # datasets can be readed by it creator
    if package and user_obj and package.creator_user_id == user_obj.id:
        return {'success': True}

    # anyone can see a public package
    if not package.private and package.state == 'active':
        return {'success': True}

    # if the user has rights to read in the organization or in the group
    if package.owner_org:
        authorized = new_authz.has_user_permission_for_group_or_org(
            package.owner_org, user, 'read')
    else:
        authorized = False

    # if the user is not authorized yet, we should check if the
    # user is in the allowed_users object
    if not authorized:
        if hasattr(package, 'extras') and 'allowed_users' in package.extras:
            allowed_users = package.extras['allowed_users'].split(',')
            if user in allowed_users:
                authorized = True

    if not authorized:
        # Show a flash message with the URL to adquire the dataset
        # This message only can be shown when the user tries to access the dataset via its URL (/dataset/...)
        # The message cannot be displayed in other pages that uses the package_show function such as
        # the user profile page

        if hasattr(package, 'extras') and 'adquire_url' in package.extras and request.path.startswith('/dataset/'):
            helpers.flash_notice(_('This private dataset can be adquired. To do so, please click ' +
                                   '<a target="_blank" href="%s">here</a>') % package.extras['adquire_url'],
                                 allow_html=True)
        
        return {'success': False, 'msg': _('User %s not authorized to read package %s') % (user, package.id)}
    else:
        return {'success': True}


def package_update(context, data_dict):
    user = context.get('user')
    user_obj = context.get('auth_user_obj')
    package = logic_auth.get_package_object(context, data_dict)

    # Only the package creator can update it
    if package and user_obj and package.creator_user_id == user_obj.id:
        return {'success': True}

    # if the user has rights to update a dataset in the organization or in the group
    if package and package.owner_org:
        authorized = new_authz.has_user_permission_for_group_or_org(
            package.owner_org, user, 'update_dataset')
    else:
        authorized = False

    if not authorized:
        return {'success': False, 'msg': _('User %s is not authorized to edit package %s') % (user, package.id)}
    else:
        return {'success': True}


def private_datasets_metadata_checker(key, data, errors, context):

    # TODO: In some cases, we will need to retireve all the dataset information if it isn't present...

    private_val = data.get(('private',))
    owner_org = data.get(('owner_org',))
    private = private_val is True if isinstance(private_val, bool) else private_val == "True"
    metadata_value = data[key]

    # If allowed users are included and the dataset is not private outside and organization, an error will be raised.
    if metadata_value != '' and (not private or owner_org):
        errors[key].append(_('This field is only valid when you create a private dataset outside an organization'))


class PrivateDatasets(p.SingletonPlugin, tk.DefaultDatasetForm):

    p.implements(p.IDatasetForm)
    p.implements(p.IAuthFunctions)
    p.implements(p.IConfigurer)
    p.implements(p.IRoutes, inherit=True)

    ######################################################################
    ############################ DATASET FORM ############################
    ######################################################################

    def _modify_package_schema(self):
        return {
            'allowed_users': [tk.get_validator('ignore_missing'),
                              private_datasets_metadata_checker,
                              tk.get_converter('convert_to_extras')],
            'adquire_url': [tk.get_validator('ignore_missing'),
                            private_datasets_metadata_checker,
                            tk.get_converter('convert_to_extras')]
        }

    def create_package_schema(self):
        # grab the default schema in our plugin
        schema = super(PrivateDatasets, self).create_package_schema()
        # remove datasets_with_no_organization_cannot_be_private validator
        schema.update({
            'private': [tk.get_validator('ignore_missing'),
                        tk.get_validator('boolean_validator')]
        })
        schema.update(self._modify_package_schema())
        return schema

    def update_package_schema(self):
        # grab the default schema in our plugin
        schema = super(PrivateDatasets, self).update_package_schema()
        # remove datasets_with_no_organization_cannot_be_private validator
        schema.update({
            'private': [tk.get_validator('ignore_missing'),
                        tk.get_validator('boolean_validator')]
        })
        schema.update(self._modify_package_schema())
        return schema

    def show_package_schema(self):
        schema = super(PrivateDatasets, self).show_package_schema()
        schema.update({
            'allowed_users': [tk.get_converter('convert_from_extras'),
                              tk.get_validator('ignore_missing')],
            'adquire_url': [tk.get_converter('convert_from_extras'),
                            tk.get_validator('ignore_missing')]
        })
        return schema

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

    ######################################################################
    ########################### AUTH FUNCTIONS ###########################
    ######################################################################

    def get_auth_functions(self):
        return {'package_show': package_show,
                'package_update': package_update}

    ######################################################################
    ############################ ICONFIGURER #############################
    ######################################################################

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        tk.add_template_directory(config, 'templates')

        # Register this plugin's fanstatic directory with CKAN.
        tk.add_resource('fanstatic', 'privatedatasets')

    ######################################################################
    ############################### ROUTES ###############################
    ######################################################################

    def after_map(self, m):
        # DataSet adquired notification
        m.connect('/dataset_adquired',
                  controller='ckanext.privatedatasets.controller:AdquiredDatasetsController',
                  action='add_user', conditions=dict(method=['POST']))

        return m
