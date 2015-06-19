Provides: PostgreSQL
====================

Example Usage
-------------

This is what a charm using this relation would look like:

.. code-block:: python

    # in the postgres charm:
    from charmhelpers.core import hookenv  # noqa
    from charmhelpers.core import unitdata
    from charmhelpers.core.reactive import when
    from common import (
        user_name,
        create_user,
        reset_user_roles,
        ensure_database,
        get_service_port,
    )


    @when('db.roles.requested')
    def update_roles(pgsql):
        for service, roles in pgsql.requested_roles():
            user = user_name(pgsql.relation_name(), service)
            reset_user_roles(user, roles)
            pgsql.ack_roles(service, roles)


    @when('db.database.requested')
    def provide_database(pgsql):
        for service, database in pgsql.requested_databases():
            if not database:
                database = service
            roles = pgsql.requested_roles(service)

            user = user_name(pgsql.relation_name(), service)  # generate username
            password = create_user(user)  # get-or-create user
            schema_user = "{}_schema".format(user)
            schema_password = create_user(schema_user)

            reset_user_roles(user, roles)
            ensure_database(user, schema_user, database)

            pgsql.provide_database(
                service=service,
                host=hookenv.unit_private_ip(),
                port=get_service_port(),
                database=database,
                state=unitdata.kv().get('pgsql.state'),  # master, hot standby, standalone
                user=user,
                password=password,
                schema_user=schema_user,
                schema_password=schema_password,
            )


Reference
---------

.. autoclass::
    provides.PostgreSQL
    :members:
