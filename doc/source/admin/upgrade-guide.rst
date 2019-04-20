Sahara Upgrade Guide
====================

This page contains details about upgrading sahara between releases such as
configuration file updates, database migrations, and architectural changes.

Icehouse -> Juno
----------------

Main binary renamed to sahara-all
+++++++++++++++++++++++++++++++++

The All-In-One sahara binary has been renamed from ``sahara-api``
to ``sahara-all``. The new name should be used in all cases where the
All-In-One sahara is desired.

Authentication middleware changes
+++++++++++++++++++++++++++++++++

The custom auth_token middleware has been deprecated in favor of the keystone
middleware. This change requires an update to the sahara configuration file. To
update your configuration file you should replace the following parameters from
the ``[DEFAULT]`` section with the new parameters in the
``[keystone_authtoken]`` section:

+-----------------------+--------------------+
| Old parameter name    | New parameter name |
+=======================+====================+
| os_admin_username     | admin_user         |
+-----------------------+--------------------+
| os_admin_password     | admin_password     |
+-----------------------+--------------------+
| os_admin_tenant_name  | admin_tenant_name  |
+-----------------------+--------------------+

Additionally, the parameters ``os_auth_protocol``, ``os_auth_host``,
and ``os_auth_port`` have been combined to create the ``auth_uri``
and ``identity_uri`` parameters. These new parameters should be
full URIs to the keystone public and admin endpoints, respectively.

For more information about these configuration parameters please see
the :doc:`../admin/configuration-guide`.

Database package changes
++++++++++++++++++++++++

The oslo based code from sahara.openstack.common.db has been replaced by
the usage of the oslo.db package. This change does not require any
update to sahara's configuration file.

Additionally, the usage of SQLite databases has been deprecated. Please use
MySQL or PostgreSQL databases for sahara. SQLite has been deprecated because it
does not, and is not going to, support the ``ALTER COLUMN`` and ``DROP COLUMN``
commands required for migrations between versions. For more information please
see http://www.sqlite.org/omitted.html

Sahara integration into OpenStack Dashboard
+++++++++++++++++++++++++++++++++++++++++++

The sahara dashboard package has been deprecated in the Juno release. The
functionality of the dashboard has been fully incorporated into the
OpenStack Dashboard. The sahara interface is available under the
"Project" -> "Data Processing" tab.

The Data processing service endpoints must be registered in the Identity
service catalog for the Dashboard to properly recognize and display
those user interface components. For more details on this process please see
:ref:`registering Sahara in installation guide <register-sahara-label>`.

The
`sahara-dashboard <https://opendev.org/openstack/sahara-dashboard>`_
project is now used solely to host sahara user interface integration tests.

Virtual machine user name changes
+++++++++++++++++++++++++++++++++

The HEAT infrastructure engine has been updated to use the same rules for
instance user names as the direct engine. In previous releases the user
name for instances created by sahara using HEAT was always 'ec2-user'. As
of Juno, the user name is taken from the image registry as described in
the :doc:`../user/registering-image` document.

This change breaks backward compatibility for clusters created using the HEAT
infrastructure engine prior to the Juno release. Clusters will continue to
operate, but we do not recommended using the scaling operations with them.

Anti affinity implementation changed
++++++++++++++++++++++++++++++++++++

Starting with the Juno release the anti affinity feature is implemented
using server groups. From the user perspective there will be no
noticeable changes with this feature. Internally this change has
introduced the following behavior:

1) Server group objects will be created for any clusters with anti affinity
   enabled.
2) Affected instances on the same host will not be allowed even if they
   do not have common processes. Prior to Juno, instances with differing
   processes were allowed on the same host. The new implementation
   guarantees that all affected instances will be on different hosts
   regardless of their processes.

The new anti affinity implementation will only be applied for new clusters.
Clusters created with previous versions will continue to operate under
the older implementation, this applies to scaling operations on these
clusters as well.

Juno -> Kilo
------------

Sahara requires policy configuration
++++++++++++++++++++++++++++++++++++

Sahara now requires a policy configuration file. The ``policy.json`` file
should be placed in the same directory as the sahara configuration file or
specified using the ``policy_file`` parameter. For more details about the
policy file please see the
:ref:`policy section in the configuration guide <policy-configuration-label>`.

Kilo -> Liberty
---------------

Direct engine deprecation
+++++++++++++++++++++++++

In the Liberty release the direct infrastructure engine has been deprecated and
the heat infrastructure engine is now default. This means, that it is
preferable to use heat engine instead now. In the Liberty release you can
continue to operate clusters with the direct engine (create, delete, scale).
Using heat engine only the delete operation is available on clusters that were
created by the direct engine.  After the Liberty release the direct engine will
be removed, this means that you will only be able to delete clusters created
with the direct engine.

Policy namespace changed (policy.json)
++++++++++++++++++++++++++++++++++++++

The "data-processing:" namespace has been added to the beginning of the all
Sahara's policy based actions, so, you need to update the policy.json file by
prepending all actions with "data-processing:".

Liberty -> Mitaka
-----------------

Direct engine is removed.

Mitaka -> Newton
----------------

Sahara CLI command is deprecated, please use OpenStack Client.

.. note::

    Since Mitaka release sahara actively uses release notes so you can see all
    required upgrade actions here: https://docs.openstack.org/releasenotes/sahara/
