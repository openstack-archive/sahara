Sahara Configuration Guide
==========================

This guide covers the steps for a basic configuration of sahara.
It will help you to configure the service in the most simple
manner.

Basic configuration
-------------------

Sahara is packaged with a basic sample configuration file:
``sahara.conf.sample-basic``. This file contains all the essential
parameters that are required for sahara. We recommend creating your
configuration file based on this basic example.

If a more thorough configuration is needed we recommend using the ``tox``
tool to create a full configuration file by executing the following
command:

.. sourcecode:: cfg

    $ tox -e genconfig

..

Running this command will create a file named ``sahara.conf.sample``
in the ``etc/sahara`` directory of the project.

After creating a configuration file by either copying the basic example
or generating one, edit the ``connection`` parameter in the
``[database]`` section. The URL provided here should point to an empty
database. For example, the connection string for a MySQL database will be:

.. sourcecode:: cfg

    connection=mysql://username:password@host:port/database
..

Next you will configure the Identity service parameters in the
``[keystone_authtoken]`` section. The ``auth_uri`` parameter
should point to the public Identity API endpoint. The ``identity_uri``
should point to the admin Identity API endpoint. For example:

.. sourcecode:: cfg

    auth_uri=http://127.0.0.1:5000/v2.0/
    identity_uri=http://127.0.0.1:35357/
..

Specify the ``admin_user``, ``admin_password`` and ``admin_tenant_name``.
These parameters must specify an Identity user who has the ``admin`` role
in the given tenant. These credentials allow sahara to authenticate and
authorize its users.

Next you will configure the default Networking service. If using
neutron for networking the following parameter should be set
in the ``[DEFAULT]`` section:

.. sourcecode:: cfg

    use_neutron=true
..

If you are using nova-network for networking then this parameter should
be set to ``false``.

With these parameters set, sahara is ready to run.

If you wish to increase the logging levels for troubleshooting there
are two parameters in the ``[DEFAULT]`` section of the configuration
file which control the level of logging output; ``verbose`` and
``debug``. With ``verbose`` set to ``true`` sahara's default logging
level will be set to INFO, and with ``debug`` set to ``true`` it will
be set to DEBUG. By default the sahara's log level is set to WARNING.

.. _neutron-nova-network:

Networking configuration
------------------------

By default sahara is configured to use the nova-network implementation
of OpenStack Networking. If an OpenStack cluster uses neutron,
then the ``use_neutron`` parameter should be set to ``True`` in the
sahara configuration file. Additionally, if the cluster supports network
namespaces the ``use_namespaces`` property can be used to enable their usage.

.. sourcecode:: cfg

    [DEFAULT]
    use_neutron=True
    use_namespaces=True

.. note::
    If a user other than ``root`` will be running the Sahara server
    instance and namespaces are used, some additional configuration is
    required, please see :ref:`non-root-users` for more information.

.. _floating_ip_management:

Floating IP management
++++++++++++++++++++++

During cluster setup sahara must access instances through a secure
shell(SSH). To establish this connection it may use either the fixed
or floating IP address of an instance. By default sahara is configured
to use floating IP addresses for access. This is controlled by the
``use_floating_ips`` configuration parameter. With this setup the user
has two options for ensuring that all instances gain a floating IP
address:

* If using the nova-network, it may be configured to assign floating
  IP addresses automatically by setting the ``auto_assign_floating_ip``
  parameter to ``True`` in the nova configuration file
  (usually ``nova.conf``).

* The user may specify a floating IP address pool for each node
  group directly.

.. warning::
    When using floating IP addresses for management
    (``use_floating_ips=True``) **every** instance in the cluster must have
    a floating IP address, otherwise sahara will not be able to utilize
    that cluster.

If not using floating IP addresses (``use_floating_ips=False``) sahara
will use fixed IP addresses for instance management. When using neutron
for the Networking service the user will be able to choose the
fixed IP network for all instances in a cluster. Whether using nova-network
or neutron it is important to ensure that all instances running sahara
have access to the fixed IP networks.

.. _notification-configuration:

Notifications configuration
---------------------------

Sahara can be configured to send notifications to the OpenStack
Telemetry module. To enable this functionality the following parameter
``enable`` should be set in the ``[oslo_messaging_notifications]`` section
of the configuration file:

.. sourcecode:: cfg

    [oslo_messaging_notifications]
    enable = true
..

And the following parameter ``driver`` should be set in the
``[oslo_messaging_notifications]`` section of the configuration file:

.. sourcecode:: cfg

    [oslo_messaging_notifications]
    driver = messaging
..

By default sahara is configured to use RabbitMQ as its message broker.

If you are using RabbitMQ as the message broker, then you should set the
following parameter in the ``[DEFAULT]`` section:

.. sourcecode:: cfg

    rpc_backend = rabbit
..

You may also need to specify the connection parameters for your
RabbitMQ installation. The following example shows the default
values in the ``[oslo_messaging_rabbit]`` section which may need
adjustment:

.. sourcecode:: cfg

    rabbit_host=localhost
    rabbit_port=5672
    rabbit_hosts=$rabbit_host:$rabbit_port
    rabbit_userid=guest
    rabbit_password=guest
    rabbit_virtual_host=/
..

.. _orchestration-configuration:

Orchestration configuration
---------------------------

By default sahara is configured to use the heat engine for instance
creation. The heat engine uses the OpenStack Orchestration service to
provision instances. Sahara can be configured to use the direct engine for
this purpose, but after the Liberty release it will be removed. This
engine makes calls directly to the services required for instance
provisioning. We recommend using the OpenStack Orchestration service.

To configure sahara to use the direct engine for instance
provisioning the ``infrastructure_engine`` parameter should be modified in
the configuration file as follows:

.. sourcecode:: cfg

    [DEFAULT]
    infrastructure_engine=direct

.. warning::
    The direct engine will be removed after the Liberty release, we
    recommend using the heat engine.

.. _policy-configuration-label:

Policy configuration
---------------------------

Sahara’s public API calls may be restricted to certain sets of users by
using a policy configuration file. The location of the policy file(s)
is controlled by the ``policy_file`` and ``policy_dirs`` parameters
in the ``[oslo_policy]`` section. By default sahara will search for
a ``policy.json`` file in the same directory as the ``sahara.conf``
configuration file.

Examples
++++++++

Example 1. Allow all method to all users (default policy).

.. sourcecode:: json

    {
        "default": ""
    }


Example 2. Disallow image registry manipulations to non-admin users.

.. sourcecode:: json

    {
        "default": "",

        "data-processing:images:register": "role:admin",
        "data-processing:images:unregister": "role:admin",
        "data-processing:images:add_tags": "role:admin",
        "data-processing:images:remove_tags": "role:admin"
    }

API configuration
-----------------

Sahara uses the ``api-paste.ini`` file to configure the data processing API
service. For middleware injection sahara uses pastedeploy library. The location
of the api-paste file is controlled by the ``api_paste_config`` parameter in
the ``[default]`` section. By default sahara will search for a
``api-paste.ini`` file in the same directory as the configuration file.
