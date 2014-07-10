import ckan.model as model
import ckan.plugins.toolkit as tk
import db


def is_adquired(pkg_dict):

    if db.package_allowed_users_table is None:
        db.init_db(model)

    return len(db.AllowedUser.get(package_id=pkg_dict['id'], user_name=tk.c.user)) > 0


def is_owner(pkg_dict):
    return tk.c.userobj.id == pkg_dict['creator_user_id']


def get_allowed_users_str(users):
    return ','.join([user for user in users])
