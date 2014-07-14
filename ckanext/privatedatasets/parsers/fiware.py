import ckan.plugins.toolkit as tk
import re

from urlparse import urlparse
from ckan.common import request


class FiWareNotificationParser(object):

    def parse_notification(self, request_data):

        my_host = request.host

        fields = ['resources', 'customer_name']

        for field in fields:
            if not field in request_data:
                raise tk.ValidationError({'message': '%s not found in the request' % field})

        # Parse the body
        resources = request_data['resources']
        user_name = request_data['customer_name']
        datasets = []

        if not isinstance(resources, list):
            raise tk.ValidationError({'message': 'Invalid resources format'})

        if not isinstance(user_name, basestring):
            raise tk.ValidationError({'message': 'Invalid customer_name format'})

        for resource in resources:
            if isinstance(resource, dict) and 'url' in resource:
                parsed_url = urlparse(resource['url'])
                dataset_name = re.findall('^/dataset/([^/]+).*$', parsed_url.path)

                if len(dataset_name) == 1:
                    if parsed_url.netloc == my_host:
                        datasets.append(dataset_name[0])
                    else:
                        raise tk.ValidationError({'message': 'Dataset %s is associated with the CKAN instance located at %s'
                                                 % (dataset_name[0], parsed_url.netloc)})
            else:
                raise tk.ValidationError({'message': 'Invalid resource format'})

        return {'users_datasets': [{'user': user_name, 'datasets': datasets}]}
