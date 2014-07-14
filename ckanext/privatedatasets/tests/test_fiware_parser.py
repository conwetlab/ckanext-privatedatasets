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
        'result': {'users_datasets': [{'user': 'test', 'datasets': []}]}
    },
    'error_one_ds': {
        'host': 'localhost',
        'json': {"customer_name": "test", "resources": [{"url": "http://localhosta/dataset/ds1"},
                {"url": "http://localhost/dataset/ds2"}]},
        'error': 'Dataset ds1 is associated with the CKAN instance located at localhosta',
        'result': {'users_datasets': [{'user': 'test', 'datasets': ['ds2']}]}
    },
    'two_errors': {
        'host': 'localhost',
        'json': {"customer_name": "test", "resources": [{"url": "http://localhosta/dataset/ds1"},
                {"url": "http://localhostb/dataset/ds2"}]},
        'error': 'Dataset ds1 is associated with the CKAN instance located at localhosta',
        'result': {'users_datasets': [{'user': 'test', 'datasets': []}]}
    },
    'two_errors_two_ds': {
        'host': 'example.com',
        'json': {"customer_name": "test", "resources": [{"url": "http://localhosta/dataset/ds1"},
                {"url": "http://example.es/dataset/ds2"}, {"url": "http://example.com/dataset/ds3"},
                {"url": "http://example.com/dataset/ds4"}]},
        'error': 'Dataset ds1 is associated with the CKAN instance located at localhosta',
        'result': {'users_datasets': [{'user': 'test', 'datasets': ['ds3', 'ds4']}]}
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
