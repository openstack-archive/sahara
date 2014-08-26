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
library. Default sqlite db name was changed as follows.

* ``sahara.sqlite`` -> ``oslo.sqlite``

You can find more info about config file options in sahara repository in file
``etc/sahara/sahara.conf.sample``.

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
