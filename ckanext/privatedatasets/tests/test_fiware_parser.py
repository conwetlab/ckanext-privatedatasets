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

import unittest
import ckanext.privatedatasets.parsers.fiware as fiware

from mock import MagicMock
from nose_parameterized import parameterized


TEST_CASES = {
    'one_ds': {
        'host': 'localhost',
        'json': {"customer_name": "test", "resources": [{"url": "http://localhost/dataset/ds1"}]},
        'result': {'users_datasets': [{'user': 'test', 'datasets': ['ds1']}]}
    },
    'two_ds': {
        'host': 'localhost',
        'json': {"customer_name": "test", "resources": [{"url": "http://localhost/dataset/ds1"},
                {"url": "http://localhost/dataset/ds2"}]},
        'result': {'users_datasets': [{'user': 'test', 'datasets': ['ds1', 'ds2']}]}
    },
    'error': {
        'host': 'localhost',
        'json': {"customer_name": "test", "resources": [{"url": "http://localhosta/dataset/ds1"}]},
        'error': 'Dataset ds1 is associated with the CKAN instance located at localhosta',
    },
    'error_one_ds': {
        'host': 'localhost',
        'json': {"customer_name": "test", "resources": [{"url": "http://localhosta/dataset/ds1"},
                {"url": "http://localhost/dataset/ds2"}]},
        'error': 'Dataset ds1 is associated with the CKAN instance located at localhosta',
    },
    'two_errors': {
        'host': 'localhost',
        'json': {"customer_name": "test", "resources": [{"url": "http://localhosta/dataset/ds1"},
                {"url": "http://localhostb/dataset/ds2"}]},
        'error': 'Dataset ds1 is associated with the CKAN instance located at localhosta',
    },
    'two_errors_two_ds': {
        'host': 'example.com',
        'json': {"customer_name": "test", "resources": [{"url": "http://localhosta/dataset/ds1"},
                {"url": "http://example.es/dataset/ds2"}, {"url": "http://example.com/dataset/ds3"},
                {"url": "http://example.com/dataset/ds4"}]},
        'error': 'Dataset ds1 is associated with the CKAN instance located at localhosta',
    },
    'no_customer_name': {
        'host': 'localhost',
        'json': {"resources": [{"url": "http://localhost/dataset/ds1"}]},
        'error': 'customer_name not found in the request'
    },
    'no_resources': {
        'host': 'localhost',
        'json': {"customer_name": "test"},
        'error': 'resources not found in the request'
    },
    'no_customer_name_and_resources': {
        'host': 'localhost',
        'json': {"customer": "test"},
        'error': 'customer_name not found in the request'
    },
    'invalid_customer_name': {
        'host': 'localhost',
        'json': {"customer_name": 974, "resources": [{"url": "http://localhost/dataset/ds1"}]},
        'error': 'Invalid customer_name format'
    },
    'invalid_resources': {
        'host': 'localhost',
        'json': {"customer_name": "test", "resources": "http://localhost/dataset/ds1"},
        'error': 'Invalid resources format'
    },
    'missing_url_resource': {
        'host': 'localhost',
        'json': {"customer_name": "test", "resources": [{"urla": "http://localhost/dataset/ds1"}]},
        'error': 'Invalid resource format'
    },


}


class FiWareParserTest(unittest.TestCase):

    def setUp(self):
        # Parser
        self.parser = fiware.FiWareNotificationParser()

        # Mock functions
        self._request = fiware.request
        fiware.request = MagicMock()

    def tearDown(self):
        # Unmock functions
        fiware.request = self._request

    @parameterized.expand([
        ('one_ds',),
        ('two_ds',),
        ('error',),
        ('error_one_ds',),
        ('two_errors',),
        ('two_errors_two_ds',),
        ('no_customer_name',),
        ('no_resources',),
        ('no_customer_name_and_resources',),
        ('invalid_customer_name',),
        ('invalid_resources',),
        ('missing_url_resource',)
    ])
    def test_parse_notification(self, case):

        # Configure
        fiware.request.host = TEST_CASES[case]['host']

        # Call the function
        if 'error' in TEST_CASES[case]:
            with self.assertRaises(fiware.tk.ValidationError) as cm:
                self.parser.parse_notification(TEST_CASES[case]['json'])
            self.assertEqual(cm.exception.error_dict['message'], TEST_CASES[case]['error'])
        else:
            result = self.parser.parse_notification(TEST_CASES[case]['json'])
            # Assert that the result is what we expected to be
            self.assertEquals(TEST_CASES[case]['result'], result)
