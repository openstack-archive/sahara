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
