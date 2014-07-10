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
    # We will just try to create the table.  If it already exists we get an
    # error but we can just skip it and carry on.
    sql = '''
                CREATE TABLE package_allowed_users (
                    package_id text NOT NULL,
                    user_name text NOT NULL
                );
    '''
    conn = model.Session.connection()
    try:
        conn.execute(sql)
    except sa.exc.ProgrammingError:
        pass
    model.Session.commit()

    types = sa.types
    global package_allowed_users_table
    package_allowed_users_table = sa.Table('package_allowed_users', model.meta.metadata,
        sa.Column('package_id', types.UnicodeText, primary_key=True, default=u''),
        sa.Column('user_name', types.UnicodeText, primary_key=True, default=u''),
    )

    model.meta.mapper(
        AllowedUser,
        package_allowed_users_table,
    )
