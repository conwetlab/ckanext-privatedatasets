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
import ckanext.privatedatasets.db as db

from mock import MagicMock


class DBTest(unittest.TestCase):

    def setUp(self):
        # Restart databse initial status
        db.AllowedUser = None

        # Create mocks
        self._sa = db.sa
        db.sa = MagicMock()

    def tearDown(self):
        db.AllowedUser = None
        db.sa = self._sa

    def test_initdb_not_initialized(self):

        # Call the function
        model = MagicMock()
        db.init_db(model)

        # Assert that table method has been called
        db.sa.Table.assert_called_once()
        model.meta.mapper.assert_called_once()

    def test_initdb_initialized(self):
        db.AllowedUser = MagicMock()

        # Call the function
        model = MagicMock()
        db.init_db(model)

        # Assert that table method has been called
        self.assertEquals(0, db.sa.Table.call_count)
        self.assertEquals(0, model.meta.mapper.call_count)
