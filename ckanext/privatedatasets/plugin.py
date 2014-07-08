import ckan.lib.helpers as helpers
import ckan.logic.auth as logic_auth
import ckan.plugins as p
import ckan.plugins.toolkit as tk
import ckan.new_authz as new_authz

from ckan.common import _, request


######################################################################
########################### AUTH FUNCTIONS ###########################
######################################################################

@tk.auth_allow_anonymous_access
def package_show(context, data_dict):
    user = context.get('user')
    user_obj = context.get('auth_user_obj')
    package = logic_auth.get_package_object(context, data_dict)

    # datasets can be readed by it creator
    if package and user_obj and package.creator_user_id == user_obj.id:
        return {'success': True}

    # Not active packages can only be seen by its owners
    if package.state == 'active':
        # anyone can see a public package
        if not package.private:
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
                allowed_users = package.extras['allowed_users']
                if allowed_users != '':     # ''.split(',') ==> ['']
                    allowed_users_list = allowed_users.split(',')
                    if user in allowed_users_list:
                        authorized = True

        if not authorized:
            # Show a flash message with the URL to adquire the dataset
            # This message only can be shown when the user tries to access the dataset via its URL (/dataset/...)
            # The message cannot be displayed in other pages that uses the package_show function such as
            # the user profile page

            if hasattr(package, 'extras') and 'adquire_url' in package.extras and request.path.startswith('/dataset/')\
                    and package.extras['adquire_url'] != '':
                helpers.flash_notice(_('This private dataset can be adquired. To do so, please click ' +
                                       '<a target="_blank" href="%s">here</a>') % package.extras['adquire_url'],
                                     allow_html=True)

            return {'success': False, 'msg': _('User %s not authorized to read package %s') % (user, package.id)}
        else:
            return {'success': True}
    else:
        return {'success': False, 'msg': _('User %s not authorized to read package %s') % (user, package.id)}


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


@tk.auth_allow_anonymous_access
def resource_show(context, data_dict):
    # This function is needed since CKAN resource_show function uses the default package_show
    # function instead the one defined in the plugin.
    # A bug is openend in order to be able to remove this function
    # https://github.com/ckan/ckan/issues/1818
    model = context['model']
    user = context.get('user')
    resource = logic_auth.get_resource_object(context, data_dict)

    # check authentication against package
    query = model.Session.query(model.Package)\
        .join(model.ResourceGroup)\
        .join(model.Resource)\
        .filter(model.ResourceGroup.id == resource.resource_group_id)
    pkg = query.first()
    if not pkg:
        raise tk.ObjectNotFound(_('No package found for this resource, cannot check auth.'))

    pkg_dict = {'id': pkg.id}
    authorized = package_show(context, pkg_dict).get('success')

    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to read resource %s') % (user, resource.id)}
    else:
        return {'success': True}


######################################################################
############################### CHECKER ##############################
######################################################################

def private_datasets_metadata_checker(key, data, errors, context):

    # TODO: In some cases, we will need to retireve all the dataset information if it isn't present...

    private_val = data.get(('private',))
    private = private_val is True if isinstance(private_val, bool) else private_val == "True"
    metadata_value = data[key]

    # If allowed users are included and the dataset is not private outside and organization, an error will be raised.
    if metadata_value != '' and not private:
        errors[key].append(_('This field is only valid when you create a private dataset outside an organization'))


######################################################################
############################### ADQUIRED #############################
######################################################################

def adquired(pkg_dict):

    adquired = False
    if 'allowed_users' in pkg_dict and pkg_dict['allowed_users'] != '' and pkg_dict['allowed_users'] is not None:
        allowed_users = pkg_dict['allowed_users'].split(',')
        if tk.c.user in allowed_users:
            adquired = True

    return adquired


class PrivateDatasets(p.SingletonPlugin, tk.DefaultDatasetForm):

    p.implements(p.IDatasetForm)
    p.implements(p.IAuthFunctions)
    p.implements(p.IConfigurer)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IPackageController)
    p.implements(p.ITemplateHelpers)

    ######################################################################
    ############################ DATASET FORM ############################
    ######################################################################

    def _modify_package_schema(self):
        return {
            # remove datasets_with_no_organization_cannot_be_private validator
            'private': [tk.get_validator('ignore_missing'),
                        tk.get_validator('boolean_validator')],
            'allowed_users': [tk.get_validator('ignore_missing'),
                              private_datasets_metadata_checker,
                              tk.get_converter('convert_to_extras')],
            'adquire_url': [tk.get_validator('ignore_missing'),
                            private_datasets_metadata_checker,
                            tk.get_converter('convert_to_extras')],
            'searchable': [tk.get_validator('ignore_missing'),
                           private_datasets_metadata_checker,
                           tk.get_converter('convert_to_extras'),
                           tk.get_validator('boolean_validator')]
        }

    def create_package_schema(self):
        # grab the default schema in our plugin
        schema = super(PrivateDatasets, self).create_package_schema()
        schema.update(self._modify_package_schema())
        return schema

    def update_package_schema(self):
        # grab the default schema in our plugin
        schema = super(PrivateDatasets, self).update_package_schema()
        schema.update(self._modify_package_schema())
        return schema

    def show_package_schema(self):
        schema = super(PrivateDatasets, self).show_package_schema()
        schema.update({
            'allowed_users': [tk.get_converter('convert_from_extras'),
                              tk.get_validator('ignore_missing')],
            'adquire_url': [tk.get_converter('convert_from_extras'),
                            tk.get_validator('ignore_missing')],
            'searchable': [tk.get_converter('convert_from_extras'),
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
                'package_update': package_update,
                'resource_show': resource_show}

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
                  controller='ckanext.privatedatasets.controllers.api_controller:AdquiredDatasetsControllerAPI',
                  action='add_users', conditions=dict(method=['POST']))
        m.connect('user_adquired_datasets', '/dashboad/adquired', ckan_icon='shopping-cart',
                  controller='ckanext.privatedatasets.controllers.ui_controller:AdquiredDatasetsControllerUI',
                  action='user_adquired_datasets', conditions=dict(method=['GET']))

        return m

    ######################################################################
    ######################### IPACKAGECONTROLLER #########################
    ######################################################################

    def before_index(self, pkg_dict):

        if 'extras_searchable' in pkg_dict:
            if pkg_dict['extras_searchable'] == 'False':
                pkg_dict['capacity'] = 'private'
            else:
                pkg_dict['capacity'] = 'public'

        return pkg_dict

    def before_view(self, pkg_dict):
        return pkg_dict

    def before_search(self, search_params):
        return search_params

    def create(self, pkg_dict):
        return pkg_dict

    def edit(self, pkg_dict):
        return pkg_dict

    def read(self, pkg_dict):
        return pkg_dict

    def delete(self, pkg_dict):
        return pkg_dict

    def after_create(self, context, pkg_dict):
        return pkg_dict

    def after_update(self, context, pkg_dict):
        return pkg_dict

    def after_show(self, context, pkg_dict):
        return pkg_dict

    def after_search(self, search_results, search_params):
        return search_results

    def after_delete(self, context, pkg_dict):
        return pkg_dict

    ######################################################################
    ########################## ITEMPLATESHELER ###########################
    ######################################################################

    def get_helpers(self):
        return {'privatedatasets_adquired': adquired}
