import db

from ckan.plugins import toolkit
from ckan.common import _
from itertools import count


def private_datasets_metadata_checker(key, data, errors, context):

    dataset_id = data.get(('id',))
    private_val = data.get(('private',))

    # If the private field is not included in the data dict, we must check the current value
    if not private_val and dataset_id:
        dataset_dict = toolkit.get_action('package_show')({'ignore_auth': True}, {'id': dataset_id})
        private_val = dataset_dict.get('private')

    private = private_val is True if isinstance(private_val, bool) else private_val == "True"
    metadata_value = data[key]

    # If allowed users are included and the dataset is not private outside and organization, an error will be raised.
    if metadata_value != '' and not private:
        errors[key].append(_('This field is only valid when you create a private dataset'))


def allowed_users_convert(key, data, errors, context):
    if isinstance(data[key], basestring):
        allowed_users = [allowed_user for allowed_user in data[key].split(',')]
    else:
        allowed_users = data[key]

    current_index = max([int(k[1]) for k in data.keys() if len(k) == 2 and k[0] == 'allowed_users'] + [-1])

    for num, allowed_user in zip(count(current_index + 1), allowed_users):
        data[('allowed_users', num)] = allowed_user


def get_allowed_users(key, data, errors, context):
    pkg_id = data[('id',)]

    if db.package_allowed_users_table is None:
        db.init_db(context['model'])

    users = db.AllowedUser.get(package_id=pkg_id)
    counter = 0

    for user in users:
        data[(key[0], counter)] = user.user_name
        counter += 1
