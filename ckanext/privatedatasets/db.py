import sqlalchemy as sa

package_allowed_users_table = None
AllowedUser = None


def init_db(model):
    class _AllowedUser(model.DomainObject):

        @classmethod
        def get(cls, **kw):
            '''Finds all the instances required.'''
            query = model.Session.query(cls).autoflush(False)
            return query.filter_by(**kw).all()

    global AllowedUser
    AllowedUser = _AllowedUser

    global package_allowed_users_table
    package_allowed_users_table = sa.Table('package_allowed_users', model.meta.metadata,
        sa.Column('package_id', sa.types.UnicodeText, primary_key=True, default=u''),
        sa.Column('user_name', sa.types.UnicodeText, primary_key=True, default=u''),
    )

    # Create the table only if it does not exist
    package_allowed_users_table.create(checkfirst=True)

    model.meta.mapper(
        AllowedUser,
        package_allowed_users_table,
    )
