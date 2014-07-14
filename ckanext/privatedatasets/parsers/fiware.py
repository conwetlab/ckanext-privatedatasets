import ckan.plugins.toolkit as tk
import re

from urlparse import urlparse
from ckan.common import request


class FiWareNotificationParser(object):

    def parse_notification(self, request_data):

        my_host = request.host

        # Parse the body
        resources = request_data['resources']
        user_name = request_data['customer_name']
        datasets = []

        for resource in resources:
            if 'url' in resource:
                parsed_url = urlparse(resource['url'])
                dataset_name = re.findall('^/dataset/([^/]+).*$', parsed_url.path)

                if len(dataset_name) == 1:
                    if parsed_url.netloc == my_host:
                        datasets.append(dataset_name[0])
                    else:
                        raise tk.ValidationError({'message': 'Dataset %s is associated with the CKAN instance located at %s'
                                                 % (dataset_name[0], parsed_url.netloc)})

        return {'users_datasets': [{'user': user_name, 'datasets': datasets}]}
