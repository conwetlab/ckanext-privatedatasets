import ckan.lib.helpers as helpers
import re

from urlparse import urlparse
from ckan.common import request


class FiWareNotificationParser(object):

    def parse_notification(self):

        my_host = request.host

        # Parse the body
        content = helpers.json.loads(request.body, encoding='utf-8')
        resources = content['resources']
        user_name = content['customer_name']
        datasets = []
        errors = []

        for resource in resources:
            if 'url' in resource:
                parsed_url = urlparse(resource['url'])
                dataset_name = re.findall('^/dataset/(.+)$', parsed_url.path)

                if len(dataset_name) == 1:
                    if parsed_url.netloc == my_host:
                        datasets.append(dataset_name[0])
                    else:
                        errors.append('Dataset %s is associated with the CKAN instance located at %s' % (dataset_name[0], parsed_url.netloc))

        return {'errors': errors,
                'users_datasets': [{'user': user_name, 'datasets': datasets}]
                }
