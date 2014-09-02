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

import ckan.plugins.toolkit as tk
import re

from urlparse import urlparse
from ckan.common import request


class FiWareNotificationParser(object):

    def parse_notification(self, request_data):

        my_host = request.host

        fields = ['customer_name', 'resources']

        for field in fields:
            if not field in request_data:
                raise tk.ValidationError({'message': '%s not found in the request' % field})

        # Parse the body
        resources = request_data['resources']
        user_name = request_data['customer_name']
        datasets = []

        if not isinstance(user_name, basestring):
            raise tk.ValidationError({'message': 'Invalid customer_name format'})

        if not isinstance(resources, list):
            raise tk.ValidationError({'message': 'Invalid resources format'})

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
