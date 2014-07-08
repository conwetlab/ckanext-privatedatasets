import ckan.lib.base as base
import ckan.lib.helpers as helpers
import ckan.plugins as plugins
import ckan.model as model
import importlib
import logging
import pylons.config as config

from ckan.common import response, _

log = logging.getLogger(__name__)

PARSER_CONFIG_PROP = 'ckan.privatedatasets.parser'


######################################################################
############################ API CONTROLLER ##########################
######################################################################

class AdquiredDatasetsControllerAPI(base.BaseController):

    def __call__(self, environ, start_response):
        # avoid status_code_redirect intercepting error responses
        environ['pylons.status_code_redirect'] = True
        return base.BaseController.__call__(self, environ, start_response)

    def add_users(self):

        log.info('Notification Request received')

        # Get the parser from the configuration
        class_path = config.get(PARSER_CONFIG_PROP, '')

        if class_path != '':
            try:
                class_package = class_path.split(':')[0]
                class_name = class_path.split(':')[1]
                parser = getattr(importlib.import_module(class_package), class_name)
                # Parse the result using the parser set in the configuration
                result = parser().parse_notification()
            except Exception as e:
                result = {'errors': [type(e).__name__ + ': ' + str(e)]}
        else:
            result = {'errors': ['%s not configured' % PARSER_CONFIG_PROP]}

        # Introduce the users into the datasets
        # Expected result: {'errors': ["...", "...", ...]
        #                   'users_datasets': [{'user': 'user_name', 'datasets': ['ds1', 'ds2', ...]}, ...]}
        warns = []

        if 'errors' in result and len(result['errors']) > 0:
            log.warn('Errors arised parsing the request: ' + str(result['errors']))
            response.status_int = 400
            return helpers.json.dumps({'errors': result['errors']})
        elif 'users_datasets' in result:
            for user_info in result['users_datasets']:
                for dataset_id in user_info['datasets']:
                    try:
                        # Get dataset data
                        dataset = plugins.toolkit.get_action('package_show')({'ignore_auth': True}, {'id': dataset_id})

                        # Generate default set of users if it does not exist
                        if 'allowed_users' not in dataset or dataset['allowed_users'] is None:
                            dataset['allowed_users'] = ''

                        # Only new users will be inserted
                        allowed_users = dataset['allowed_users'].split(',')
                        if user_info['user'] not in allowed_users:

                            # Comma is only introduced when there are more than one user in the list of allowed users
                            separator = '' if dataset['allowed_users'] == '' else ','
                            dataset['allowed_users'] += separator + user_info['user']

                            # Update dataset data
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
                        warns.append('Dataset %s: %s' % (dataset_id, e.error_dict['allowed_users'][0]))

        # Return warnings that inform about non-existing datasets
        if len(warns) > 0:
            return helpers.json.dumps({'warns': warns})


######################################################################
############################ UI CONTROLLER ###########################
######################################################################

class AdquiredDatasetsControllerUI(base.BaseController):

    def user_adquired_datasets(self):

        c = plugins.toolkit.c
        context = {
            'model': model,
            'session': model.Session,
            'user': plugins.toolkit.c.user
        }

        # Get user information
        try:
            c.user_dict = plugins.toolkit.get_action('user_show')(context, {'user_obj': c.userobj})
            c.user_dict['adquired_datasets'] = []
        except plugins.toolkit.ObjectNotFound:
            plugins.toolkit.abort(404, _('User not found'))
        except plugins.toolkit.NotAuthorized:
            plugins.toolkit.abort(401, _('Not authorized to see this page'))

        # Get the datasets adquired by the user
        query = model.Session.query(model.PackageExtra).filter(
            # Select only the allowed_users key
            'package_extra.key=\'%s\' AND package_extra.value!=\'\' ' % 'allowed_users' +
            # Selec only when the state is 'active'
            'AND package_extra.state=\'%s\' ' % 'active' +
            # The user name should be contained in the list
            'AND regexp_split_to_array(package_extra.value,\',\') @> ARRAY[\'%s\']' % context['user'])

        # Get full information about the datasets
        for dataset in query:
            try:
                dataset_dict = plugins.toolkit.get_action('package_show')(context, {'id': dataset.package_id})
                c.user_dict['adquired_datasets'].append(dataset_dict)
            except Exception:
                continue

        return plugins.toolkit.render('user/dashboard_adquired.html')
