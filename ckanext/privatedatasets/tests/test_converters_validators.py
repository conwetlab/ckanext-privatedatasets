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
import ckanext.privatedatasets.converters_validators as conv_val

from mock import MagicMock
from nose_parameterized import parameterized


class ConvertersValidatorsTest(unittest.TestCase):

    def setUp(self):
        # Create mocks
        self._toolkit = conv_val.toolkit
        conv_val.toolkit = MagicMock()

        self._db = conv_val.db
        conv_val.db = MagicMock()

    def tearDown(self):
        conv_val.db = self._db
        conv_val.toolkit = self._toolkit

    @parameterized.expand([
        # When no data is present, no errors should be returned
        (True,    True,  'conwet', '',     False),
        ('True',  True,  'conwet', '',     False),
        (False,   True,  'conwet', '',     False),
        ('False', True,  'conwet', '',     False),
        (None,    True,  'conwet', '',     False),
        (None,    False, 'conwet', '',     False),
        (True,    True,  None,     '',     False),
        ('True',  True,  None,     '',     False),
        (False,   True,  None,     '',     False),
        ('False', True,  None,     '',     False),
        (None,    True,  None,     '',     False),
        (None,    False, None,     '',     False),
        (True,    True,  'conwet', [],     False),
        ('True',  True,  'conwet', [],     False),
        (False,   True,  'conwet', [],     False),
        ('False', True,  'conwet', [],     False),
        (None,    True,  'conwet', [],     False),
        (None,    False, 'conwet', [],     False),
        (True,    True,  None,     [],     False),
        ('True',  True,  None,     [],     False),
        (False,   True,  None,     [],     False),
        ('False', True,  None,     [],     False),
        (None,    True,  None,     [],     False),
        (None,    False, None,     [],     False),
        # When data is present, the field is only valid when the
        # the private field is set to true (organization should
        # not be taken into account anymore)
        (True,    True,  'conwet', 'test', False),
        ('True',  True,  'conwet', 'test', False),
        (True,    False, 'conwet', 'test', False),
        ('True',  False, 'conwet', 'test', False),
        (False,   True,  'conwet', 'test', True),
        ('False', True,  'conwet', 'test', True),
        (False,   False, 'conwet', 'test', True),
        ('False', False, 'conwet', 'test', True),
        (None,    True,  'conwet', 'test', False),
        (None,    False, 'conwet', 'test', True),
        (True,    True,  None,     'test', False),
        ('True',  True,  None,     'test', False),
        (True,    False, None,     'test', False),
        ('True',  False, None,     'test', False),
        (False,   True,  None,     'test', True),
        ('False', True,  None,     'test', True),
        (False,   False, None,     'test', True),
        ('False', False, None,     'test', True),
        (None,    True,  None,     'test', False),
        (None,    False, None,     'test', True),
    ])
    def test_metadata_checker(self, received_private, package_private, owner_org, metada_val, error_set):

        # Configure the mocks
        package_show = MagicMock(return_value={'private': package_private, 'id': 'package_id'})
        conv_val.toolkit.get_action = MagicMock(return_value=package_show)

        KEY = ('test',)
        errors = {}
        errors[KEY] = []

        data = {}
        data[('id',)] = 'package_id'
        data[('owner_org',)] = owner_org
        if received_private is not None:
            data[('private',)] = received_private
        data[KEY] = metada_val

        conv_val.private_datasets_metadata_checker(KEY, data, errors, {})

        if error_set:
            self.assertEquals(1, len(errors[KEY]))
        else:
            self.assertEquals(0, len(errors[KEY]))

    @parameterized.expand([
        ('',             0, []),
        ('',             2, []),
        ('a',            0, ['a']),
        ('a',            2, ['a']),
        (',,,   , ,  ',  0, []),
        (',,,   , ,  ',  2, []),
        ('a,z, d',       0, ['a', 'z', 'd']),
        ('a,z, d',       2, ['a', 'z', 'd']),
        (['a','z', 'd'], 0, ['a', 'z', 'd']),
        (['a','z', 'd'], 2, ['a', 'z', 'd']),
    ])
    def test_allowed_user_convert(self, users, previous_users, expected_users):
        key_str = 'allowed_users_str'
        key = 'allowed_users'

        # Configure mock
        name_validator = MagicMock()
        conv_val.toolkit.get_validator = MagicMock(return_value=name_validator)
        
        # Fullfill the data dictionary
        # * list should be included in the allowed_users filed
        # * strings should be included in the allowed_users_str field
        if isinstance(users, basestring):
            data_key = key_str
        else:
            data_key = key

        data = {(data_key,): users}

        for i in range(0, previous_users):
            data[(key, i)] = i

        # Call the function
        context = {'user': 'test', 'auth_obj_id': {'id': 1}}
        conv_val.allowed_users_convert((key,), data, {}, context)

        # Check that the users are set properly
        for i in range(previous_users, previous_users + len(expected_users)):
            name_validator.assert_any_call(expected_users[i - previous_users], context)
            self.assertEquals(expected_users[i - previous_users], data[(key, i)])

    @parameterized.expand([
        ([],),
        (['a'],),
        (['a', 'b'],),
        (['a', 'b', 'c'],),
        (['a', 'b', 'c', 'd', 'e'],)
    ])
    def test_get_allowed_users(self, users):
        key = 'allowed_users'
        data = {('id',): 'package_id'}

        # Create the users
        db_res = []
        for user in users:
            db_row = MagicMock()
            db_row.package_id = 'package_id'
            db_row.user_name = user
            db_res.append(db_row)

        conv_val.db.AllowedUser.get = MagicMock(return_value=db_res)

        # Call the function
        context = {'model': MagicMock()}
        conv_val.get_allowed_users((key,), data, {}, context)

        # Check that the users are set properly
        for i, user in enumerate(users):
            self.assertEquals(user, data[(key, i)])

        # Check that the table has been initialized properly
        conv_val.db.init_db.assert_called_once_with(context['model'])

    @parameterized.expand([
        (None, False),
        ('', False),
        ('http://google.es', False),
        ('https://google.es', False),
        ('http://google.es:80', False),
        ('https://google.es:443', False),
        ('http://google.es/path/path2/path3', False),
        ('https://google.es/path/path2/path3', False),
        ('http://google.es/path/path2/path3?aaaa=bbbb&cccc=dddd', False),
        ('https://google.es/path/path2/path3?aaaa=bbbb&cccc=dddd', False),
        ('http://google.es:80/path/path2/path3?aaaa=bbbb&cccc=dddd', False),
        ('https://google.es:443/path/path2/path3?aaaa=bbbb&cccc=dddd', False),
        ('http://goo-gl3.epa.es:80/path/path2/path3?aaaa=bbbb&cccc=dddd', False),
        ('https://go-ogl2.epa.es:443/path/path2/path3?aaaa=bbbb&cccc=dddd', False),
        ('http://192.168.0.1:80/path/path2/path3?aaaa=bbbb&cccc=dddd', False),
        ('https://192.168.0.1:443/path/path2/path3?aaaa=bbbb&cccc=dddd', False),
        ('ftp://google.es', True),
        ('http://google*.com', True),
        ('http://google+.com', True),
        ('http://google/.com', True),
        ('google', True),
        ('http://google', True),
        ('http://google:es', True),
        ('www.google.es', True)
    ])
    def test_url_validator(self, url, expected_error):
        key = ('url',)
        data = {key: url}

        # Call the function
        errors = {key: []}
        conv_val.url_checker(key, data, errors, {})

        # Check the errors array
        if expected_error:
            self.assertEquals('The URL "%s" is not valid.' % url, errors[key][0])
            expected_length = 1
        else:
            expected_length = 0

        self.assertEquals(expected_length, len(errors[key]))
