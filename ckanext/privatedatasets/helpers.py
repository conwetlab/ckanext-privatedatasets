import ckan.model as model
import ckan.plugins.toolkit as tk
import auth
import db


def is_adquired(pkg_dict):

    db.init_db(model)

    if tk.c.user:
        return len(db.AllowedUser.get(package_id=pkg_dict['id'], user_name=tk.c.user)) > 0
    else:
        return False


def is_owner(pkg_dict):
    if tk.c.userobj is not None:
        return tk.c.userobj.id == pkg_dict['creator_user_id']
    else:
        return False


def get_allowed_users_str(users):
    if users:
        return ','.join([user for user in users])
    else:
        return ''


def can_read(pkg_dict):
    if tk.c.userobj and tk.c.userobj.sysadmin:
        return True
    else:
        context = {'user': tk.c.user, 'auth_user_obj': tk.c.userobj, 'model': model}
        return auth.package_show(context, pkg_dict)['success'] is True
