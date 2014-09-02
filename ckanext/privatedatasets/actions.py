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
import importlib
import logging
import pylons.config as config

log = logging.getLogger(__name__)

PARSER_CONFIG_PROP = 'ckan.privatedatasets.parser'


def package_acquired(context, request_data):

    log.info('Notification Request received')

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
                        plugins.toolkit.get_action('package_update')(context_pkg_update, dataset)
                    else:
                        log.warn('The user %s is already allowed to access the %s dataset' % (user_info['user'], dataset_id))
                else:
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
                warns.append('%s(%s): %s' % (dataset_id, constants.ALLOWED_USERS, e.error_dict[constants.ALLOWED_USERS][0]))

    # Return warnings that inform about non-existing datasets
    if len(warns) > 0:
        return {'warns': warns}
