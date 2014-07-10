import ckan.lib.helpers as helpers
import ckan.logic.auth as logic_auth
import ckan.plugins.toolkit as tk
import ckan.new_authz as new_authz
import db

from ckan.common import _, request


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
            # Init the model
            if db.package_allowed_users_table is None:
                db.init_db(context['model'])

            if db.AllowedUser.get(package_id=package.id, user_name=user):
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
    _model = context['model']
    user = context.get('user')
    resource = logic_auth.get_resource_object(context, data_dict)

    # check authentication against package
    query = _model.Session.query(_model.Package)\
        .join(_model.ResourceGroup)\
        .join(_model.Resource)\
        .filter(_model.ResourceGroup.id == resource.resource_group_id)
    pkg = query.first()
    if not pkg:
        raise tk.ObjectNotFound(_('No package found for this resource, cannot check auth.'))

    pkg_dict = {'id': pkg.id}
    authorized = package_show(context, pkg_dict).get('success')

    if not authorized:
        return {'success': False, 'msg': _('User %s not authorized to read resource %s') % (user, resource.id)}
    else:
        return {'success': True}
