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

import sqlalchemy as sa

AllowedUser = None


def init_db(model):

    global AllowedUser
    if AllowedUser is None:

        class _AllowedUser(model.DomainObject):

            @classmethod
            def get(cls, **kw):
                '''Finds all the instances required.'''
                query = model.Session.query(cls).autoflush(False)
                return query.filter_by(**kw).all()

        AllowedUser = _AllowedUser

        # FIXME: Maybe a default value should not be included...
        package_allowed_users_table = sa.Table('package_allowed_users', model.meta.metadata,
            sa.Column('package_id', sa.types.UnicodeText, primary_key=True, default=u''),
            sa.Column('user_name', sa.types.UnicodeText, primary_key=True, default=u''),
        )

        # Create the table only if it does not exist
        package_allowed_users_table.create(checkfirst=True)

        model.meta.mapper(AllowedUser, package_allowed_users_table,)
