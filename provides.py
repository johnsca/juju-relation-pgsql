#!/usr/bin/python
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from charmhelpers.core import hookenv
from charmhelpers.core.reactive import RelationBase
from charmhelpers.core.reactive import scopes
from charmhelpers.core.reactive import hook
from charmhelpers.core.reactive import not_until


class PostgreSQL(RelationBase):
    # We expect multiple, separate services to be related, but all units of a
    # given service will share the same database name and connection info.
    # Thus, we use SERVICE scope and will have one converstaion per service.
    scope = scopes.SERVICE

    @hook('{interface:pgsql}-relation-{joined,changed}')
    def joined_changed(self):
        """
        Handles the relation-joined and relation-changed hook.

        Depending on the state of the conversation, this can trigger one
        of the following states:

        * ``{relation_name}.database.requested`` This state will be activated if
          the remote service has requested a different database name than the
          one it has been provided.  This state should be resolved by calling
          :meth:`provide_database`.  See also :meth:`requested_databases`.

        * ``{relation_name}.roles.requested`` This state will be activated if
          the remote service has requested a specific set of roles for its user.
          This state should be resolved by calling :meth:`ack_roles`.  See also
          :meth:`requrested_roles`.
        """
        service = hookenv.remote_service()
        conversation = self.conversation()

        if self.previous_database(service) != self.requested_database(service):
            conversation.set_state('{relation_name}.database.requested')

        if self.previous_roles(service) != self.requested_roles(service):
            conversation.set_state('{relation_name}.roles.requested')

    @not_until('{interface:pgsql}.database.requested')
    def provide_database(self, service, host, port, database, user, password, schema_user, schema_password, state):
        """
        Provide a database to a requesting service.

        :param str service: The service which requested the database, as
            returned by :meth:`~provides.PostgreSQL.requested_databases`.
        :param str host: The host where the database can be reached (e.g.,
            the charm's private or public-address).
        :param int port: The port where the database can be reached.
        :param str database: The name of the database being provided.
        :param str user: The username to be used to access the database.
        :param str password: The password to be used to access the database.
        :param str schema_user: The username to be used to admin the database.
        :param str schema_password: The password to be used to admin the database.
        :param str state: I have no idea what this is for.  TODO: Document this better
        """
        conversation = self.conversation(scope=service)
        conversation.set_remote(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            schema_user=schema_user,
            schema_password=schema_password,
            state=state,
        )
        conversation.set_local('database', database)
        conversation.remove_state('{relation_name}.database.requested')

    @not_until('{interface:pgsql}.roles.requested')
    def ack_roles(self, service, roles):
        """
        Acknowledge that a set of roles have been given to a service's user.

        :param str service: The service which requested the roles, as
            returned by :meth:`~provides.PostgreSQL.requested_roles`.
        """
        conversation = self.conversation(scope=service)
        conversation.set_local('roles', roles)
        conversation.remove_state('{relation_name}.roles.requested')

    def requested_roles(self, service=None):
        """
        Return the roles requested by all or a single given service.

        :param str service: The name of a service requesting roles, as
            provided by either :meth:`requested_roles` (with no args) or
            :meth:`requested_databases`.
        :returns: If no service name is given, then a list of ``(service, roles)``
            tuples are returned, mapping service names to their requested
            roles.  If a service name is given, a list of the roles requested
            for that service is returned.

        Example usage::

            for service, roles in pgsql.requested_roles():
                set_roles(username_from_service(service), roles)
                pgsql.ack_roles(service, roles)
        """
        _roles = lambda conv: filter(None, conv.get_remote('roles', '').split(','))
        if service is not None:
            return _roles(self.conversation(scope=service))
        else:
            results = []
            for conversation in self.conversations():
                service = conversation.scope
                results.append((service, _roles(conversation)))
            return results

    def previous_roles(self, service):
        """
        Return the roles previously requested, if different from the currently
        requested roles.
        """
        return self.conversation(scope=service).get_local('roles')

    def requested_databases(self):
        """
        Return a list of tuples mapping a service name to the database name
        requested by that service.  If a given service has not requested a
        specific database name, an empty string is returned, indicating that
        the database name should be generated.

        Example usage::

            for service, database in pgsql.requested_databases():
                database = database or generate_dbname(service)
                pgsql.provide_database(**create_database(database))
        """
        for conversation in self.conversations():
            service = conversation.scope
            database = self.requested_database(service)
            yield service, database

    def requested_database(self, service):
        """
        Return the database name requested by the given service.  If the given
        service has not requested a specific database name, an empty string is
        returned, indicating that the database name should be generated.
        """
        return self.conversation(scope=service).get_remote('database', '')

    def previous_database(self, service):
        """
        Return the roles previously requested, if different from the currently
        requested roles.
        """
        return self.conversation(scope=service).get_local('database')
