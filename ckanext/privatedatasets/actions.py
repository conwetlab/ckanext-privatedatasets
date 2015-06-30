# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of CKAN Private Dataset Extension.

# CKAN Private Dataset Extension is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# CKAN Private Dataset Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with CKAN Private Dataset Extension.  If not, see <http://www.gnu.org/licenses/>.

import ckan.plugins as plugins
import ckanext.privatedatasets.constants as constants
import db
import importlib
import logging
import pylons.config as config

log = logging.getLogger(__name__)

PARSER_CONFIG_PROP = 'ckan.privatedatasets.parser'


def package_acquired(context, request_data):
    '''
    API action to be called every time a user acquires a dataset in an external service.

    This API should be called to add the user to the list of allowed users.

    Since each service can provide a different way of pushing the data, the received
    data will be forwarded to the parser set in the preferences. This parser should
    return a dict similar to the following one:
        {'errors': ["...", "...", ...]
         'users_datasets': [{'user': 'user_name', 'datasets': ['ds1', 'ds2', ...]}, ...]}
    1) 'errors' contains the list of errors. It should be empty if no errors arised
       while the notification is parsed
    2) 'users_datasets' is the lists of datasets available for each user (each element
       of this list is a dictionary with two fields: user and datasets).

    :parameter request_data: Depends on the parser
    :type request_data: dict

    :return: A list of warnings or None if the list of warnings is empty
    :rtype: dict

    '''

    log.info('Notification received: %s' % request_data)

    # Check access
    plugins.toolkit.check_access(constants.PACKAGE_ACQUIRED, context, request_data)

    # Get the parser from the configuration
    class_path = config.get(PARSER_CONFIG_PROP, '')

    if class_path != '':
        try:
            cls = class_path.split(':')
            class_package = cls[0]
            class_name = cls[1]
            parser_cls = getattr(importlib.import_module(class_package), class_name)
            parser = parser_cls()
        except Exception as e:
            raise plugins.toolkit.ValidationError({'message': '%s: %s' % (type(e).__name__, str(e))})
    else:
        raise plugins.toolkit.ValidationError({'message': '%s not configured' % PARSER_CONFIG_PROP})

    # Parse the result using the parser set in the configuration
    # Expected result: {'errors': ["...", "...", ...]
    #                   'users_datasets': [{'user': 'user_name', 'datasets': ['ds1', 'ds2', ...]}, ...]}
    result = parser.parse_notification(request_data)

    warns = []

    # Introduce the users into the datasets
    for user_info in result['users_datasets']:
        for dataset_id in user_info['datasets']:
            try:

                context_pkg_show = context.copy()
                context_pkg_show['ignore_auth'] = True
                context_pkg_show[constants.CONTEXT_CALLBACK] = True
                dataset = plugins.toolkit.get_action('package_show')(context_pkg_show, {'id': dataset_id})

                # This operation can only be performed with private datasets
                # This check is redundant since the package_update function will throw an exception
                # if a list of allowed users is included in a public dataset. However, this check
                # should be performed in order to avoid strange future exceptions
                if dataset.get('private', None) is True:

                    # Create the array if it does not exist
                    if constants.ALLOWED_USERS not in dataset or dataset[constants.ALLOWED_USERS] is None:
                        dataset[constants.ALLOWED_USERS] = []

                    # Add the user only if it is not in the list
                    if user_info['user'] not in dataset[constants.ALLOWED_USERS]:
                        dataset[constants.ALLOWED_USERS].append(user_info['user'])
                        context_pkg_update = context.copy()
                        context_pkg_update['ignore_auth'] = True

                        # Set creator as the user who is performing the changes
                        user_show = plugins.toolkit.get_action('user_show')
                        creator_user_id = dataset.get('creator_user_id', '')
                        user_show_context = {'ignore_auth': True}
                        user = user_show(user_show_context, {'id': creator_user_id})
                        context_pkg_update['user'] = user.get('name', '')

                        plugins.toolkit.get_action('package_update')(context_pkg_update, dataset)
                        log.info('Allowed Users added correctly')
                    else:
                        log.warn('The user %s is already allowed to access the %s dataset' % (user_info['user'], dataset_id))
                else:
                    log.warn('Dataset %s is public. Allowed Users cannot be added')
                    warns.append('Unable to upload the dataset %s: It\'s a public dataset' % dataset_id)

            except plugins.toolkit.ObjectNotFound:
                # If a dataset does not exist in the instance, an error message will be returned to the user.
                # However the process won't stop and the process will continue with the remaining datasets.
                log.warn('Dataset %s was not found in this instance' % dataset_id)
                warns.append('Dataset %s was not found in this instance' % dataset_id)
            except plugins.toolkit.ValidationError as e:
                # Some datasets does not allow to introduce the list of allowed users since this property is
                # only valid for private datasets outside an organization. In this case, a wanr will return
                # but the process will continue
                # WARN: This exception should not be risen anymore since public datasets are not updated.
                message = '%s(%s): %s' % (dataset_id, constants.ALLOWED_USERS, e.error_dict[constants.ALLOWED_USERS][0])
                log.warn(message)
                warns.append(message)

    # Return warnings that inform about non-existing datasets
    if len(warns) > 0:
        return {'warns': warns}

def acquisitions_list(context, data_dict):
    '''
    API to retrieve the list of datasets that have been acquired by a certain user

    :parameter user: The user whose acquired dataset you want to retrieve. This parameter
        is optional. If you don't include this identifier, the system will use the one
        of the user that is performing the request
    :type user: string

    :return: The list of datarequest that has been acquired by the specified user
    :rtype: list
    '''

    if data_dict is None:
        data_dict = {}

    if 'user' not in data_dict and 'user' in context:
        data_dict['user'] = context['user']

    plugins.toolkit.check_access(constants.ACQUISITIONS_LIST, context.copy(), data_dict)

    # Init db
    db.init_db(context['model'])

    # Init the result array
    result = []

    # Check that the user exists
    try:
        plugins.toolkit.get_validator('user_name_exists')(data_dict['user'], context.copy())
    except Exception:
        raise plugins.toolkit.ValidationError('User %s does not exist' % data_dict['user'])

    # Get the datasets acquired by the user
    query = db.AllowedUser.get(user_name=data_dict['user'])

    # Get the datasets
    for dataset in query:
        try:
            dataset_show_func = 'package_show'
            func_data_dict = {'id': dataset.package_id}
            internal_context = context.copy()

            # Check that the the dataset can be accessed and get its data
            # FIX: If the check_access function is not called, an exception is risen.
            plugins.toolkit.check_access(dataset_show_func, internal_context, func_data_dict)
            dataset_dict = plugins.toolkit.get_action(dataset_show_func)(internal_context, func_data_dict)

            # Only packages with state == 'active' can be shown
            if dataset_dict.get('state', None) == 'active':
                result.append(dataset_dict)
        except Exception:
            pass

    return result
