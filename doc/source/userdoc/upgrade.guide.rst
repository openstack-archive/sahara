Sahara Upgrade Guide
====================

This page contains some details about upgrading Sahara from one release to
another like config file updates, db migrations, architecture changes and etc.

Icehouse -> Juno
----------------

Main binary renamed to sahara-all
+++++++++++++++++++++++++++++++++

Please, note that you should use `sahara-all` instead of `sahara-api` to start
the All-In-One Sahara.

sahara.conf upgrade
+++++++++++++++++++

We've migrated from custom auth_token middleware config options to the common
config options. To update your config file you should replace the following
old config opts with the new ones.

* ``os_auth_protocol``, ``os_auth_host``, ``os_auth_port``
  -> ``[keystone_authtoken]/auth_uri`` and ``[keystone_authtoken]/identity_uri``;
  it should be the full uri, for example: ``http://127.0.0.1:5000/v2.0/``
* ``os_admin_username`` -> ``[keystone_authtoken]/admin_user``
* ``os_admin_password`` -> ``[keystone_authtoken]/admin_password``
* ``os_admin_tenant_name`` -> ``[keystone_authtoken]/admin_tenant_name``

We've replaced oslo code from sahara.openstack.common.db by usage of oslo.db
library.

Also sqlite database is not supported anymore. Please use MySQL or PostgreSQL
db backends for Sahara. Sqlite support was dropped because it doesn't support
(and not going to support, see http://www.sqlite.org/omitted.html) ALTER
COLUMN and DROP COLUMN commands required for DB migrations between versions.

You can find more info about config file options in Sahara repository in file
``etc/sahara/sahara.conf.sample``.

Sahara Dashboard was merged into OpenStack Dashboard
++++++++++++++++++++++++++++++++++++++++++++++++++++

The Sahara Dashboard is not available in Juno release. Instead it's
functionality is provided by OpenStack Dashboard out of the box.
The Sahara UI is available in OpenStack Dashboard in
"Project" -> "Data Processing" tab.

Note that you have to properly register Sahara in Keystone in
order for Sahara UI in the Dashboard to work. For details see
``:ref:`registering Sahara in installation guide <register-sahara-label>```.

The `sahara-dashboard <https://git.openstack.org/cgit/openstack/sahara-dashboard>`_
project is now used solely to host Sahara UI integration tests.

VM user name changed for HEAT infrastructure engine
+++++++++++++++++++++++++++++++++++++++++++++++++++

We've updated HEAT infrastructure engine (``infrastructure_engine=heat``) to
use the same rules for instance user name as in direct engine. Before the
change user name for VMs created by Sahara using HEAT engine was always
'ec2-user'. Now user name is taken from the image registry as it is described
in the documentation.

Note, this change breaks Sahara backward compatibility for clusters created
using HEAT infrastructure engine before the change. Clusters will continue to
operate, but it is not recommended to perform scale operation over them.

Anti affinity implementation changed
++++++++++++++++++++++++++++++++++++

Starting with Juno release anti affinity feature is implemented using server
groups. There should not be much difference in Sahara behaviour from user
perspective, but there are internal changes:

1) Server group object will be created if anti affinity feature is enabled
2) New implementation doesn't allow several affected instances on the same
   host even if they don't have common processes. So, if anti affinity enabled
   for 'datanode' and 'tasktracker' processes, previous implementation allowed
   to have instance with 'datanode' process and other instance with
   'tasktracker' process on one host. New implementation guarantees that
   instances will be on different hosts.

Note, new implementation will be applied for new clusters only. Old
implementation will be applied if user scales cluster created in Icehouse.
