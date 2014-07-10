import ckan.model as model
import ckan.plugins.toolkit as tk
import db


def is_adquired(pkg_dict):

    adquired = False

    if db.package_allowed_users_table is None:
        db.init_db(model)

    if db.AllowedUser.get(package_id=pkg_dict['id'], user_name=tk.c.user):
        adquired = True

    return adquired


def is_owner(pkg_dict):

    owner = False
    if tk.c.userobj.id == pkg_dict['creator_user_id']:
        owner = True

    return owner


def get_allowed_users_str(users):
    return ','.join([user for user in users])
