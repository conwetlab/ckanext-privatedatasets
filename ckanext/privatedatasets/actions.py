import ckan.plugins as plugins
import ckanext.privatedatasets.constants as constants
import importlib
import logging
import pylons.config as config

log = logging.getLogger(__name__)

PARSER_CONFIG_PROP = 'ckan.privatedatasets.parser'


def package_adquired(context, request_data):

    log.info('Notification Request received')

    # Check access
    plugins.toolkit.check_access(constants.PACKAGE_ADQUIRED, context, request_data)

    # Get the parser from the configuration
    class_path = config.get(PARSER_CONFIG_PROP, '')

    if class_path != '':
        try:
            class_package = class_path.split(':')[0]
            class_name = class_path.split(':')[1]
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

                dataset = plugins.toolkit.get_action('package_show')({'ignore_auth': True, constants.CONTEXT_CALLBACK: True}, {'id': dataset_id})

                # Create the array if it does not exist
                if constants.ALLOWED_USERS not in dataset or dataset[constants.ALLOWED_USERS] is None:
                    dataset[constants.ALLOWED_USERS] = []

                # Add the user only if it is not in the list
                if user_info['user'] not in dataset[constants.ALLOWED_USERS]:
                    dataset[constants.ALLOWED_USERS].append(user_info['user'])
                    plugins.toolkit.get_action('package_update')({'ignore_auth': True}, dataset)
                else:
                    log.warn('The user %s is already allowed to access the %s dataset' % (user_info['user'], dataset_id))

            except plugins.toolkit.ObjectNotFound:
                # If a dataset does not exist in the instance, an error message will be returned to the user.
                # However the process won't stop and the process will continue with the remaining datasets.
                log.warn('Dataset %s was not found in this instance' % dataset_id)
                warns.append('Dataset %s was not found in this instance' % dataset_id)
            except plugins.toolkit.ValidationError as e:
                # Some datasets does not allow to introduce the list of allowed users since this property is
                # only valid for private datasets outside an organization. In this case, a wanr will return
                # but the process will continue
                warns.append('%s(%s): %s' % (dataset_id, constants.ALLOWED_USERS, e.error_dict[constants.ALLOWED_USERS][0]))

    # Return warnings that inform about non-existing datasets
    if len(warns) > 0:
        return {'warns': warns}
