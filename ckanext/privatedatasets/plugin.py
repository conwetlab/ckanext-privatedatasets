import ckan.plugins as p
import ckan.plugins.toolkit as tk
import ckan.new_authz as new_authz

from ckan.common import _
import ckan.logic.auth as logic_auth


def package_show(context, data_dict):
    user = context.get('user')
    user_obj = context.get('auth_user_obj')
    package = logic_auth.get_package_object(context, data_dict)

    # datasets can be readed by it creator
    if package and user and package.creator_user_id == user_obj.id:
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


def allowed_users_not_valid_on_public_datasets_or_organizations(key, data, errors, context):

    # TODO: Check the owner_org and private value according to /usr/lib/ckan/default/src/ckan/ckan/logic/validatos
    # to check if private or owner_org are defined even if they are not included in the request

    owner_org = data.get(('owner_org',))
    private = data.get(('private',)) is True

    if not private or owner_org:
        errors[key].append(_('The list of allowed users can only be set when you create a private dataset without of an organization'))


class PrivateDatasets(p.SingletonPlugin, tk.DefaultDatasetForm):
    p.implements(p.IDatasetForm)
    p.implements(p.IAuthFunctions)
    p.implements(p.IConfigurer)

    ######################################################################
    ############################ DATASET FORM ############################
    ######################################################################

    def _modify_package_schema(self):
        return {
            'allowed_users': [tk.get_validator('ignore_missing'),
                              allowed_users_not_valid_on_public_datasets_or_organizations,
                              tk.get_converter('convert_to_extras')]
        }

    def create_package_schema(self):
        # let's grab the default schema in our plugin
        schema = super(PrivateDatasets, self).create_package_schema()
        # remove datasets_with_no_organization_cannot_be_private validator
        schema.update({
            'private': [tk.get_validator('ignore_missing'),
                        tk.get_validator('boolean_validator')]
        })
        schema.update(self._modify_package_schema())
        return schema

    def update_package_schema(self):
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
        # Here, 'fanstatic' is the path to the fanstatic directory
        # (relative to this plugin.py file), and 'example_theme' is the name
        # that we'll use to refer to this fanstatic directory from CKAN
        # templates.
        tk.add_resource('fanstatic', 'privatedatasets')
